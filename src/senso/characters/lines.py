"""Sen & So 대사 모음.

- Sen(센): 커피. 장난스럽고 실험을 좋아하는 바리스타. 반말 섞인 친근한 말투.
- So(소): 차. 차분하고 다정한 티 소믈리에. 부드러운 존댓말.

대사는 템플릿이다(AI 아님). 시간과 상황에 따라 고른다.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from senso.domain.bean import BeanKind
from senso.recommend.engine import Recommendation, Result

CAFFEINE_CUTOFF_HOUR = 15  # 오후 3시 이후엔 So가 카페인을 챙긴다


class Who(StrEnum):
    SEN = "sen"
    SO = "so"
    DUO = "duo"


NAMES = {Who.SEN: "Sen", Who.SO: "So", Who.DUO: "Sen & So"}


@dataclass(frozen=True)
class Line:
    who: Who
    text: str


def for_kind(kind: BeanKind) -> Who:
    return Who.SEN if kind is BeanKind.COFFEE else Who.SO


def home_greeting(now: datetime, brew_count: int) -> Line:
    h = now.hour
    if brew_count == 0:
        return Line(
            Who.DUO,
            "반가워요! 우리는 Sen과 So예요. 첫 한 잔을 기록하면 다음 한 잔을 같이 찾아 줄게요.",
        )
    if h >= CAFFEINE_CUTOFF_HOUR + 6 or h < 5:
        return Line(
            Who.SO, "늦은 시간이에요. 오늘은 카페인 없는 보리차나 허브티로 하루를 마무리해 볼까요?"
        )
    if h >= CAFFEINE_CUTOFF_HOUR:
        return Line(Who.SO, "오후 3시가 지났어요. 편한 잠을 위해 디카페인 커피나 보리차는 어때요?")
    if h < 11:
        return Line(
            Who.SEN,
            "좋은 아침! 오늘 첫 잔은 뭐로 할까? 기록해 두면 내가 다음 레시피를 고민해 볼게.",
        )
    return Line(Who.SEN, "점심 먹고 한 잔 어때? 지난번 기록이랑 비교해 보면 재밌을 거야.")


def beans_greeting(kind: BeanKind, count: int) -> Line:
    if kind is BeanKind.COFFEE:
        if count == 0:
            return Line(
                Who.SEN,
                "원두를 등록해 줘! 로스팅 날짜를 적어 두면 맛이 변하는 것도 같이 볼 수 있어.",
            )
        return Line(Who.SEN, f"원두가 {count}개 있네. 오늘은 어떤 걸로 실험해 볼까?")
    if count == 0:
        return Line(Who.SO, "좋아하는 차를 등록해 주세요. 시간대에 맞는 차를 골라 드릴게요.")
    return Line(Who.SO, f"차가 {count}가지 있어요. 오늘 기분에 맞는 차를 골라 봐요.")


def recommendation_line(kind: BeanKind, result: Result) -> Line:
    who = for_kind(kind)
    sen = who is Who.SEN
    if isinstance(result, Recommendation):
        if sen:
            return Line(
                who,
                f"이번엔 {result.field_label}만 바꿔 보자! 나머지는 그대로 두는 게 비교의 핵심이야.",
            )
        return Line(
            who,
            f"이번에는 {result.field_label}만 살짝 바꿔 봐요. 천천히 비교하면 차이가 보일 거예요.",
        )
    if result.kind == "satisfied":
        return Line(
            who,
            "지금 레시피 좋은데? 한 번 더 내려서 같은 맛이 나는지 보자."
            if sen
            else "지금 그대로도 좋아요. 이 맛을 기억해 둘게요.",
        )
    if result.kind == "no_tasting":
        return Line(
            who,
            "마셔 보고 어땠는지 알려 줘. 그래야 내가 머리를 굴려 보지!"
            if sen
            else "마셔 보신 뒤 느낌을 알려 주세요. 그다음에 함께 고민해요.",
        )
    if result.kind == "conflict":
        return Line(
            who,
            "음, 두 가지가 반대 방향이야. 하나만 골라 주면 바로 실험 들어갈게!"
            if sen
            else "두 가지 바람이 서로 반대예요. 더 중요한 하나만 골라 주세요.",
        )
    return Line(
        who,
        "조금만 더 알려 주면 제안할 수 있어!" if sen else "조금만 더 알려 주시면 제안해 드릴게요.",
    )


def brew_again_line(kind: BeanKind, rec: Recommendation) -> Line:
    who = for_kind(kind)
    what = f"{rec.field_label}: {rec.from_value} → {rec.to_value}"
    if who is Who.SEN:
        return Line(who, f"좋아, 실험 시작! {what}. 내리고 나서 평가도 꼭 남겨 줘.")
    return Line(who, f"이번엔 {what}. 마셔 보시고 느낌을 남겨 주세요.")


def compare_line(kind: BeanKind, before_score: int | None, after_score: int | None) -> Line:
    who = for_kind(kind)
    if before_score is None or after_score is None:
        return Line(
            who,
            "두 기록을 나란히 놓고 보자. 평가가 있으면 차이가 더 잘 보여!"
            if who is Who.SEN
            else "두 기록을 나란히 놓고 봐요. 평가를 남기면 차이가 더 잘 보여요.",
        )
    if after_score > before_score:
        return Line(
            who,
            f"만족도가 {before_score}점에서 {after_score}점으로 올랐어! 이 방향이 맞나 봐."
            if who is Who.SEN
            else f"만족도가 {before_score}점에서 {after_score}점으로 올랐어요. 좋은 방향이에요.",
        )
    if after_score < before_score:
        return Line(
            who,
            "이번엔 오히려 아쉬웠구나. 괜찮아, 이것도 중요한 실험 결과야."
            if who is Who.SEN
            else "이번엔 조금 아쉬웠네요. 원래 레시피로 돌아가도 괜찮아요.",
        )
    return Line(
        who,
        "만족도는 같네. 맛 점수에서 달라진 걸 찾아보자."
        if who is Who.SEN
        else "만족도는 같아요. 어떤 맛이 달라졌는지 살펴봐요.",
    )


__all__ = [
    "Line",
    "Who",
    "NAMES",
    "for_kind",
    "home_greeting",
    "beans_greeting",
    "recommendation_line",
    "brew_again_line",
    "compare_line",
]
