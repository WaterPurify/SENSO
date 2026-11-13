"""사업계획서 v2.5: 산지 국기, 오늘의 말씀 한 잔."""

import io
from datetime import date, datetime

import pytest
from PIL import Image

from senso.db.bean_repo import BeanRepository
from senso.db.brew_repo import BrewRepository
from senso.db.database import open_database
from senso.db.settings_repo import WORD_ENABLED, SettingsRepository
from senso.db.word_repo import AlreadyToday, WordRepository
from senso.domain.bean import BeanKind, BeanValidationError, validate_bean
from senso.domain.brew import BeanSnapshot
from senso.origin import country_of, find_country, with_flag
from senso.word.card import render_word_card
from senso.word.moods import MOODS, MOODS_BY_KEY, find_verse, is_crisis, pick_verse

NOW = datetime(2026, 11, 14, 9, 30)


@pytest.fixture
def conn(tmp_path):
    c = open_database(tmp_path / "t.db")
    yield c
    c.close()


# ---- 산지와 국기 ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("에티오피아 예가체프", "ET"),
        ("[예시] 에티오피아 예가체프", "ET"),
        ("예가체프 G1", "ET"),
        ("제주 세작", "KR"),
        ("보성 녹차", "KR"),
        ("콜롬비아 수프리모", "CO"),
        ("인도네시아 만델링", "ID"),  # '인도'가 아니라 인도네시아
        ("다즐링 퍼스트 플러시", "IN"),
        ("Kenya AA", "KE"),
        ("하와이 코나", "US"),
        ("브라질 산토스와 에티오피아 블렌드", "BR"),  # 먼저 나온 나라
    ],
)
def test_find_country(text, code):
    assert find_country(text).code == code


@pytest.mark.parametrize("text", ["하우스 블렌드", "", None, "디카페인"])
def test_no_country(text):
    assert find_country(text) is None


def test_origin_field_wins_over_name():
    assert country_of("케냐", "에티오피아 블렌드").code == "KE"
    assert country_of("어딘가", "제주 세작").code == "KR"  # 산지에서 못 찾으면 이름


def test_flag_emoji():
    assert find_country("에티오피아").flag == "\U0001f1ea\U0001f1f9"
    assert find_country("제주").flag == "\U0001f1f0\U0001f1f7"
    assert with_flag("제주 세작") == "\U0001f1f0\U0001f1f7 제주 세작"
    assert with_flag("하우스 블렌드") == "하우스 블렌드"


def test_origin_saved_and_snapshotted(conn):
    beans = BeanRepository(conn)
    bean = beans.create(validate_bean(BeanKind.COFFEE, "G1 워시드", origin="  에티오피아 구지 "))
    assert bean.origin == "에티오피아 구지"
    snap = BeanSnapshot.of(bean)
    assert BeanSnapshot.from_dict(snap.to_dict()).origin == "에티오피아 구지"
    # 예전 기록(origin 없는 JSON)도 그대로 읽힌다
    assert BeanSnapshot.from_dict({"name": "옛 원두", "kind": "coffee"}).origin is None
    updated = beans.update(bean.id, validate_bean(BeanKind.COFFEE, "G1 워시드"), None)
    assert updated.origin is None


def test_origin_too_long():
    with pytest.raises(BeanValidationError) as e:
        validate_bean(BeanKind.TEA, "차", origin="가" * 41)
    assert "origin" in e.value.errors


def test_brew_keeps_origin(conn):
    from senso.domain.brew import validate_brew

    beans, brews = BeanRepository(conn), BrewRepository(conn)
    bean = beans.create(validate_bean(BeanKind.TEA, "세작", origin="제주"))
    draft = validate_brew(bean=bean, bean_id=bean.id, dose_g="3", water_g="200")
    brew = brews.create(draft, NOW)
    assert brews.get(brew.id).bean.origin == "제주"


# ---- 말씀 데이터 ------------------------------------------------------------------


def test_eight_moods_each_with_verse():
    assert len(MOODS) == 8
    assert len(MOODS_BY_KEY) == 8
    for m in MOODS:
        assert m.side in ("sen", "so")
        assert m.verses
        for v in m.verses:
            assert v.ref and v.text and v.meditation


def test_same_day_same_verse_and_rotation():
    wisdom = MOODS_BY_KEY["wisdom"]
    d = date(2026, 11, 14)
    assert pick_verse(wisdom, d) == pick_verse(wisdom, d)
    refs = {pick_verse(wisdom, date.fromordinal(d.toordinal() + i)).ref for i in range(2)}
    assert refs == {"야고보서 1:5", "잠언 3:5-6"}


def test_find_verse():
    mood, verse = find_verse("tired", "마태복음 11:28")
    assert mood.key == "tired" and verse.text.startswith("수고하고")
    assert find_verse("tired", "없는 구절 1:1") is None
    assert find_verse("unknown", "마태복음 11:28") is None


@pytest.mark.parametrize(
    "text", ["요즘 죽고 싶어요", "그냥 사라지고싶다", "살기 싫어", "자해를 했어요", "자 살"]
)
def test_crisis_detected(text):
    assert is_crisis(text)


@pytest.mark.parametrize("text", [None, "", "발표가 걱정돼요", "피곤해 죽겠어요"])
def test_no_crisis(text):
    assert not is_crisis(text)


# ---- 설정과 카드 저장 ---------------------------------------------------------------


def test_setting_three_states(conn):
    settings = SettingsRepository(conn)
    assert settings.get_flag(WORD_ENABLED) is None  # 아직 고르지 않음
    settings.set_flag(WORD_ENABLED, True)
    assert settings.get_flag(WORD_ENABLED) is True
    settings.set_flag(WORD_ENABLED, False)
    assert settings.get_flag(WORD_ENABLED) is False


def test_one_card_per_day(conn):
    words = WordRepository(conn)
    day = NOW.date()
    assert words.for_day(day) is None
    card = words.create(day, "tired", "마태복음 11:28", "  ", NOW)
    assert card.note is None and not card.saved
    assert words.for_day(day) == card
    with pytest.raises(AlreadyToday):
        words.create(day, "joyful", "데살로니가전서 5:16-18", None, NOW)
    nxt = words.create(date(2026, 11, 15), "joyful", "데살로니가전서 5:16-18", "좋은 날", NOW)
    assert nxt.note == "좋은 날"


def test_word_note(conn):
    words = WordRepository(conn)
    a = words.create(date(2026, 11, 13), "tired", "마태복음 11:28", None, NOW)
    b = words.create(date(2026, 11, 14), "peace", "민수기 6:24-26", None, NOW)
    assert words.saved() == []
    words.set_saved(a.id, True)
    words.set_saved(b.id, True)
    assert [c.id for c in words.saved()] == [b.id, a.id]  # 최신순
    words.set_saved(a.id, False)
    assert [c.id for c in words.saved()] == [b.id]


@pytest.mark.parametrize("key", [m.key for m in MOODS])
def test_word_card_png(key):
    mood = MOODS_BY_KEY[key]
    png = render_word_card(mood, mood.verses[0], date(2026, 11, 14))
    with Image.open(io.BytesIO(png)) as img:
        assert img.format == "PNG"
        assert img.size == (1080, 1920)
