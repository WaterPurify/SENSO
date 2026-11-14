"""Taste DNA v0: 기록에서 맛 선호를 계산한다.

방법 (설명할 수 있는 단순한 계산):
- 만족도를 매긴 '직접 남긴' 기록만 쓴다 (예시 데이터 제외).
- 기록이 MIN_BREWS개 이상일 때만 계산한다.
- 맛 항목(산미·쓴맛·단맛·바디)마다, 만족도 4~5점 기록의 평균과
  나머지 기록의 평균을 비교해 '좋아하는 쪽'을 정한다.
- 차이가 작으면(±0.5 미만) '상관없음'으로 둔다. 억지로 결론 내지 않는다.
- 근거로 만족도가 가장 높은 기록 몇 개를 함께 보여 준다.
"""

from collections import Counter
from dataclasses import dataclass

from senso.domain.aroma import groups_by_key
from senso.domain.bean import BeanKind
from senso.domain.brew import SCORE_FIELDS, Brew
from senso.text import josa

MIN_BREWS = 5
LIKED = 4  # 만족도 4점 이상을 '좋았던 기록'으로 본다
THRESHOLD = 0.5
TRAITS = ("acidity", "bitterness", "sweetness", "body")


@dataclass(frozen=True)
class Trait:
    key: str
    label: str
    liked_avg: float | None  # 좋았던 기록의 평균 (1~5)
    other_avg: float | None
    count: int  # 이 항목 점수가 있는 기록 수
    direction: str  # "high" | "low" | "neutral" | "unknown"
    sentence: str


@dataclass(frozen=True)
class TasteDNA:
    rated: int  # 만족도를 매긴 기록 수
    liked: int
    traits: tuple[Trait, ...]
    coffee_share: float  # 0~1
    top_flavors: tuple[str, ...]
    evidence: tuple[Brew, ...]  # 만족도가 높은 기록 (근거)
    top_aromas: tuple[str, ...] = ()  # 좋았던 기록에서 자주 고른 향 계열 (이름)


@dataclass(frozen=True)
class NotEnough:
    rated: int
    needed: int = MIN_BREWS


def _avg(values: list[int]) -> float | None:
    return sum(values) / len(values) if values else None


def _sentence(key: str, direction: str) -> str:
    label, low, high = SCORE_FIELDS[key]
    if direction in ("high", "low"):
        side = high if direction == "high" else low
        if key == "body":
            return f"바디가 {side} 쪽일 때 더 만족했어요"
        return f"{josa(label, '이')} {side} 쪽일 때 더 만족했어요"
    if direction == "neutral":
        return f"{josa(label, '은')} 만족도와 큰 관계가 없었어요"
    return f"{label} 점수가 아직 부족해요"


def _trait(key: str, liked: list[Brew], others: list[Brew]) -> Trait:
    lv = [getattr(b.tasting, key) for b in liked if getattr(b.tasting, key) is not None]
    ov = [getattr(b.tasting, key) for b in others if getattr(b.tasting, key) is not None]
    la, oa = _avg(lv), _avg(ov)
    if la is None:
        direction = "unknown"
    elif oa is None:
        # 비교할 '덜 좋았던' 기록이 없으면 좋았던 기록의 평균만으로 본다
        direction = "high" if la >= 3 + THRESHOLD else "low" if la <= 3 - THRESHOLD else "neutral"
    else:
        diff = la - oa
        direction = "high" if diff >= THRESHOLD else "low" if diff <= -THRESHOLD else "neutral"
    return Trait(
        key=key,
        label=SCORE_FIELDS[key][0],
        liked_avg=la,
        other_avg=oa,
        count=len(lv) + len(ov),
        direction=direction,
        sentence=_sentence(key, direction),
    )


def compute(brews: list[Brew]) -> TasteDNA | NotEnough:
    rated = [b for b in brews if not b.is_sample and b.tasting.satisfaction is not None]
    if len(rated) < MIN_BREWS:
        return NotEnough(rated=len(rated))

    liked = [b for b in rated if b.tasting.satisfaction >= LIKED]
    others = [b for b in rated if b.tasting.satisfaction < LIKED]
    if not liked:
        # 좋았던 기록이 없으면 상대적으로 나았던 절반을 기준으로 삼는다
        ordered = sorted(rated, key=lambda b: b.tasting.satisfaction, reverse=True)
        top = ordered[0].tasting.satisfaction
        liked = [b for b in rated if b.tasting.satisfaction == top]
        others = [b for b in rated if b.tasting.satisfaction < top]

    flavors = Counter(f for b in liked for f in b.desired_flavors)
    aromas = Counter(
        group.label
        for b in liked
        for key in b.tasting.aromas
        if (group := groups_by_key(b.kind).get(key))
    )
    coffee = sum(1 for b in rated if b.kind is BeanKind.COFFEE)
    evidence = sorted(liked, key=lambda b: (b.tasting.satisfaction, b.brewed_at), reverse=True)

    return TasteDNA(
        rated=len(rated),
        liked=len(liked),
        traits=tuple(_trait(k, liked, others) for k in TRAITS),
        coffee_share=coffee / len(rated),
        top_flavors=tuple(f for f, _ in flavors.most_common(3)),
        evidence=tuple(evidence[:3]),
        top_aromas=tuple(a for a, _ in aromas.most_common(3)),
    )
