"""산지 → 나라 → 국기.

산지 칸(없으면 이름)에서 나라를 찾는다. '에티오피아 예가체프'는 🇪🇹, '제주 세작'은 🇰🇷.
국기는 이모지로 그린다 (이미지 파일이 필요 없다).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    code: str  # ISO 3166-1 alpha-2
    name: str

    @property
    def flag(self) -> str:
        return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in self.code)


# (나라 코드, 한국어 이름, 찾을 낱말들). 낱말은 나라 이름과 대표 산지·품종 이름.
# 헷갈리기 쉬운 낱말(모카, 게이샤, 하라 등)은 넣지 않는다.
_TABLE: list[tuple[str, str, tuple[str, ...]]] = [
    # 아프리카·중동
    (
        "ET",
        "에티오피아",
        (
            "에티오피아",
            "예가체프",
            "시다모",
            "구지",
            "리무",
            "ethiopia",
            "yirgacheffe",
            "sidamo",
            "guji",
        ),
    ),
    ("KE", "케냐", ("케냐", "kenya")),
    ("RW", "르완다", ("르완다", "rwanda")),
    ("BI", "부룬디", ("부룬디", "burundi")),
    ("TZ", "탄자니아", ("탄자니아", "킬리만자로", "tanzania", "kilimanjaro")),
    ("UG", "우간다", ("우간다", "uganda")),
    ("MW", "말라위", ("말라위", "malawi")),
    ("CD", "콩고", ("콩고", "congo")),
    ("YE", "예멘", ("예멘", "yemen")),
    # 중남미
    ("CO", "콜롬비아", ("콜롬비아", "수프리모", "colombia", "supremo")),
    ("BR", "브라질", ("브라질", "산토스", "세라도", "brazil", "santos", "cerrado")),
    ("GT", "과테말라", ("과테말라", "안티구아", "우에우에테낭고", "guatemala", "antigua")),
    ("CR", "코스타리카", ("코스타리카", "타라주", "costa rica", "tarrazu")),
    ("PA", "파나마", ("파나마", "보케테", "panama", "boquete")),
    ("HN", "온두라스", ("온두라스", "honduras")),
    ("SV", "엘살바도르", ("엘살바도르", "el salvador")),
    ("NI", "니카라과", ("니카라과", "nicaragua")),
    ("MX", "멕시코", ("멕시코", "치아파스", "mexico", "chiapas")),
    ("PE", "페루", ("페루", "peru")),
    ("BO", "볼리비아", ("볼리비아", "bolivia")),
    ("EC", "에콰도르", ("에콰도르", "ecuador")),
    ("JM", "자메이카", ("자메이카", "블루마운틴", "jamaica", "blue mountain")),
    ("US", "미국(하와이)", ("하와이", "코나", "hawaii", "kona")),
    # 아시아·태평양
    (
        "ID",
        "인도네시아",
        (
            "인도네시아",
            "만델링",
            "수마트라",
            "토라자",
            "자바",
            "indonesia",
            "mandheling",
            "sumatra",
            "toraja",
        ),
    ),
    ("PG", "파푸아뉴기니", ("파푸아뉴기니", "papua new guinea")),
    ("VN", "베트남", ("베트남", "vietnam")),
    ("TH", "태국", ("태국", "thailand")),
    ("LA", "라오스", ("라오스", "laos")),
    ("MM", "미얀마", ("미얀마", "myanmar")),
    ("IN", "인도", ("인도", "다즐링", "아쌈", "닐기리", "india", "darjeeling", "assam", "nilgiri")),
    ("LK", "스리랑카", ("스리랑카", "실론", "누와라엘리야", "sri lanka", "ceylon")),
    ("NP", "네팔", ("네팔", "nepal")),
    (
        "CN",
        "중국",
        (
            "중국",
            "운남",
            "윈난",
            "보이차",
            "철관음",
            "안계",
            "무이",
            "용정",
            "룽징",
            "기문",
            "china",
            "yunnan",
            "pu-erh",
            "puer",
        ),
    ),
    ("TW", "대만", ("대만", "타이완", "아리산", "동방미인", "taiwan", "alishan")),
    ("JP", "일본", ("일본", "우지", "시즈오카", "japan", "uji", "shizuoka")),
    ("KR", "대한민국", ("대한민국", "한국", "국산", "제주", "보성", "하동", "korea", "jeju")),
]

COUNTRIES: dict[str, Country] = {code: Country(code, name) for code, name, _ in _TABLE}

# 긴 낱말부터 본다: '인도네시아'가 '인도'보다 먼저 걸리도록
_KEYWORDS: list[tuple[str, Country]] = sorted(
    ((kw.lower(), COUNTRIES[code]) for code, _, kws in _TABLE for kw in kws),
    key=lambda pair: -len(pair[0]),
)


def find_country(text: str | None) -> Country | None:
    """글에서 가장 앞에 나오는 나라. 같은 자리면 더 긴 낱말이 이긴다."""
    if not text:
        return None
    lowered = text.lower()
    best: tuple[int, int, Country] | None = None
    for kw, country in _KEYWORDS:
        i = lowered.find(kw)
        if i < 0:
            continue
        rank = (i, -len(kw))
        if best is None or rank < best[:2]:
            best = (i, -len(kw), country)
    return best[2] if best else None


def country_of(origin: str | None, name: str | None = None) -> Country | None:
    """산지 칸을 먼저 보고, 없거나 못 찾으면 이름에서 찾는다."""
    return find_country(origin) or find_country(name)


def with_flag(name: str, origin: str | None = None) -> str:
    """'🇪🇹 에티오피아 예가체프'. 나라를 못 찾으면 이름 그대로."""
    country = country_of(origin, name)
    return f"{country.flag} {name}" if country else name
