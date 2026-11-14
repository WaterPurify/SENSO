"""쇼핑: 출시 예정 상품 (사업계획서 v2.5 '3-5. 멤버십 혜택', 수익 구조).

아직 결제는 없다. 상품을 보여 주고 '출시 알림 받기'만 기기 안에 기록한다
(실제로 알림을 보내지는 않는다. 서버·푸시가 생기면 이 기록을 쓴다).
"""

from dataclasses import dataclass

NOTIFY_PREFIX = "shop_notify:"  # app_settings 키: shop_notify:<상품 키> = '1'


@dataclass(frozen=True)
class Product:
    key: str
    name: str
    price: str
    summary: str
    points: tuple[str, ...]
    tag: str  # '정기 결제' | '단품' | '시즌 한정' 등


PRODUCTS: tuple[Product, ...] = (
    Product(
        "tasting_box",
        "테이스팅 박스",
        "12,900원",
        "취향 기록에 맞춰 고른 원두·찻잎 샘플을 담은 상자",
        (
            "2종 × 25g 샘플과 산지 이야기 카드",
            "마셔 본 뒤 앱에 기록하면 다음 박스 추천이 더 정확해져요",
            "판매액의 1%를 커피·차 생산 농가 지원에 쓰는 것이 목표예요",
        ),
        "단품",
    ),
    Product(
        "plus",
        "Plus 멤버십",
        "월 7,900원",
        "기록과 분석을 마음껏 쓰는 디지털 멤버십",
        (
            "취향 유형 테스트·기록 무제한, 비교 분석",
            "AI 취향 일치도와 추천 이유 설명, AI Brew Coach",
            "무드 플레이리스트, 계절 의상 해금, 테이스팅 박스 회원가 구매",
        ),
        "정기 결제",
    ),
    Product(
        "premium",
        "Premium 멤버십",
        "월 29,000원",
        "격주로 집에 오는 테이스팅 박스와 전문가 코칭",
        (
            "테이스팅 박스 격주 배송 포함 (2종 × 25g)",
            "취향 변화 분석, 고급 코칭, 월 1회 1:1 전문가 코칭",
            "연간 회원 한정 굿즈",
        ),
        "정기 결제",
    ),
    Product(
        "gift_set",
        "명절 선물세트",
        "가격 미정",
        "Sen & So가 고른 커피·차를 담은 선물 상자",
        ("설·추석 시즌 한정", "받는 분의 취향 유형에 맞춰 고를 수 있게 준비 중이에요"),
        "시즌 한정",
    ),
    Product(
        "goods",
        "Sen & So 굿즈",
        "가격 미정",
        "머그컵·스티커 같은 캐릭터 굿즈",
        ("Sen & So 일러스트 머그컵, 스티커, 티 코스터", "멤버십 회원에게 먼저 소개할 예정이에요"),
        "준비 중",
    ),
)

PRODUCTS_BY_KEY: dict[str, Product] = {p.key: p for p in PRODUCTS}
