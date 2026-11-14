"""추출·시음 기록 모델과 입력 검증.

한 기록은 세 부분으로 나뉜다.
- 추출 전: 원두, 오늘 원하는 맛, 따뜻하게/아이스, 도구, 레시피(Recipe)
- 시음 후: 맛 점수와 메모(Tasting). 비워 두고 나중에 추가할 수 있다
- 연결: 어떤 기록·추천을 보고 만든 기록인지
"""

import re
from dataclasses import dataclass, field, replace
from datetime import datetime

from senso.domain.aroma import clean_aromas
from senso.domain.bean import Bean, BeanKind

# ---- 선택지 ------------------------------------------------------------------

DESIRED_FLAVORS: dict[BeanKind, list[str]] = {
    BeanKind.COFFEE: ["초콜릿", "견과류", "과일", "꽃향", "산뜻함", "묵직함", "단맛"],
    BeanKind.TEA: ["구수함", "꽃향", "과일향", "풀향", "산뜻함", "묵직함", "단맛"],
}

# 다음에 원하는 변화. 추천 엔진이 이 값을 먼저 본다.
NEXT_WISHES: dict[str, str] = {
    "less_acid": "산미 줄이기",
    "more_acid": "더 산뜻하게",
    "less_bitter": "쓴맛·떫은맛 줄이기",
    "stronger": "더 진하게",
    "lighter": "더 가볍게",
    "sweeter": "단맛 더",
    "keep": "이대로 좋아요",
}
WISHES_BY_KIND: dict[BeanKind, list[str]] = {
    BeanKind.COFFEE: [
        "less_acid",
        "more_acid",
        "less_bitter",
        "stronger",
        "lighter",
        "sweeter",
        "keep",
    ],
    BeanKind.TEA: ["less_bitter", "stronger", "lighter", "sweeter", "keep"],
}

SCORE_FIELDS: dict[str, tuple[str, str, str]] = {
    # 이름: (표시 이름, 1점 쪽, 5점 쪽)
    "acidity": ("산미", "약함", "강함"),
    "bitterness": ("쓴맛", "약함", "강함"),
    "sweetness": ("단맛", "약함", "강함"),
    "body": ("바디", "가벼움", "묵직함"),
    "satisfaction": ("만족도", "불만족", "만족"),
}

LIMITS = {
    "dose_g": (0.1, 100.0),
    "water_g": (1.0, 2000.0),
    "temp_c": (0.0, 100.0),
    "ice_g": (0.0, 1000.0),
    "time_s": (0, 3600),
}


# ---- 모델 --------------------------------------------------------------------


@dataclass(frozen=True)
class Recipe:
    dose_g: float
    water_g: float
    temp_c: float | None = None
    grind: str | None = None  # 그라인더마다 표기가 달라 문자열
    time_s: int | None = None
    ice_g: float | None = None

    @property
    def ratio(self) -> float:
        """물 / 원두 (예: 16.7 → 1:16.7)."""
        return self.water_g / self.dose_g


@dataclass(frozen=True)
class Tasting:
    acidity: int | None = None
    bitterness: int | None = None
    sweetness: int | None = None
    body: int | None = None
    satisfaction: int | None = None
    notes: str | None = None
    next_wish: tuple[str, ...] = ()
    next_memo: str | None = None
    # 향(냄새) 평가: 세기, 계열 키, 세부 향 (senso.domain.aroma)
    aroma_intensity: int | None = None
    aromas: tuple[str, ...] = ()
    aroma_notes: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        scores = (self.acidity, self.bitterness, self.sweetness, self.body, self.satisfaction)
        return all(s is None for s in scores) and not (
            self.notes
            or self.next_wish
            or self.next_memo
            or self.aroma_intensity
            or self.aromas
            or self.aroma_notes
        )


