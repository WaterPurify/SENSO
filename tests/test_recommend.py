"""규칙 기반 추천(rule-v1) 테스트."""

from datetime import datetime

import pytest

from senso.domain.bean import BeanKind
from senso.domain.brew import BeanSnapshot, Brew, Recipe, Tasting
from senso.recommend.engine import NoRecommendation, Recommendation, recommend

COFFEE = BeanSnapshot(name="예가체프", kind=BeanKind.COFFEE)
TEA = BeanSnapshot(name="세작", kind=BeanKind.TEA)


def brew(
    kind=BeanKind.COFFEE,
    *,
    dose=15.0,
    water=250.0,
    temp=None,
    grind=None,
    time=None,
    wish=(),
    **scores,
) -> Brew:
    return Brew(
        id=1,
        bean_id=1,
        bean=COFFEE if kind is BeanKind.COFFEE else TEA,
        recipe=Recipe(dose_g=dose, water_g=water, temp_c=temp, grind=grind, time_s=time),
        tasting=Tasting(next_wish=tuple(wish), **scores),
        brewed_at=datetime(2026, 11, 14, 9),
    )


def rec(b: Brew) -> Recommendation:
    result = recommend(b)
    assert isinstance(result, Recommendation), result
    return result


def no(b: Brew) -> NoRecommendation:
    result = recommend(b)
    assert isinstance(result, NoRecommendation), result
    return result


# ---- 제안하지 않는 경우 -------------------------------------------------------------


def test_no_tasting():
    assert no(brew()).kind == "no_tasting"


def test_keep_means_no_change():
    assert no(brew(wish=["keep"], satisfaction=2)).kind == "satisfied"


def test_satisfied_without_wish():
    assert no(brew(satisfaction=5, acidity=3)).kind == "satisfied"


def test_unclear_middle_scores():
    r = no(brew(acidity=3, bitterness=3, sweetness=3, body=3, satisfaction=3))
    assert r.kind == "unclear"
    assert "다음에 원하는 변화" in r.reason


@pytest.mark.parametrize(
    "wish",
    [
        ["less_acid", "more_acid"],
        ["stronger", "lighter"],
        ["less_acid", "less_bitter"],
        ["less_bitter", "stronger"],
    ],
)
def test_conflicting_wishes(wish):
    r = no(brew(wish=wish))
    assert r.kind == "conflict"
    assert "반대 방향" in r.reason


def test_conflicting_scores():
    # 산미도 쓴맛도 강하게 느꼈으면 한 방향으로 바꿀 수 없다
    assert no(brew(acidity=5, bitterness=5, satisfaction=2)).kind == "conflict"


def test_tea_acid_wish_unsupported():
    assert no(brew(BeanKind.TEA, wish=["less_acid"])).kind == "unsupported"


# ---- 커피 -----------------------------------------------------------------------


def test_less_acid_grind_finer_direction_only():
    b = brew(grind="24클릭", wish=["less_acid"])
    r = rec(b)
    assert r.field == "grind"
    assert r.to_value == "조금 더 곱게"
    assert r.from_value == "24클릭"
    assert r.direction_only
    assert r.new_recipe == b.recipe  # 숫자를 임의로 바꾸지 않는다


def test_less_bitter_grind_coarser():
    r = rec(brew(wish=["less_bitter"]))
    assert (r.field, r.to_value) == ("grind", "조금 더 굵게")
    assert r.note and "분쇄도를 적어 두면" in r.note  # 분쇄도 기록이 없을 때 안내


def test_more_acid_lowers_temp_when_known():
    r = rec(brew(temp=93, wish=["more_acid"]))
    assert r.field == "temp_c"
    assert r.new_recipe.temp_c == 91


def test_more_acid_falls_back_to_grind_without_temp():
    assert rec(brew(wish=["more_acid"])).field == "grind"


def test_more_acid_respects_min_temp():
    assert rec(brew(temp=86, wish=["more_acid"])).field == "grind"


