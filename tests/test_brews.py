from datetime import datetime

import pytest

from senso.db.bean_repo import BeanRepository
from senso.db.brew_repo import BrewRepository
from senso.db.database import open_database
from senso.domain.bean import BeanKind, validate_bean
from senso.domain.brew import (
    BrewValidationError,
    Tasting,
    format_number,
    format_time,
    parse_time,
    validate_brew,
)

NOW = datetime(2026, 11, 13, 9, 30)


@pytest.fixture
def conn(tmp_path):
    c = open_database(tmp_path / "test.db")
    yield c
    c.close()


@pytest.fixture
def beans(conn):
    return BeanRepository(conn)


@pytest.fixture
def brews(conn):
    return BrewRepository(conn)


@pytest.fixture
def coffee(beans):
    return beans.create(validate_bean(BeanKind.COFFEE, "예가체프", "프릳츠", roast_level="light"))


@pytest.fixture
def tea(beans):
    return beans.create(validate_bean(BeanKind.TEA, "제주 세작", tea_type="green"))


def draft(bean, **kw):
    args = {"bean": bean, "bean_id": bean.id, "dose_g": "15", "water_g": "250"} | kw
    return validate_brew(**args)


# ---- 시간·숫자 -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "seconds"),
    [("3:20", 200), ("03:05", 185), ("3분 20초", 200), ("3분", 180), ("200", 200), ("45초", 45)],
)
def test_parse_time(text, seconds):
    assert parse_time(text) == seconds


@pytest.mark.parametrize("text", ["3:75", "abc", "1:2:3"])
def test_parse_time_rejects(text):
    with pytest.raises(ValueError):
        parse_time(text)


def test_formatting():
    assert format_time(200) == "3:20"
    assert format_time(None) == "-"
    assert format_number(15.0, "g") == "15g"
    assert format_number(15.5) == "15.5"


# ---- 검증 --------------------------------------------------------------------


def test_minimum_brew(coffee):
    d = draft(coffee)
    assert d.recipe.dose_g == 15 and d.recipe.water_g == 250
    assert d.tasting.is_empty
    assert round(d.recipe.ratio, 1) == 16.7


def test_bean_dose_water_required():
    with pytest.raises(BrewValidationError) as e:
        validate_brew(bean=None, bean_id=None, dose_g="", water_g=" ")
    assert set(e.value.errors) == {"bean", "dose_g", "water_g"}
    assert e.value.errors["dose_g"] == "원두량을 입력해 주세요"


@pytest.mark.parametrize(
    ("field", "value"),
    [("dose_g", "abc"), ("dose_g", "0"), ("water_g", "-5"), ("temp_c", "120"), ("time", "9:99")],
)
def test_bad_numbers(coffee, field, value):
    with pytest.raises(BrewValidationError):
        draft(coffee, **{field: value})


def test_comma_decimal(coffee):
    assert draft(coffee, dose_g="15,5").recipe.dose_g == 15.5


def test_unset_score_differs_from_middle_score(coffee):
    d = draft(coffee, scores={"acidity": 3, "bitterness": None})
    assert d.tasting.acidity == 3
    assert d.tasting.bitterness is None
    assert not d.tasting.is_empty


def test_score_out_of_range(coffee):
    with pytest.raises(BrewValidationError):
        draft(coffee, scores={"body": 6})


def test_ice_only_kept_when_iced(coffee):
    assert draft(coffee, ice_g="80").recipe.ice_g is None
    assert draft(coffee, ice_g="80", iced=True).recipe.ice_g == 80


def test_tea_drops_grind_and_grinder(tea):
    d = draft(tea, grind="24클릭", grinder="코만단테")
    assert d.recipe.grind is None and d.grinder is None
    assert d.kind is BeanKind.TEA


def test_keep_cannot_mix_with_changes(coffee):
    with pytest.raises(BrewValidationError):
        draft(coffee, next_wish=["keep", "stronger"])


def test_wishes_deduplicated_in_order(coffee):
    d = draft(coffee, next_wish=["stronger", "less_acid", "stronger"])
    assert d.tasting.next_wish == ("stronger", "less_acid")


# ---- 저장소 ------------------------------------------------------------------


def test_save_without_tasting_then_add_later(brews, coffee):
    brew = brews.create(draft(coffee, dripper="V60", time="2:50"), brewed_at=NOW)
    assert brew.tasting.is_empty
    assert brew.dripper == "V60" and brew.recipe.time_s == 170
    assert brew.brewed_at == NOW

    rated = draft(
        coffee,
        dripper="V60",
        time="2:50",
        scores={"acidity": 4, "satisfaction": 3},
        tasting_notes="밝은 산미",
        next_wish=["less_acid"],
    )
    updated = brews.update(brew.id, rated)
    assert updated.tasting.acidity == 4
    assert updated.tasting.next_wish == ("less_acid",)
    assert updated.tasting.notes == "밝은 산미"
    assert updated.brewed_at == NOW  # 수정해도 추출 시각은 그대로


def test_list_newest_first(brews, coffee):
    brews.create(draft(coffee), brewed_at=datetime(2026, 11, 1, 8))
    brews.create(draft(coffee), brewed_at=datetime(2026, 11, 3, 8))
    brews.create(draft(coffee), brewed_at=datetime(2026, 11, 2, 8))
    assert [b.brewed_at.day for b in brews.list()] == [3, 2, 1]


def test_snapshot_survives_bean_edit_and_delete(beans, brews, coffee):
    brew = brews.create(draft(coffee), brewed_at=NOW)
    beans.update(coffee.id, validate_bean(BeanKind.COFFEE, "바뀐 이름"), None)
    beans.soft_delete(coffee.id)
    again = brews.get(brew.id)
    assert again.bean.name == "예가체프"
    assert again.bean.producer == "프릳츠"


def test_delete_keeps_derived_brews(brews, coffee):
    parent = brews.create(draft(coffee), brewed_at=NOW)
    child = brews.create(draft(coffee, based_on_brew_id=parent.id), brewed_at=NOW)
    assert [b.id for b in brews.derived_from(parent.id)] == [child.id]
    brews.delete(parent.id)
    assert brews.get(parent.id) is None
    assert brews.get(child.id).based_on_brew_id is None


def test_update_does_not_change_link(brews, coffee):
    parent = brews.create(draft(coffee), brewed_at=NOW)
    child = brews.create(draft(coffee, based_on_brew_id=parent.id), brewed_at=NOW)
    updated = brews.update(child.id, draft(coffee))
    assert updated.based_on_brew_id == parent.id


def test_tasting_is_empty():
    assert Tasting().is_empty
    assert not Tasting(next_wish=("keep",)).is_empty
