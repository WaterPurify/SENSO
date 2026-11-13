"""규칙 기반 다음 레시피 제안 (rule-v1).

원칙 (Coffee Bible MVP 명세):
- '다음에 원하는 변화'를 먼저 반영하고, 없으면 맛 점수에서 방향을 찾는다.
- 한 번에 한 가지 조건만 바꾼다.
- 그라인더마다 눈금이 달라 분쇄도는 숫자 대신 '조금 더 곱게'처럼 방향만 말한다.
- 정보가 부족하거나 바람이 서로 부딪치면 억지로 제안하지 않는다.
- 맛이 반드시 좋아진다고 단정하지 않고 '다음 추출에서 비교해 볼 제안'으로 말한다.

이 모듈은 화면·DB를 모른다. recommend(brew)만 바꾸면 나중에 AI 엔진으로 교체할 수 있다.
"""

from dataclasses import dataclass, replace

from senso.domain.bean import BeanKind
from senso.domain.brew import NEXT_WISHES, Brew, Recipe, format_number, format_time
from senso.text import josa

METHOD = "rule-v1"

FIELD_LABELS = {
    "grind": "분쇄도",
    "temp_c": "수온",
    "water_g": "물양",
    "dose_g": "원두량",
    "time_s": "추출 시간",
}

# 여러 변화를 골랐을 때 먼저 볼 순서
PRIORITY = ["less_bitter", "less_acid", "more_acid", "stronger", "lighter", "sweeter"]

# 함께 고르면 서로 반대 방향이라 한 번에 한 가지만 바꾸는 규칙으로는 풀 수 없는 조합
CONFLICTS: dict[BeanKind, list[frozenset[str]]] = {
    BeanKind.COFFEE: [
        frozenset({"less_acid", "more_acid"}),
        frozenset({"stronger", "lighter"}),
        frozenset({"less_acid", "less_bitter"}),
        frozenset({"less_bitter", "stronger"}),
    ],
    BeanKind.TEA: [
        frozenset({"stronger", "lighter"}),
        frozenset({"less_bitter", "stronger"}),
    ],
}

SUPPORTED: dict[BeanKind, set[str]] = {
    BeanKind.COFFEE: {"less_acid", "more_acid", "less_bitter", "stronger", "lighter", "sweeter"},
    BeanKind.TEA: {"less_bitter", "stronger", "lighter", "sweeter"},
}

CLOSING = "다음 추출에서 비교해 보세요. 맛이 꼭 좋아진다는 보장은 없지만, 한 가지만 바꿔야 차이를 알 수 있어요."


@dataclass(frozen=True)
class Recommendation:
    goal: str  # 반영한 바람 (예: less_bitter)
    field: str  # 바꾸는 조건 (예: grind)
    from_value: str  # 화면 표시용 지금 값
    to_value: str  # 화면 표시용 제안 값 또는 방향
    reason: str
    new_recipe: Recipe  # 새 기록의 초기값 (방향만 제안하면 원래 값 그대로)
    direction_only: bool = False
    inferred: bool = False  # 바람을 직접 고르지 않아 점수에서 추론했는지
    note: str | None = None
    method: str = METHOD

    @property
    def field_label(self) -> str:
        return FIELD_LABELS[self.field]

    @property
    def goal_label(self) -> str:
        return NEXT_WISHES[self.goal]


@dataclass(frozen=True)
class NoRecommendation:
    kind: str  # no_tasting | satisfied | conflict | unclear | missing | unsupported | limit
    reason: str
    missing: tuple[str, ...] = ()
    method: str = METHOD


Result = Recommendation | NoRecommendation


# ---- 바람 정하기 ----------------------------------------------------------------


