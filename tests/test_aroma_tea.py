"""시음 후 향 평가, 차 종류별 특징."""

from datetime import datetime

import pytest

from senso.db.bean_repo import BeanRepository
from senso.db.brew_repo import BrewRepository
from senso.db.database import open_database
from senso.domain.aroma import AROMAS, clean_aromas, describe, group_of
from senso.domain.bean import TEA_TYPES, BeanKind, validate_bean
from senso.domain.brew import BrewValidationError, validate_brew
from senso.domain.tea import DISCLAIMER, TEA_INFO, caffeine_tag, tea_info
from senso.taste.dna import compute

NOW = datetime(2026, 11, 14, 9, 0)


@pytest.fixture
def repos(tmp_path):
    conn = open_database(tmp_path / "t.db")
    yield BeanRepository(conn), BrewRepository(conn)
    conn.close()


# ---- 향 목록 ------------------------------------------------------------------------


@pytest.mark.parametrize("kind", list(BeanKind))
def test_aroma_lists_are_unique(kind):
    groups = AROMAS[kind]
    assert len({g.key for g in groups}) == len(groups)
    notes = [n for g in groups for n in g.notes]
    assert len(set(notes)) == len(notes), "세부 향은 한 계열에만 속해야 한다"
    assert all(g.color.startswith("#") and len(g.color) == 7 for g in groups)


def test_clean_aromas_adds_group_of_note_and_orders():
    groups, notes, unknown = clean_aromas(BeanKind.COFFEE, ["citrus"], ["자스민", "레몬", "레몬"])
    assert groups == ("floral", "citrus")  # 자스민을 골랐으니 꽃 계열도
    assert notes == ("자스민", "레몬")
    assert unknown == []
    assert group_of(BeanKind.TEA, "김").key == "marine"
    assert describe(BeanKind.COFFEE, groups, notes) == "꽃(자스민) · 시트러스(레몬)"


def test_clean_aromas_unknown():
    _, _, unknown = clean_aromas(BeanKind.TEA, ["chocolate"], ["다크 초콜릿"])  # 커피용 향
    assert unknown == ["chocolate", "다크 초콜릿"]


# ---- 기록에 저장 ----------------------------------------------------------------------


def test_aroma_saved_and_loaded(repos):
    beans, brews = repos
    bean = beans.create(validate_bean(BeanKind.COFFEE, "예가체프"))
    draft = validate_brew(
        bean=bean,
        bean_id=bean.id,
        dose_g="15",
        water_g="250",
        aroma_intensity=4,
        aromas=["floral"],
        aroma_notes=["자스민", "복숭아"],
    )
    assert not draft.tasting.is_empty  # 향만 남겨도 평가가 있는 것
    saved = brews.get(brews.create(draft, NOW).id)
    assert saved.tasting.aroma_intensity == 4
    assert saved.tasting.aromas == ("floral", "fruit")
    assert saved.tasting.aroma_notes == ("자스민", "복숭아")


def test_aroma_validation(repos):
    beans, _ = repos
    tea = beans.create(validate_bean(BeanKind.TEA, "세작", tea_type="green"))
    with pytest.raises(BrewValidationError) as e:
        validate_brew(
            bean=tea,
            bean_id=tea.id,
            dose_g="3",
            water_g="150",
            aroma_intensity=7,
            aroma_notes=["다크 초콜릿"],
        )
    assert {"aroma_intensity", "aromas"} <= set(e.value.errors)


def test_old_brews_without_aroma_still_load(repos):
    beans, brews = repos
    bean = beans.create(validate_bean(BeanKind.COFFEE, "예가체프"))
    brew = brews.create(validate_brew(bean=bean, bean_id=bean.id, dose_g="15", water_g="250"), NOW)
    loaded = brews.get(brew.id)
    assert loaded.tasting.aromas == () and loaded.tasting.aroma_intensity is None
    assert loaded.tasting.is_empty


def test_dna_top_aromas(repos):
    beans, brews = repos
    bean = beans.create(validate_bean(BeanKind.COFFEE, "예가체프"))
    for i in range(5):
        draft = validate_brew(
            bean=bean,
            bean_id=bean.id,
            dose_g="15",
            water_g="250",
            scores={"satisfaction": 5 if i < 3 else 2},
            aroma_notes=["자스민"] if i < 3 else ["탄 향"],
        )
        brews.create(draft, NOW)
    dna = compute(brews.list())
    assert dna.top_aromas == ("꽃",)


# ---- 차 종류별 특징 ---------------------------------------------------------------------


def test_every_tea_type_has_info():
    assert set(TEA_INFO) == set(TEA_TYPES)
    for key, info in TEA_INFO.items():
        assert info.caffeine and info.points and info.brew_tip, key
    assert tea_info(None) is None and tea_info("nope") is None


def test_caffeine_tags():
    assert caffeine_tag("matcha") == "카페인 많음"
    assert caffeine_tag("grain") == "카페인 없음(대부분)"
    assert caffeine_tag(None) is None


def test_no_cure_claims():
    """'치료·예방·완화' 같은 의학적 효능 단정 표현을 쓰지 않는다."""
    banned = ("치료", "예방", "완화", "낫", "다이어트", "살이 빠")
    for info in TEA_INFO.values():
        for text in (*info.points, info.brew_tip):
            assert not any(b in text for b in banned), text
    assert "뜻하지 않아요" in DISCLAIMER
