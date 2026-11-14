"""시음 후 향(냄새) 평가: 향 계열과 세부 향.

커피 테이스터 플레이버 휠처럼 큰 계열(꽃, 과일, 단 향 ...)을 먼저 고르고, 그 안의 세부 향을 고른다.
휠 그림을 옮긴 것이 아니라, 커피·차 시음에서 흔히 쓰는 낱말로 SENSO가 따로 정리한 목록이다.
색은 화면에서 계열을 구분하는 데 쓴다 (휠의 색 구분처럼).
"""

from dataclasses import dataclass

from senso.domain.bean import BeanKind


@dataclass(frozen=True)
class AromaGroup:
    key: str
    label: str
    color: str  # 칩 테두리·점 색
    notes: tuple[str, ...]


COFFEE_AROMAS: tuple[AromaGroup, ...] = (
    AromaGroup("floral", "꽃", "#C2668F", ("자스민", "장미", "오렌지 꽃", "라벤더", "홍차 같은")),
    AromaGroup(
        "berry", "베리", "#9C2F55", ("블루베리", "딸기", "라즈베리", "블랙베리", "크랜베리")
    ),
    AromaGroup("citrus", "시트러스", "#E0A321", ("레몬", "오렌지", "자몽", "라임", "귤")),
    AromaGroup("fruit", "과일", "#E0713F", ("복숭아", "살구", "체리", "사과", "포도", "열대과일")),
    AromaGroup("sweet", "단 향", "#C98236", ("캐러멜", "꿀", "흑설탕", "메이플 시럽", "바닐라")),
    AromaGroup("chocolate", "초콜릿", "#6B3E26", ("다크 초콜릿", "밀크 초콜릿", "코코아")),
    AromaGroup("nutty", "견과", "#A57A4C", ("아몬드", "헤이즐넛", "땅콩", "호두")),
    AromaGroup("spice", "향신료", "#A2452A", ("시나몬", "정향", "후추", "육두구")),
    AromaGroup("roasted", "구운 향", "#5B4535", ("토스트", "곡물", "스모키", "탄 향")),
    AromaGroup("green", "풀·허브", "#5F8A45", ("풀", "허브", "토마토", "완두콩")),
    AromaGroup("earthy", "흙·나무", "#7A6A55", ("흙", "나무", "담배", "가죽")),
    AromaGroup("ferment", "발효", "#7D3F6B", ("와인", "럼", "식초", "발효 과일")),
)

TEA_AROMAS: tuple[AromaGroup, ...] = (
    AromaGroup("floral", "꽃", "#C2668F", ("자스민", "난초", "장미", "국화", "계화")),
    AromaGroup("fruit", "과일", "#E0713F", ("복숭아", "사과", "감귤", "머스캣", "말린 과일")),
    AromaGroup("green", "풀·채소", "#5F8A45", ("새싹", "풀", "시금치", "완두콩")),
    AromaGroup("marine", "바다", "#2E6F8E", ("김", "해초")),
    AromaGroup("nutty", "구수함", "#A57A4C", ("볶은 곡물", "밤", "누룽지", "견과")),
    AromaGroup("sweet", "단 향", "#C98236", ("꿀", "캐러멜", "고구마")),
    AromaGroup("woody", "나무·흙", "#7A6A55", ("나무", "흙", "이끼", "묵은 향")),
    AromaGroup("smoky", "연기", "#5B4535", ("훈연", "탄 향")),
    AromaGroup("spice", "향신료·허브", "#A2452A", ("민트", "시나몬", "생강")),
)

AROMAS: dict[BeanKind, tuple[AromaGroup, ...]] = {
    BeanKind.COFFEE: COFFEE_AROMAS,
    BeanKind.TEA: TEA_AROMAS,
}

AROMA_INTENSITY = ("향 세기", "약함", "강함")


def groups_by_key(kind: BeanKind) -> dict[str, AromaGroup]:
    return {g.key: g for g in AROMAS[kind]}


def group_of(kind: BeanKind, note: str) -> AromaGroup | None:
    for g in AROMAS[kind]:
        if note in g.notes:
            return g
    return None


def clean_aromas(
    kind: BeanKind, groups: list[str] | tuple[str, ...], notes: list[str] | tuple[str, ...]
) -> tuple[tuple[str, ...], tuple[str, ...], list[str]]:
    """고른 계열·세부 향을 정리한다. 세부 향을 고르면 그 계열도 고른 것으로 친다.

    돌려주는 값: (계열들, 세부 향들, 알 수 없는 값들). 순서는 목록 순서를 따른다.
    """
    known = groups_by_key(kind)
    unknown = [g for g in groups if g and g not in known]
    chosen_notes: list[str] = []
    chosen_groups = {g for g in groups if g in known}
    for n in notes:
        if not n:
            continue
        g = group_of(kind, n)
        if g is None:
            unknown.append(n)
            continue
        chosen_notes.append(n)
        chosen_groups.add(g.key)
    ordered_groups = tuple(g.key for g in AROMAS[kind] if g.key in chosen_groups)
    ordered_notes = tuple(n for g in AROMAS[kind] for n in g.notes if n in set(chosen_notes))
    return ordered_groups, ordered_notes, unknown


def describe(kind: BeanKind, groups: tuple[str, ...], notes: tuple[str, ...]) -> str:
    """'과일(복숭아·사과) · 꽃' 처럼 한 줄로."""
    known = groups_by_key(kind)
    parts = []
    for key in groups:
        g = known.get(key)
        if g is None:
            continue
        inner = [n for n in notes if n in g.notes]
        parts.append(f"{g.label}({'·'.join(inner)})" if inner else g.label)
    return " · ".join(parts)