def _infer_goals(brew: Brew) -> list[tuple[str, str]]:
    """맛 점수에서 바람을 추론한다. (바람, 근거 문장) 목록."""
    t = brew.tasting
    coffee = brew.kind is BeanKind.COFFEE
    found: list[tuple[str, str]] = []
    if t.bitterness is not None and t.bitterness >= 4:
        found.append(("less_bitter", f"쓴맛을 {t.bitterness}점으로 강하게 느꼈어요"))
    if coffee and t.acidity is not None and t.acidity >= 4:
        found.append(("less_acid", f"산미를 {t.acidity}점으로 강하게 느꼈어요"))
    if t.body is not None and t.body <= 2:
        found.append(("stronger", f"바디를 {t.body}점으로 가볍게 느꼈어요"))
    if t.body is not None and t.body >= 5 and (t.satisfaction or 0) <= 3:
        found.append(("lighter", f"바디를 {t.body}점으로 아주 묵직하게 느꼈어요"))
    if t.sweetness is not None and t.sweetness <= 2:
        found.append(("sweeter", f"단맛을 {t.sweetness}점으로 약하게 느꼈어요"))
    return found


def _conflict(goals: set[str], kind: BeanKind) -> frozenset[str] | None:
    for pair in CONFLICTS[kind]:
        if pair <= goals:
            return pair
    return None


def _labels(goals) -> str:
    return "', '".join(NEXT_WISHES[g] for g in goals)


def _quoted(goals) -> str:
    return f"'{_labels(goals)}'"


def recommend(brew: Brew) -> Result:
    t = brew.tasting
    kind = brew.kind

    if t.is_empty:
        return NoRecommendation(
            "no_tasting",
            "아직 시음 평가가 없어요. 마셔 본 뒤 평가를 남기면 다음 레시피를 제안할게요.",
        )
    if "keep" in t.next_wish:
        return NoRecommendation(
            "satisfied",
            "'이대로 좋아요'를 골랐어요. 같은 레시피로 한 번 더 내려서 맛이 유지되는지 확인해 보세요.",
        )

    wishes = [w for w in t.next_wish if w in NEXT_WISHES]
    inferred = False
    evidence = ""
    if wishes:
        unsupported = [w for w in wishes if w not in SUPPORTED[kind]]
        wishes = [w for w in wishes if w in SUPPORTED[kind]]
        if not wishes:
            return NoRecommendation(
                "unsupported", f"차에는 아직 '{_labels(unsupported)}' 제안 규칙이 없어요."
            )
    else:
        found = _infer_goals(brew)
        if not found:
            if t.satisfaction is not None and t.satisfaction >= 4:
                return NoRecommendation(
                    "satisfied",
                    f"만족도 {t.satisfaction}점이에요. 지금 레시피를 기준으로 삼고, "
                    "바꾸고 싶은 점이 생기면 '다음에 원하는 변화'를 골라 주세요.",
                )
            return NoRecommendation(
                "unclear",
                "평가만으로는 어느 쪽으로 바꿀지 정하기 어려워요. "
                "기록을 고쳐 '다음에 원하는 변화'를 골라 주세요.",
            )
        wishes = [g for g, _ in found]
        inferred = True
        evidence = " / ".join(e for _, e in found)

    pair = _conflict(set(wishes), kind)
    if pair:
        source = "평가" if inferred else "고른 변화"
        return NoRecommendation(
            "conflict",
            f"{source}에서 {josa(_quoted(sorted(pair, key=PRIORITY.index)), '이')} 서로 반대 방향이에요. "
            "한 번에 하나만 바꿔야 차이를 알 수 있으니, 더 중요한 한 가지만 골라 주세요.",
        )

    ordered = sorted(set(wishes), key=PRIORITY.index)
    goal = ordered[0]
    rule = (_coffee_rule if kind is BeanKind.COFFEE else _tea_rule)(brew, goal)
    if isinstance(rule, NoRecommendation):
        return rule

    extra: list[str] = []
    if inferred:
        extra.append(f"'다음에 원하는 변화'를 고르지 않아 평가를 보고 정했어요 ({evidence}).")
    if len(ordered) > 1:
        extra.append(
            f"이번엔 '{NEXT_WISHES[goal]}'만 반영했어요. 다음엔 {josa(_quoted(ordered[1:]), '을')} 볼게요."
        )
    if rule.note:
        extra.append(rule.note)
    return replace(rule, inferred=inferred, note=" ".join(extra) or None)


