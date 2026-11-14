"""원두(커피)와 찻잎(차) 모델, 그리고 입력 검증."""

import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class BeanKind(StrEnum):
    COFFEE = "coffee"
    TEA = "tea"


ROAST_LEVELS: dict[str, str] = {
    "light": "라이트",
    "medium_light": "미디엄 라이트",
    "medium": "미디엄",
    "medium_dark": "미디엄 다크",
    "dark": "다크",
    "unknown": "모름",
}

TEA_TYPES: dict[str, str] = {
    "green": "녹차",
    "matcha": "말차",
    "black": "홍차",
    "oolong": "우롱차",
    "white": "백차",
    "puer": "보이차",
    "herbal": "허브티",
    "grain": "곡물차",
    "other": "기타",
}

NAME_MAX = 60
PRODUCER_MAX = 60
ORIGIN_MAX = 40


@dataclass(frozen=True)
class KindLabels:
    """커피와 차에서 같은 항목을 다르게 부르는 이름."""

    title: str
    item: str  # "원두" / "차"
    producer: str
    produced_on: str


LABELS: dict[BeanKind, KindLabels] = {
    BeanKind.COFFEE: KindLabels("커피", "원두", "로스터리", "로스팅된 날짜"),
    BeanKind.TEA: KindLabels("차", "차", "브랜드·찻집", "제조일"),
}


@dataclass(frozen=True)
class BeanDraft:
    """검증을 통과한, 저장할 수 있는 입력값."""

    kind: BeanKind
    name: str
    producer: str | None = None
    produced_on: date | None = None
    roast_level: str | None = None  # 커피만
    tea_type: str | None = None  # 차만
    origin: str | None = None  # 산지 (나라·지역)


@dataclass(frozen=True)
class Bean(BeanDraft):
    id: int = 0
    photo_path: str | None = None
    is_sample: bool = False


class BeanValidationError(ValueError):
    def __init__(self, errors: dict[str, str]):
        super().__init__(", ".join(f"{k}: {v}" for k, v in errors.items()))
        self.errors = errors


_DATE = re.compile(r"^\s*(\d{4})[-./\s]?(\d{1,2})[-./\s]?(\d{1,2})\s*$")


def parse_date(text: str) -> date:
    """'2026-11-01', '2026.11.01', '20261101' 형식을 받아들인다."""
    match = _DATE.match(text)
    if not match:
        raise ValueError("날짜는 2026-11-01처럼 입력해 주세요")
    year, month, day = (int(g) for g in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        raise ValueError("없는 날짜예요") from None


def _blank_to_none(text: str | None) -> str | None:
    if text is None:
        return None
    text = text.strip()
    return text or None


def validate_bean(
    kind: BeanKind,
    name: str | None,
    producer: str | None = None,
    produced_on: str | None = None,
    roast_level: str | None = None,
    tea_type: str | None = None,
    today: date | None = None,
    origin: str | None = None,
) -> BeanDraft:
    """폼 입력을 검사한다. 문제가 있으면 항목별 메시지를 담은 BeanValidationError."""
    today = today or date.today()
    errors: dict[str, str] = {}
    labels = LABELS[kind]

    clean_name = _blank_to_none(name)
    if clean_name is None:
        errors["name"] = f"{labels.item} 이름을 입력해 주세요"
    elif len(clean_name) > NAME_MAX:
        errors["name"] = f"{NAME_MAX}자 이내로 입력해 주세요"

    clean_producer = _blank_to_none(producer)
    if clean_producer and len(clean_producer) > PRODUCER_MAX:
        errors["producer"] = f"{PRODUCER_MAX}자 이내로 입력해 주세요"

    clean_origin = _blank_to_none(origin)
    if clean_origin and len(clean_origin) > ORIGIN_MAX:
        errors["origin"] = f"{ORIGIN_MAX}자 이내로 입력해 주세요"

    parsed_date: date | None = None
    if _blank_to_none(produced_on):
        try:
            parsed_date = parse_date(produced_on or "")
        except ValueError as e:
            errors["produced_on"] = str(e)
        else:
            if parsed_date > today:
                errors["produced_on"] = "미래 날짜는 입력할 수 없어요"

    level = _blank_to_none(roast_level)
    ttype = _blank_to_none(tea_type)
    if kind is BeanKind.COFFEE:
        if level is not None and level not in ROAST_LEVELS:
            errors["roast_level"] = "로스팅 정도를 목록에서 골라 주세요"
        ttype = None
    else:
        if ttype is not None and ttype not in TEA_TYPES:
            errors["tea_type"] = "차 종류를 목록에서 골라 주세요"
        level = None

    if errors:
        raise BeanValidationError(errors)
    assert clean_name is not None
    return BeanDraft(
        kind=kind,
        name=clean_name,
        producer=clean_producer,
        produced_on=parsed_date,
        roast_level=level,
        tea_type=ttype,
        origin=clean_origin,
    )
