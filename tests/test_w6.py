"""W6: 제안으로 새 기록 만들기, 추천 저장, 캐릭터 대사."""

from datetime import datetime

import pytest

from senso.characters.lines import (
    Who,
    beans_greeting,
    brew_again_line,
    compare_line,
    home_greeting,
    recommendation_line,
)
from senso.db.bean_repo import BeanRepository
from senso.db.brew_repo import BrewRepository
from senso.db.database import open_database
from senso.db.recommendation_repo import RecommendationRepository
from senso.domain.bean import BeanKind, validate_bean
from senso.domain.brew import validate_brew
from senso.recommend.apply import draft_from_recommendation
from senso.recommend.engine import NoRecommendation, recommend

NOW = datetime(2026, 11, 14, 10, 0)


@pytest.fixture
def repos(tmp_path):
    conn = open_database(tmp_path / "t.db")
    yield BeanRepository(conn), BrewRepository(conn), RecommendationRepository(conn)
    conn.close()


def rated_brew(beans, brews, wish, **kw):
    bean = beans.create(validate_bean(BeanKind.COFFEE, "예가체프"))
    args = {
        "bean": bean,
        "bean_id": bean.id,
        "dose_g": "15",
        "water_g": "250",
        "temp_c": "93",
        "grind": "24클릭",
        "time": "2:40",
        "dripper": "V60",
        "notes": "30초 뜸",
        "desired_flavors": ["과일"],
        "scores": {"acidity": 5, "satisfaction": 2},
        "tasting_notes": "너무 시다",
        "next_wish": wish,
    } | kw
    return brews.create(validate_brew(**args), brewed_at=NOW)


def test_brew_again_creates_linked_new_record(repos):
    beans, brews, recs = repos
    original = rated_brew(beans, brews, ["stronger"])
    rec = recommend(original)
    saved = recs.save(original.id, rec)

    draft = draft_from_recommendation(original, rec, saved.id)
    new = brews.create(draft, brewed_at=NOW.replace(hour=11))

    # 새 기록: 제안 반영, 평가는 비어 있음, 연결 정보 있음
    assert new.id != original.id
    assert new.recipe.water_g == 225
    assert new.tasting.is_empty
    assert new.based_on_brew_id == original.id
    assert new.based_on_rec_id == saved.id
    assert new.desired_flavors == ("과일",) and new.dripper == "V60"
    # 이전 기록은 그대로
    again = brews.get(original.id)
    assert again.recipe.water_g == 250
    assert again.tasting.notes == "너무 시다"
    # 저장된 제안
    stored = recs.get(saved.id)
    assert (stored.changed_field, stored.method) == ("water_g", "rule-v1")
    assert stored.source_brew_id == original.id


def test_direction_only_hint_goes_to_notes(repos):
    beans, brews, _ = repos
    original = rated_brew(beans, brews, ["less_acid"])
    rec = recommend(original)
    assert rec.direction_only
    draft = draft_from_recommendation(original, rec, 1)
    assert draft.recipe.grind == "24클릭"  # 숫자는 바꾸지 않는다
    assert draft.notes.startswith("[제안] 분쇄도 조금 더 곱게 (이전: 24클릭)")
    assert draft.notes.endswith("30초 뜸")


def test_recommendation_deleted_with_source_brew_keeps_child(repos):
    beans, brews, recs = repos
    original = rated_brew(beans, brews, ["stronger"])
    rec = recommend(original)
    saved = recs.save(original.id, rec)
    child = brews.create(draft_from_recommendation(original, rec, saved.id), brewed_at=NOW)

    brews.delete(original.id)
    assert recs.get(saved.id) is None
    survivor = brews.get(child.id)
    assert survivor.based_on_brew_id is None and survivor.based_on_rec_id is None


# ---- 대사 -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("hour", "count", "who"),
    [(9, 3, Who.SEN), (13, 3, Who.SEN), (16, 3, Who.SO), (23, 3, Who.SO), (9, 0, Who.DUO)],
)
def test_home_greeting_by_time(hour, count, who):
    line = home_greeting(NOW.replace(hour=hour), count)
    assert line.who is who
    assert line.text


def test_after_cutoff_so_mentions_caffeine():
    assert "디카페인" in home_greeting(NOW.replace(hour=15), 2).text


def test_beans_greeting_matches_kind():
    assert beans_greeting(BeanKind.COFFEE, 0).who is Who.SEN
    assert beans_greeting(BeanKind.TEA, 2).who is Who.SO
    assert "2가지" in beans_greeting(BeanKind.TEA, 2).text


def test_recommendation_and_again_lines(repos):
    beans, brews, _ = repos
    original = rated_brew(beans, brews, ["stronger"])
    rec = recommend(original)
    assert "물양" in recommendation_line(BeanKind.COFFEE, rec).text
    again = brew_again_line(BeanKind.COFFEE, rec)
    assert again.who is Who.SEN and "250g" in again.text and "225g" in again.text
    no = NoRecommendation("conflict", "x")
    assert recommendation_line(BeanKind.TEA, no).who is Who.SO


@pytest.mark.parametrize(
    ("before", "after", "word"), [(2, 4, "올랐"), (4, 2, "아쉬"), (3, 3, "같"), (None, 4, "평가")]
)
def test_compare_line(before, after, word):
    assert word in compare_line(BeanKind.COFFEE, before, after).text