# ---- 값 계산 도우미 ---------------------------------------------------------------


def _grind(brew: Brew, goal: str, finer: bool, why: str) -> Recommendation:
    current = brew.recipe.grind
    return Recommendation(
        goal=goal,
        field="grind",
        from_value=current or "기록 없음",
        to_value="조금 더 곱게" if finer else "조금 더 굵게",
        reason=f"{why} {CLOSING}",
        new_recipe=brew.recipe,
        direction_only=True,
        note=None if current else "지금 분쇄도를 적어 두면 다음에 비교하기 쉬워요.",
    )


def _temp(brew: Brew, goal: str, delta: float, why: str) -> Recommendation:
    r = brew.recipe
    assert r.temp_c is not None
    new = r.temp_c + delta
    return Recommendation(
        goal=goal,
        field="temp_c",
        from_value=format_number(r.temp_c, "°C"),
        to_value=format_number(new, "°C"),
        reason=f"{why} {CLOSING}",
        new_recipe=replace(r, temp_c=new),
    )


def _water(brew: Brew, goal: str, factor: float, why: str) -> Recommendation:
    r = brew.recipe
    new = float(round(r.water_g * factor))
    new_recipe = replace(r, water_g=new)
    return Recommendation(
        goal=goal,
        field="water_g",
        from_value=f"{format_number(r.water_g, 'g')} (1:{r.ratio:.1f})",
        to_value=f"{format_number(new, 'g')} (1:{new_recipe.ratio:.1f})",
        reason=f"{why} {CLOSING}",
        new_recipe=new_recipe,
    )


def _dose(brew: Brew, goal: str, factor: float, why: str) -> Recommendation:
    r = brew.recipe
    # 저울로 재기 쉽게 0.5g 단위로, 최소 0.5g은 늘린다
    new = max(r.dose_g + 0.5, round(r.dose_g * factor * 2) / 2)
    return Recommendation(
        goal=goal,
        field="dose_g",
        from_value=format_number(r.dose_g, "g"),
        to_value=format_number(new, "g"),
        reason=f"{why} {CLOSING}",
        new_recipe=replace(r, dose_g=new),
    )


def _time(brew: Brew, goal: str, new_seconds: int, why: str) -> Recommendation:
    r = brew.recipe
    return Recommendation(
        goal=goal,
        field="time_s",
        from_value=format_time(r.time_s),
        to_value=format_time(new_seconds),
        reason=f"{why} {CLOSING}",
        new_recipe=replace(r, time_s=new_seconds),
    )


def _round5(seconds: float) -> int:
    return int(5 * round(seconds / 5))


# ---- 커피 규칙 ------------------------------------------------------------------

COFFEE_TEMP_MIN = 85.0


def _coffee_rule(brew: Brew, goal: str) -> Result:
    r = brew.recipe
    if goal == "less_acid":
        return _grind(
            brew,
            goal,
            True,
            "산미가 튀는 건 덜 추출됐을 때 흔해요. 조금 더 곱게 갈면 추출이 늘어 산미가 둥글어질 수 있어요.",
        )
    if goal == "less_bitter":
        return _grind(
            brew,
            goal,
            False,
            "쓴맛이 강한 건 너무 많이 추출됐을 때 흔해요. 조금 더 굵게 갈면 추출이 줄어 쓴맛이 덜할 수 있어요.",
        )
    if goal == "more_acid":
        if r.temp_c is not None and r.temp_c - 2 >= COFFEE_TEMP_MIN:
            return _temp(
                brew,
                goal,
                -2,
                "물 온도를 조금 낮추면 쓴맛 성분이 덜 녹아 나와 산뜻한 산미가 살아날 수 있어요.",
            )
        return _grind(
            brew,
            goal,
            False,
            "조금 더 굵게 갈면 추출이 가벼워져 산뜻한 느낌이 살아날 수 있어요.",
        )
    if goal == "stronger":
        return _water(
            brew,
            goal,
            0.9,
            "같은 원두량에 물을 10% 줄이면 농도가 올라가 더 진하게 느껴질 수 있어요.",
        )
    if goal == "lighter":
        return _water(
            brew,
            goal,
            1.1,
            "같은 원두량에 물을 10% 늘리면 농도가 내려가 더 가볍게 느껴질 수 있어요.",
        )
    if goal == "sweeter":
        if r.time_s is not None:
            return _time(
                brew,
                goal,
                r.time_s + 15,
                "추출 시간을 15초쯤 늘리면 단맛 성분이 더 녹아 나올 수 있어요. 붓는 속도를 조금 늦춰 보세요.",
            )
        return _grind(
            brew,
            goal,
            True,
            "조금 더 곱게 갈면 단맛 성분이 더 녹아 나올 수 있어요.",
        )
    raise ValueError(goal)


