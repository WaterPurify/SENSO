"""W7: 취향 유형 테스트, Taste DNA, 결과 카드."""

import io
from datetime import datetime, timedelta
from itertools import product

import pytest
from PIL import Image

from senso.db.database import open_database
from senso.db.quiz_repo import QuizRepository
from senso.domain.bean import BeanKind
from senso.domain.brew import BeanSnapshot, Brew, Recipe, Tasting
from senso.taste.card import HEIGHT, WIDTH, render_card
from senso.taste.dna import MIN_BREWS, NotEnough, TasteDNA, compute
from senso.taste.quiz import FLAVORS, QUESTIONS, TYPES, score

NOW = datetime(2026, 11, 14, 10)

# ---- 테스트 문항 ------------------------------------------------------------------


def test_twelve_questions_four_choices():
    assert len(QUESTIONS) == 12
    assert all(len(q.choices) == 4 for q in QUESTIONS)
    assert len(TYPES) == 8


def test_every_type_is_reachable():
    """8가지 유형 모두 나올 수 있어야 한다 (문항 설계 점검)."""
    reached = set()
    for flavor, side in product(FLAVORS, ("sen", "so")):
        answers = []
        for q in QUESTIONS:

            def rank(c, flavor=flavor, side=side):
                return (c.flavor == flavor) * 2 + (c.side == side)

            answers.append(max(range(4), key=lambda i, q=q: rank(q.choices[i])))
        reached.add(score(answers).type.code)
    assert reached == set(TYPES)


def test_two_axes_are_balanced():
    """마시는 쪽 문항은 Sen 2·So 2, 맛 문항은 네 성향이 하나씩."""
    side_qs = [q for q in QUESTIONS if any(c.side for c in q.choices)]
    flavor_qs = [q for q in QUESTIONS if any(c.flavor for c in q.choices)]
    assert len(side_qs) == 4 and len(flavor_qs) == 8
    for q in side_qs:
        assert sorted(c.side for c in q.choices) == ["sen", "sen", "so", "so"]
        assert all(c.flavor is None for c in q.choices)
    for q in flavor_qs:
        assert sorted(c.flavor for c in q.choices) == sorted(FLAVORS)
        assert all(c.side is None for c in q.choices)


def test_score_counts_and_tie_rules():
    r = score([0] * 12)
    assert sum(r.flavor_scores.values()) == 8
    assert r.sen + r.so == 4
    # 첫 번째 선택지만 고르면 마시는 쪽은 Sen 4, 맛은 모두 고소한
    assert r.type.code == "sen_nutty"
    # 마시는 쪽 2:2 동점이면 Sen, 맛 성향 동점이면 고소한→산뜻한→진한→은은한 순서
    # 마시는 쪽 문항(1·4·8·11번): Sen·So·Sen·So / 맛: 산뜻 5, 고소 3
    tie = [0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0]
    tie_sides = score(tie)
    assert (tie_sides.sen, tie_sides.so) == (2, 2)
    assert tie_sides.type.side == "sen"
    flavor_tie = [0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0]  # 고소 4 · 산뜻 4
    assert score(flavor_tie).type.flavor == "nutty"


@pytest.mark.parametrize("answers", [[0] * 11, [0] * 13, [0] * 11 + [4], [-1] + [0] * 11])
def test_bad_answers(answers):
    with pytest.raises(ValueError):
        score(answers)


def test_quiz_saved_and_latest(tmp_path):
    conn = open_database(tmp_path / "t.db")
    repo = QuizRepository(conn)
    assert repo.latest() is None
    repo.save([0] * 12, "sen_nutty", NOW)
    repo.save([1] * 12, "sen_bright", NOW + timedelta(minutes=5))
    latest = repo.latest()
    assert latest.type_code == "sen_bright"
    assert latest.answers == tuple([1] * 12)
    conn.close()


# ---- 결과 카드 --------------------------------------------------------------------


