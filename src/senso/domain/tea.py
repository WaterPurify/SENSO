"""차 종류별로 알려진 특징(성분·카페인·우리는 법).

출처: 나무위키 '차' 문서(2026-11-12 판)의 '차의 효능'·'차의 종류'·'차를 우리는 방법'을 SENSO가 짧게 요약했다.
(나무위키 문서는 CC BY-NC-SA 2.0 KR. 문장을 옮기지 않고 내용만 요약.) 카페인 정도와 허브·곡물차의
'카페인 없음'은 일반적으로 알려진 내용을 덧붙였다.

의학적 효능을 약속하는 문구가 아니다. 화면에는 항상 DISCLAIMER를 함께 보여 준다.
나무위키는 스스로 '검증되지 않은 서술이 있을 수 있다'고 밝히므로, 출시 전 전문 자료로 다시 확인할 것.
"""

from dataclasses import dataclass

SOURCE = "나무위키 '차' 문서 요약 (CC BY-NC-SA 2.0 KR)"
DISCLAIMER = "알려진 성분과 특징을 정리한 것으로, 질병의 예방·치료 효과를 뜻하지 않아요."


@dataclass(frozen=True)
class TeaInfo:
    caffeine: str  # "많음" | "중간" | "적은 편" | "없음(대부분)"
    components: tuple[str, ...]  # 대표 성분
    points: tuple[str, ...]  # 알려진 특징 (짧은 문장)
    brew_tip: str


# 차나무 잎으로 만든 차의 공통 특징 (녹차·말차·홍차·우롱차·백차·보이차)
COMMON_TEA_POINTS = (
    "플라보노이드·카테킨 같은 폴리페놀이 들어 있어 항산화 성분으로 알려져 있어요.",
    "카테킨이 카페인이 몸에 흡수되는 속도를 늦춰, 커피보다 카페인 부담이 덜한 편이라고 해요.",
)

TEA_INFO: dict[str, TeaInfo] = {
    "green": TeaInfo(
        caffeine="중간",
        components=("카테킨", "테아닌", "카페인"),
        points=(
            "찻잎을 따자마자 가열해 산화를 막은 차라 초록빛과 풀 향이 살아 있어요.",
            "테아닌은 마음을 차분하게 하는 데 도움을 주는 성분으로 알려져 있어요.",
            *COMMON_TEA_POINTS,
        ),
        brew_tip="80°C보다 낮은 물에 우리면 쓴맛이 덜해요. 어린 잎일수록 더 낮게.",
    ),
    "matcha": TeaInfo(
        caffeine="많음",
        components=("카테킨", "테아닌", "카페인"),
        points=(
            "찻잎을 곱게 갈아 물에 풀어 마시므로, 잎의 성분을 통째로 마시게 돼요.",
            "그래서 같은 양의 우린 녹차보다 카페인을 더 많이 마시게 되는 편이에요.",
            *COMMON_TEA_POINTS,
        ),
        brew_tip="뜨겁지 않은 물(70~80°C)에 풀어 거품기로 저어요.",
    ),
    "black": TeaInfo(
        caffeine="많음",
        components=("테아닌", "카페인", "폴리페놀"),
        points=(
            "찻잎을 완전히 산화시킨 차예요. 붉은 찻물과 진한 향이 특징이에요.",
            "테아닌이 녹차·우롱차보다 많은 편이라고 알려져 있어요.",
            "카페인이 강한 잎을 모은 브렉퍼스트 티는 아침 잠을 깨우는 용도로 마셔요.",
            *COMMON_TEA_POINTS,
        ),
        brew_tip="충분히 끓인 물로, 티팟을 따뜻하게 유지하며 우려요.",
    ),
    "oolong": TeaInfo(
        caffeine="중간",
        components=("테아닌", "카테킨", "카페인"),
        points=(
            "반쯤 산화시킨 차로, 녹차와 홍차 사이의 맛과 향을 가져요.",
            "테아닌 함량도 녹차와 홍차의 중간쯤으로 알려져 있어요.",
            *COMMON_TEA_POINTS,
        ),
        brew_tip="산화가 덜 된 우롱(철관음 등)은 90°C, 많이 된 것(대홍포 등)은 95°C 정도.",
    ),
    "white": TeaInfo(
        caffeine="적은 편",
        components=("폴리페놀", "카페인"),
        points=(
            "낮은 온도에서 천천히 시들려 말린, 산화가 적은 차예요(약 15%).",
            "복잡한 향과 달고 담백한 맛이 있고, 여러 번 우려도 맛이 오래가요.",
            *COMMON_TEA_POINTS,
        ),
        brew_tip="여러 번 우려 마시기 좋고, 여름에는 찬물에 오래 우리는 냉침도 좋아요.",
    ),
    "puer": TeaInfo(
        caffeine="중간",
        components=("폴리페놀", "카페인"),
        points=(
            "찻잎을 숙성·발효시킨 흑차로, 떡처럼 뭉친 병차 형태가 많아요.",
            "묵은 듯한 깊은 향과 부드러운 맛이 특징이에요.",
            *COMMON_TEA_POINTS,
        ),
        brew_tip="숙차는 끓는 물로 우려요.",
    ),
    "herbal": TeaInfo(
        caffeine="없음(대부분)",
        components=("꽃·잎·뿌리마다 다름",),
        points=(
            "차나무 잎이 아닌 꽃·잎·뿌리를 우린 대용차예요. 캐모마일, 민트, 루이보스 등.",
            "대부분 카페인이 없어 저녁에 마시기 좋아요 (마테처럼 카페인이 있는 것도 있어요).",
        ),
        brew_tip="끓는 물에 5분 안팎으로 충분히 우려요.",
    ),
    "grain": TeaInfo(
        caffeine="없음(대부분)",
        components=("곡물마다 다름",),
        points=(
            "보리·옥수수·현미 같은 곡물을 볶아 우린 대용차로, 구수한 맛이 나요.",
            "카페인이 없어 물 대신 하루 종일 마시기 좋아요.",
        ),
        brew_tip="끓는 물에 넣고 한소끔 끓이거나 오래 우려요.",
    ),
    "other": TeaInfo(
        caffeine="종류마다 다름",
        components=("재료마다 다름",),
        points=(
            "유자차·대추차·생강차처럼 과일·열매·뿌리로 만든 대용차가 여기에 들어가요.",
            "예를 들어 대추차에는 비타민 C와 식이섬유, 항산화 성분이 들어 있다고 알려져 있어요.",
        ),
        brew_tip="재료에 따라 다르니 포장의 안내를 따라 주세요.",
    ),
}


def tea_info(tea_type: str | None) -> TeaInfo | None:
    return TEA_INFO.get(tea_type or "")


def caffeine_tag(tea_type: str | None) -> str | None:
    info = tea_info(tea_type)
    return f"카페인 {info.caffeine}" if info else None