# ---- 차 규칙 -------------------------------------------------------------------

TEA_TEMP_MIN = 60.0
TEA_TIME_MIN = 15


def _tea_rule(brew: Brew, goal: str) -> Result:
    r = brew.recipe
    if goal == "less_bitter":
        if r.temp_c is not None and r.temp_c - 5 >= TEA_TEMP_MIN:
            return _temp(
                brew,
                goal,
                -5,
                "떫은맛·쓴맛은 뜨거운 물에서 더 빨리 우러나요. 물 온도를 5°C 낮춰 보세요.",
            )
        if r.time_s is not None and r.time_s > TEA_TIME_MIN:
            return _time(
                brew,
                goal,
                max(TEA_TIME_MIN, _round5(r.time_s * 0.8)),
                "우리는 시간을 20% 줄이면 떫은맛이 덜 우러날 수 있어요.",
            )
        if r.temp_c is not None or r.time_s is not None:
            return NoRecommendation(
                "limit",
                "이미 온도와 시간이 낮은 편이에요. 찻잎 양을 줄여 볼지 기록을 보며 정해 주세요.",
            )
        return NoRecommendation(
            "missing",
            "떫은맛을 줄이려면 물 온도나 우린 시간이 필요해요. 기록에 수온이나 추출 시간을 넣어 주세요.",
            missing=("temp_c", "time_s"),
        )
    if goal == "stronger":
        if r.time_s is not None:
            return _time(
                brew,
                goal,
                r.time_s + 30,
                "30초 더 우리면 맛이 더 진하게 우러날 수 있어요.",
            )
        return _dose(
            brew,
            goal,
            1.15,
            "찻잎을 15% 늘리면 같은 시간에도 더 진하게 우러날 수 있어요.",
        )
    if goal == "lighter":
        if r.time_s is not None and r.time_s - 30 >= TEA_TIME_MIN:
            return _time(
                brew,
                goal,
                r.time_s - 30,
                "30초 덜 우리면 맛이 더 가볍고 깔끔해질 수 있어요.",
            )
        return _water(
            brew,
            goal,
            1.15,
            "물을 15% 늘리면 맛이 더 가볍게 느껴질 수 있어요.",
        )
    if goal == "sweeter":
        if r.temp_c is not None and r.temp_c - 5 >= TEA_TEMP_MIN:
            return _temp(
                brew,
                goal,
                -5,
                "낮은 온도에서 우리면 쓴맛이 줄고 단맛·감칠맛이 더 드러날 수 있어요.",
            )
        if r.temp_c is None:
            return NoRecommendation(
                "missing",
                "단맛을 끌어내려면 물 온도가 필요해요. 기록에 수온을 넣어 주세요.",
                missing=("temp_c",),
            )
        return NoRecommendation(
            "limit", "이미 낮은 온도로 우렸어요. 다른 차로 비교해 보거나 우린 시간을 바꿔 보세요."
        )
    raise ValueError(goal)