@dataclass(frozen=True)
class BeanSnapshot:
    """기록 당시의 원두 정보. 원두를 나중에 고치거나 지워도 기록은 그대로다."""

    name: str
    kind: BeanKind
    producer: str | None = None
    roast_level: str | None = None
    tea_type: str | None = None
    produced_on: str | None = None
    origin: str | None = None

    @classmethod
    def of(cls, bean: Bean) -> "BeanSnapshot":
        return cls(
            name=bean.name,
            kind=bean.kind,
            producer=bean.producer,
            roast_level=bean.roast_level,
            tea_type=bean.tea_type,
            produced_on=bean.produced_on.isoformat() if bean.produced_on else None,
            origin=bean.origin,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "producer": self.producer,
            "roast_level": self.roast_level,
            "tea_type": self.tea_type,
            "produced_on": self.produced_on,
            "origin": self.origin,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BeanSnapshot":
        return cls(
            name=data.get("name") or "이름 없는 원두",
            kind=BeanKind(data.get("kind") or "coffee"),
            producer=data.get("producer"),
            roast_level=data.get("roast_level"),
            tea_type=data.get("tea_type"),
            produced_on=data.get("produced_on"),
            origin=data.get("origin"),
        )


@dataclass(frozen=True)
class BrewDraft:
    bean_id: int | None
    bean: BeanSnapshot
    recipe: Recipe
    desired_flavors: tuple[str, ...] = ()
    iced: bool = False
    dripper: str | None = None  # 추출 도구 (드리퍼, 다관 ...)
    grinder: str | None = None
    notes: str | None = None
    tasting: Tasting = field(default_factory=Tasting)
    based_on_brew_id: int | None = None
    based_on_rec_id: int | None = None

    @property
    def kind(self) -> BeanKind:
        return self.bean.kind


@dataclass(frozen=True)
class Brew(BrewDraft):
    id: int = 0
    brewed_at: datetime = datetime(2000, 1, 1)
    is_sample: bool = False

    def with_tasting(self, tasting: Tasting) -> "Brew":
        return replace(self, tasting=tasting)


# ---- 검증 --------------------------------------------------------------------


class BrewValidationError(ValueError):
    def __init__(self, errors: dict[str, str]):
        super().__init__(", ".join(f"{k}: {v}" for k, v in errors.items()))
        self.errors = errors


_TIME_MMSS = re.compile(r"^\s*(\d{1,2})\s*[:분]\s*(\d{1,2})\s*초?\s*$")
_TIME_MIN = re.compile(r"^\s*(\d{1,2})\s*분\s*$")
_TIME_SEC = re.compile(r"^\s*(\d{1,4})\s*초?\s*$")


def parse_time(text: str) -> int:
    """'3:20', '3분 20초', '3분', '200', '200초' → 초."""
    if m := _TIME_MMSS.match(text):
        minutes, seconds = int(m.group(1)), int(m.group(2))
        if seconds >= 60:
            raise ValueError("초는 0~59로 입력해 주세요")
        return minutes * 60 + seconds
    if m := _TIME_MIN.match(text):
        return int(m.group(1)) * 60
    if m := _TIME_SEC.match(text):
        return int(m.group(1))
    raise ValueError("3:20 또는 200(초)처럼 입력해 주세요")


def format_time(seconds: int | None) -> str:
    if seconds is None:
        return "-"
    return f"{seconds // 60}:{seconds % 60:02d}"


def format_number(value: float | None, unit: str = "") -> str:
    if value is None:
        return "-"
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{text}{unit}"


def _blank(text: str | None) -> str | None:
    if text is None:
        return None
    text = text.strip()
    return text or None


def _number(
    raw: str | None, key: str, label: str, errors: dict[str, str], required: bool = False
) -> float | None:
    text = _blank(raw)
    if text is None:
        if required:
            errors[key] = f"{label}을 입력해 주세요"  # 원두량·물양 모두 받침으로 끝남
        return None
    try:
        value = float(text.replace(",", "."))
    except ValueError:
        errors[key] = "숫자로 입력해 주세요"
        return None
    low, high = LIMITS[key]
    if not (low <= value <= high):
        errors[key] = f"{format_number(low)}~{format_number(high)} 사이로 입력해 주세요"
        return None
    return value


def _score(value: int | None, key: str, errors: dict[str, str]) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or not 1 <= value <= 5:
        errors[key] = "1~5점 중에서 골라 주세요"
        return None
    return value


def validate_brew(
    *,
    bean: Bean | BeanSnapshot | None,
    bean_id: int | None,
    dose_g: str | None,
    water_g: str | None,
    temp_c: str | None = None,
    grind: str | None = None,
    time: str | None = None,
    ice_g: str | None = None,
    iced: bool = False,
    desired_flavors: list[str] | tuple[str, ...] = (),
    dripper: str | None = None,
    grinder: str | None = None,
    notes: str | None = None,
    scores: dict[str, int | None] | None = None,
    tasting_notes: str | None = None,
    next_wish: list[str] | tuple[str, ...] = (),
    next_memo: str | None = None,
    aroma_intensity: int | None = None,
    aromas: list[str] | tuple[str, ...] = (),
    aroma_notes: list[str] | tuple[str, ...] = (),
    based_on_brew_id: int | None = None,
    based_on_rec_id: int | None = None,
) -> BrewDraft:
    """폼 입력을 검사한다. 원두·원두량·물양만 필수이고 나머지는 비워도 된다."""
    errors: dict[str, str] = {}

    if bean is None:
        errors["bean"] = "원두나 차를 골라 주세요"
        snapshot = None
    else:
        snapshot = bean if isinstance(bean, BeanSnapshot) else BeanSnapshot.of(bean)

    dose = _number(dose_g, "dose_g", "원두량", errors, required=True)
    water = _number(water_g, "water_g", "물양", errors, required=True)
    temp = _number(temp_c, "temp_c", "수온", errors)
    ice = _number(ice_g, "ice_g", "얼음량", errors) if iced else None

    seconds: int | None = None
    if _blank(time):
        try:
            seconds = parse_time(time or "")
        except ValueError as e:
            errors["time_s"] = str(e)
        else:
            if seconds > LIMITS["time_s"][1]:
                errors["time_s"] = "1시간 이내로 입력해 주세요"

    scores = scores or {}
    unknown = set(scores) - set(SCORE_FIELDS)
    if unknown:
        raise ValueError(f"알 수 없는 점수 항목: {unknown}")
    checked = {k: _score(scores.get(k), k, errors) for k in SCORE_FIELDS}

    wishes = tuple(dict.fromkeys(w for w in next_wish if w))  # 순서 유지, 중복 제거
    if bad := [w for w in wishes if w not in NEXT_WISHES]:
        errors["next_wish"] = f"알 수 없는 선택: {', '.join(bad)}"
    if "keep" in wishes and len(wishes) > 1:
        errors["next_wish"] = "'이대로 좋아요'는 다른 변화와 함께 고를 수 없어요"

    intensity = _score(aroma_intensity, "aroma_intensity", errors)
    aroma_groups: tuple[str, ...] = ()
    aroma_picked: tuple[str, ...] = ()
    if snapshot is not None:
        aroma_groups, aroma_picked, bad_aromas = clean_aromas(
            snapshot.kind, tuple(aromas), tuple(aroma_notes)
        )
        if bad_aromas:
            errors["aromas"] = f"알 수 없는 향: {', '.join(bad_aromas)}"

    if errors:
        raise BrewValidationError(errors)
    assert snapshot is not None and dose is not None and water is not None

    return BrewDraft(
        bean_id=bean_id,
        bean=snapshot,
        recipe=Recipe(
            dose_g=dose,
            water_g=water,
            temp_c=temp,
            grind=_blank(grind) if snapshot.kind is BeanKind.COFFEE else None,
            time_s=seconds,
            ice_g=ice,
        ),
        desired_flavors=tuple(dict.fromkeys(f for f in desired_flavors if f)),
        iced=iced,
        dripper=_blank(dripper),
        grinder=_blank(grinder) if snapshot.kind is BeanKind.COFFEE else None,
        notes=_blank(notes),
        tasting=Tasting(
            **checked,
            notes=_blank(tasting_notes),
            next_wish=wishes,
            next_memo=_blank(next_memo),
            aroma_intensity=intensity,
            aromas=aroma_groups,
            aroma_notes=aroma_picked,
        ),
        based_on_brew_id=based_on_brew_id,
        based_on_rec_id=based_on_rec_id,
    )
