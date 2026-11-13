"""취향 유형 테스트: 12문항 → 8가지 유형.

유형 = 마시는 쪽(Sen: 커피 / So: 차) × 맛 성향 4가지
  - nutty   고소한  (견과·초콜릿·곡물)
  - bright  산뜻한  (과일·산미·상큼함)
  - bold    진한    (묵직함·쌉쌀함·바디)
  - gentle  은은한  (꽃향·부드러움·여운)

마시는 쪽 문항 4개와 맛 성향 문항 8개로 나눠 두 축을 따로 센다.
동점이면 맛 성향은 FLAVORS 순서, 마시는 쪽은 Sen을 고른다.
"""

from collections import Counter
from dataclasses import dataclass

FLAVORS = ("nutty", "bright", "bold", "gentle")  # 동점일 때 이 순서
FLAVOR_NAMES = {"nutty": "고소한", "bright": "산뜻한", "bold": "진한", "gentle": "은은한"}


@dataclass(frozen=True)
class Choice:
    text: str
    flavor: str | None = None  # 맛 성향 +1
    side: str | None = None  # "sen" | "so" +1


@dataclass(frozen=True)
class Question:
    text: str
    choices: tuple[Choice, ...]


# 문항 설계 (모든 유형이 나올 수 있도록 두 축을 나눈다)
# - 마시는 쪽 문항 4개(1·4·8·11번): 선택지마다 Sen 2개, So 2개. 맛 점수 없음
# - 맛 성향 문항 8개: 선택지마다 고소한·산뜻한·진한·은은한이 하나씩. 마시는 쪽 점수 없음
QUESTIONS: tuple[Question, ...] = (
    Question(
        "아침에 눈뜨자마자 떠오르는 한 잔은?",
        (
            Choice("진하게 내린 커피", side="sen"),
            Choice("따뜻한 녹차 한 잔", side="so"),
            Choice("고소한 라떼", side="sen"),
            Choice("상큼한 과일차", side="so"),
        ),
    ),
    Question(
        "디저트를 하나 고른다면?",
        (
            Choice("견과류 듬뿍 브라우니", "nutty"),
            Choice("레몬 타르트", "bright"),
            Choice("다크 초콜릿", "bold"),
            Choice("벚꽃 양갱", "gentle"),
        ),
    ),
    Question(
        "메뉴판에서 먼저 눈이 가는 말은?",
        (
            Choice("'고소한', '구운'", "nutty"),
            Choice("'산뜻한', '베리'", "bright"),
            Choice("'스모키', '깊은'", "bold"),
            Choice("'꽃향', '은은한'", "gentle"),
        ),
    ),
    Question(
        "오후 3시, 졸음이 올 때 나는?",
        (
            Choice("커피 한 잔 더!", side="sen"),
            Choice("카페인 적은 차로 쉬어 가기", side="so"),
            Choice("에스프레소 샷 추가", side="sen"),
            Choice("향 좋은 허브티", side="so"),
        ),
    ),
    Question(
        "좋아하는 과일은?",
        (
            Choice("바나나", "nutty"),
            Choice("자몽·오렌지", "bright"),
            Choice("잘 익은 체리", "bold"),
            Choice("복숭아", "gentle"),
        ),
    ),
    Question(
        "쓴맛은 어느 정도가 좋아요?",
        (
            Choice("살짝만 있으면 좋아요", "nutty"),
            Choice("쓴맛보다 신맛이 좋아요", "bright"),
            Choice("쌉쌀해야 제맛", "bold"),
            Choice("거의 없었으면", "gentle"),
        ),
    ),
    Question(
        "가장 끌리는 향은?",
        (
            Choice("갓 볶은 곡물", "nutty"),
            Choice("상큼한 시트러스", "bright"),
            Choice("나무와 스모키", "bold"),
            Choice("재스민·장미", "gentle"),
        ),
    ),
    Question(
        "주말 오후에 하고 싶은 건?",
        (
            Choice("새로 생긴 로스터리 탐방", side="sen"),
            Choice("조용한 찻집에서 책 읽기", side="so"),
            Choice("집에서 핸드드립 실험", side="sen"),
            Choice("다도 체험", side="so"),
        ),
    ),
    Question(
        "입 안에 남는 느낌은 어떤 게 좋아요?",
        (
            Choice("부드럽고 둥근 느낌", "nutty"),
            Choice("가볍고 깔끔한 느낌", "bright"),
            Choice("묵직하고 꽉 찬 느낌", "bold"),
            Choice("향이 오래 남는 느낌", "gentle"),
        ),
    ),
    Question(
        "빵집에서 고른다면?",
        (
            Choice("호두 깜빠뉴", "nutty"),
            Choice("크랜베리 스콘", "bright"),
            Choice("초코 크루아상", "bold"),
            Choice("녹차 롤케이크", "gentle"),
        ),
    ),
    Question(
        "잠들기 전 마지막 한 잔은?",
        (
            Choice("디카페인 커피", side="sen"),
            Choice("보리차·옥수수차", side="so"),
            Choice("디카페인 라떼", side="sen"),
            Choice("캐모마일", side="so"),
        ),
    ),
    Question(
        "나에게 커피·차는?",
        (
            Choice("익숙하고 편안한 친구", "nutty"),
            Choice("새로운 맛을 찾는 놀이", "bright"),
            Choice("하루를 깨우는 연료", "bold"),
            Choice("마음을 쉬게 하는 시간", "gentle"),
        ),
    ),
)