def test_stronger_reduces_water_10_percent():
    r = rec(brew(water=250, wish=["stronger"]))
    assert r.field == "water_g"
    assert r.new_recipe.water_g == 225
    assert r.new_recipe.dose_g == 15  # 한 가지만 바꾼다
    assert "1:15.0" in r.to_value


def test_lighter_adds_water():
    assert rec(brew(water=250, wish=["lighter"])).new_recipe.water_g == 275


def test_sweeter_extends_time():
    r = rec(brew(time=160, wish=["sweeter"]))
    assert (r.field, r.new_recipe.time_s) == ("time_s", 175)
    assert r.to_value == "2:55"


def test_sweeter_without_time_uses_grind():
    assert rec(brew(wish=["sweeter"])).to_value == "조금 더 곱게"


def test_only_one_condition_changes():
    b = brew(temp=93, grind="중간", time=170, wish=["stronger"])
    r = rec(b)
    changed = [
        f
        for f in ("dose_g", "water_g", "temp_c", "grind", "time_s", "ice_g")
        if getattr(r.new_recipe, f) != getattr(b.recipe, f)
    ]
    assert changed == ["water_g"]


def test_priority_and_followup_note():
    r = rec(brew(wish=["sweeter", "less_bitter"], time=150))
    assert r.goal == "less_bitter"
    assert "단맛 더" in r.note


def test_wish_beats_scores():
    # 쓴맛 점수가 높아도 사용자가 고른 바람을 먼저 반영한다
    r = rec(brew(wish=["stronger"], bitterness=5))
    assert r.goal == "stronger"
    assert not r.inferred


def test_inferred_from_high_acidity():
    r = rec(brew(acidity=5, satisfaction=2))
    assert r.goal == "less_acid"
    assert r.inferred
    assert "산미를 5점" in r.note


def test_inferred_from_thin_body():
    assert rec(brew(body=1, satisfaction=3)).goal == "stronger"


def test_reason_is_a_suggestion_not_a_promise():
    r = rec(brew(wish=["less_acid"]))
    assert "비교해 보세요" in r.reason
    assert "보장은 없지만" in r.reason
    assert r.method == "rule-v1"


# ---- 차 -------------------------------------------------------------------------


def test_tea_less_bitter_lowers_temp():
    r = rec(brew(BeanKind.TEA, dose=3, water=150, temp=85, wish=["less_bitter"]))
    assert (r.field, r.new_recipe.temp_c) == ("temp_c", 80)


def test_tea_less_bitter_shortens_time_at_min_temp():
    r = rec(brew(BeanKind.TEA, temp=60, time=120, wish=["less_bitter"]))
    assert (r.field, r.new_recipe.time_s) == ("time_s", 95)


def test_tea_less_bitter_needs_temp_or_time():
    r = no(brew(BeanKind.TEA, wish=["less_bitter"]))
    assert r.kind == "missing"
    assert set(r.missing) == {"temp_c", "time_s"}


def test_tea_stronger_time_then_leaf():
    assert rec(brew(BeanKind.TEA, time=120, wish=["stronger"])).new_recipe.time_s == 150
    r = rec(brew(BeanKind.TEA, dose=3, wish=["stronger"]))
    assert (r.field, r.new_recipe.dose_g) == ("dose_g", 3.5)


def test_tea_lighter():
    assert rec(brew(BeanKind.TEA, time=120, wish=["lighter"])).new_recipe.time_s == 90
    assert rec(brew(BeanKind.TEA, time=30, water=150, wish=["lighter"])).field == "water_g"


def test_tea_sweeter_needs_temp():
    assert no(brew(BeanKind.TEA, wish=["sweeter"])).missing == ("temp_c",)
    assert rec(brew(BeanKind.TEA, temp=80, wish=["sweeter"])).new_recipe.temp_c == 75


def test_tea_never_touches_grind():
    r = rec(brew(BeanKind.TEA, temp=90, wish=["less_bitter"]))
    assert r.field != "grind"


def test_tea_bitter_inferred_without_acid():
    # 차는 산미 점수로 추론하지 않는다
    r = rec(brew(BeanKind.TEA, temp=90, acidity=5, bitterness=4, satisfaction=2))
    assert r.goal == "less_bitter"