@pytest.mark.parametrize("code", ["sen_nutty", "so_gentle"])
def test_card_is_story_sized_png(code):
    side, flavor = code.split("_")
    answers = []
    for q in QUESTIONS:
        best = max(
            range(4),
            key=lambda i, q=q: (q.choices[i].flavor == flavor) * 2 + (q.choices[i].side == side),
        )
        answers.append(best)
    result = score(answers)
    assert result.type.code == code
    png = render_card(result)
    with Image.open(io.BytesIO(png)) as img:
        assert img.format == "PNG"
        assert img.size == (WIDTH, HEIGHT) == (1080, 1920)


# ---- Taste DNA -------------------------------------------------------------------

COFFEE = BeanSnapshot("예가체프", BeanKind.COFFEE)
TEA = BeanSnapshot("세작", BeanKind.TEA)


def brew(
    i, sat, acid=None, bitter=None, sweet=None, body=None, *, tea=False, sample=False, flavors=()
):
    return Brew(
        id=i,
        bean_id=1,
        bean=TEA if tea else COFFEE,
        recipe=Recipe(15, 250),
        desired_flavors=tuple(flavors),
        tasting=Tasting(
            acidity=acid, bitterness=bitter, sweetness=sweet, body=body, satisfaction=sat
        ),
        brewed_at=NOW - timedelta(days=i),
        is_sample=sample,
    )


def test_not_enough_records():
    result = compute([brew(i, 4) for i in range(MIN_BREWS - 1)])
    assert isinstance(result, NotEnough)
    assert result.rated == MIN_BREWS - 1


def test_samples_and_unrated_are_ignored():
    brews = [brew(i, 4, sample=True) for i in range(10)] + [brew(20, None)]
    assert compute(brews) == NotEnough(rated=0)


def test_preferences_follow_satisfaction():
    brews = [
        # 좋았던 기록: 산미 낮고 단맛 높음
        brew(1, 5, acid=2, sweet=5, bitter=3, body=3, flavors=["초콜릿", "견과류"]),
        brew(2, 4, acid=2, sweet=4, bitter=3, body=3, flavors=["초콜릿"]),
        brew(3, 5, acid=1, sweet=4, bitter=3, body=3, tea=True, flavors=["구수함"]),
        # 덜 좋았던 기록: 산미 높고 단맛 낮음
        brew(4, 2, acid=5, sweet=2, bitter=3, body=3),
        brew(5, 2, acid=4, sweet=1, bitter=3, body=3),
    ]
    dna = compute(brews)
    assert isinstance(dna, TasteDNA)
    traits = {t.key: t for t in dna.traits}
    assert traits["acidity"].direction == "low"
    assert traits["sweetness"].direction == "high"
    assert traits["bitterness"].direction == "neutral"
    assert traits["acidity"].sentence == "산미가 약함 쪽일 때 더 만족했어요"
    assert traits["sweetness"].sentence == "단맛이 강함 쪽일 때 더 만족했어요"
    assert traits["bitterness"].sentence == "쓴맛은 만족도와 큰 관계가 없었어요"
    assert dna.top_flavors[0] == "초콜릿"
    assert dna.coffee_share == pytest.approx(0.8)
    assert [b.id for b in dna.evidence][:2] == [1, 3]  # 만족도 5점, 최신순
    assert dna.liked == 3


def test_missing_scores_are_unknown():
    dna = compute([brew(i, 4 + i % 2) for i in range(6)])
    assert all(t.direction == "unknown" for t in dna.traits)


def test_no_liked_records_uses_best_ones():
    brews = [
        brew(1, 3, acid=2),
        brew(2, 3, acid=2),
        brew(3, 2, acid=5),
        brew(4, 1, acid=5),
        brew(5, 1, acid=4),
    ]
    dna = compute(brews)
    assert dna.liked == 2
    assert {t.key: t for t in dna.traits}["acidity"].direction == "low"