assert len(QUESTIONS) == 12


@dataclass(frozen=True)
class TasteType:
    code: str  # 예: sen_nutty
    side: str  # sen | so
    flavor: str
    name: str  # 예: 고소한 Sen형
    summary: str
    picks: tuple[str, ...]  # 추천해 볼 만한 원두·차


TYPES: dict[str, TasteType] = {
    t.code: t
    for t in (
        TasteType(
            "sen_nutty",
            "sen",
            "nutty",
            "고소한 Sen형",
            "견과와 초콜릿처럼 편안하고 고소한 커피를 좋아해요. 산미보다 단맛과 둥근 바디가 중요해요.",
            ("브라질 세하도", "콜롬비아 수프리모", "카페라떼"),
        ),
        TasteType(
            "sen_bright",
            "sen",
            "bright",
            "산뜻한 Sen형",
            "과일 향과 밝은 산미를 즐기는 탐험가예요. 새 원두를 내려 보는 걸 좋아해요.",
            ("에티오피아 예가체프", "케냐 AA", "라이트 로스트 핸드드립"),
        ),
        TasteType(
            "sen_bold",
            "sen",
            "bold",
            "진한 Sen형",
            "묵직한 바디와 쌉쌀한 여운이 있어야 커피를 마신 것 같아요.",
            ("인도네시아 만델링", "다크 로스트 블렌드", "에스프레소"),
        ),
        TasteType(
            "sen_gentle",
            "sen",
            "gentle",
            "은은한 Sen형",
            "꽃향과 부드러운 단맛이 오래 남는 섬세한 커피를 좋아해요.",
            ("파나마 게이샤", "르완다 버번", "미디엄 라이트 로스트"),
        ),
        TasteType(
            "so_nutty",
            "so",
            "nutty",
            "고소한 So형",
            "구수하고 편안한 차를 좋아해요. 하루를 차분하게 마무리하는 한 잔이 소중해요.",
            ("현미녹차", "호지차", "보리차"),
        ),
        TasteType(
            "so_bright",
            "so",
            "bright",
            "산뜻한 So형",
            "상큼한 과일 향과 깔끔한 끝맛을 즐겨요. 아이스티도 잘 어울려요.",
            ("유자차", "오미자차", "얼그레이"),
        ),
        TasteType(
            "so_bold",
            "so",
            "bold",
            "진한 So형",
            "진하게 우린 홍차나 숙성된 차의 깊은 맛을 좋아해요.",
            ("아쌈", "보이차", "진하게 우린 말차"),
        ),
        TasteType(
            "so_gentle",
            "so",
            "gentle",
            "은은한 So형",
            "꽃향과 풀향이 은은하게 퍼지는 섬세한 차를 좋아해요.",
            ("제주 세작", "재스민차", "백차"),
        ),
    )
}


@dataclass(frozen=True)
class QuizResult:
    type: TasteType
    flavor_scores: dict[str, int]
    sen: int
    so: int


def score(answers: list[int]) -> QuizResult:
    """answers[i] = i번 문항에서 고른 선택지 번호(0부터)."""
    if len(answers) != len(QUESTIONS):
        raise ValueError(f"{len(QUESTIONS)}문항에 모두 답해야 해요")
    flavors: Counter[str] = Counter({f: 0 for f in FLAVORS})
    sides: Counter[str] = Counter()
    for q, a in zip(QUESTIONS, answers, strict=True):
        if not 0 <= a < len(q.choices):
            raise ValueError(f"선택지 번호가 잘못됐어요: {a}")
        c = q.choices[a]
        if c.flavor:
            flavors[c.flavor] += 1
        if c.side:
            sides[c.side] += 1
    best = max(FLAVORS, key=lambda f: (flavors[f], -FLAVORS.index(f)))
    side = "so" if sides["so"] > sides["sen"] else "sen"  # 동점이면 Sen
    return QuizResult(
        type=TYPES[f"{side}_{best}"],
        flavor_scores=dict(flavors),
        sen=sides["sen"],
        so=sides["so"],
    )
