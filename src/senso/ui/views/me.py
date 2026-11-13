"""나: 취향 유형과 Taste DNA."""

from collections.abc import Callable

import flet as ft

from senso import __version__
from senso.characters.lines import Line, Who
from senso.db.quiz_repo import SavedQuiz
from senso.domain.brew import Brew
from senso.taste.dna import MIN_BREWS, NotEnough, TasteDNA
from senso.taste.quiz import TYPES
from senso.ui import theme
from senso.ui.components.brew_card import format_when, tag
from senso.ui.components.character import speech_bubble
from senso.ui.components.header import header
from senso.ui.components.inputs import section

DIRECTION_TEXT = {
    "high": "높을수록 좋아요",
    "low": "낮을수록 좋아요",
    "neutral": "상관없음",
    "unknown": "기록 부족",
}


def _quiz_section(quiz: SavedQuiz | None, on_quiz: Callable[[], None]) -> ft.Control:
    if quiz is None or quiz.type_code not in TYPES:
        return section(
            "취향 유형 테스트",
            "12문항, 1분이면 끝나요",
            [
                ft.Text("나는 고소한 Sen형일까, 산뜻한 So형일까?", color=theme.BROWN),
                ft.FilledButton(
                    "테스트 하기",
                    icon=ft.Icons.QUIZ_OUTLINED,
                    height=48,
                    on_click=lambda _: on_quiz(),
                ),
            ],
        )
    t = TYPES[quiz.type_code]
    return section(
        "나의 취향 유형",
        f"{format_when(quiz.taken_at)}에 테스트했어요",
        [
            ft.Text(t.name, size=theme.TITLE_SIZE, weight=ft.FontWeight.BOLD, color=theme.BROWN),
            ft.Text(t.summary, color=theme.BROWN),
            ft.Row(wrap=True, spacing=6, controls=[tag(p) for p in t.picks]),
            ft.OutlinedButton("다시 테스트", icon=ft.Icons.REPLAY, on_click=lambda _: on_quiz()),
        ],
    )


def _bar(value: float | None) -> ft.Control:
    """1~5 평균을 막대로."""
    width = 140
    filled = 0 if value is None else width * (value - 1) / 4
    return ft.Stack(
        width=width,
        height=10,
        controls=[
            ft.Container(width=width, height=10, border_radius=5, bgcolor="#E9DFD1"),
            ft.Container(width=max(filled, 0), height=10, border_radius=5, bgcolor=theme.BROWN),
        ],
    )


def _dna_section(dna: TasteDNA | NotEnough, on_open: Callable[[Brew], None]) -> list[ft.Control]:
    if isinstance(dna, NotEnough):
        left = dna.needed - dna.rated
        return [
            speech_bubble(
                Line(Who.SO, f"만족도를 매긴 기록이 {left}개 더 있으면 Taste DNA를 알려 드릴게요.")
            ),
            section(
                "Taste DNA",
                f"만족도를 매긴 기록 {dna.rated} / {MIN_BREWS}개 (예시 기록 제외)",
                [
                    ft.ProgressBar(
                        value=dna.rated / dna.needed, color=theme.TEA_GREEN, bgcolor=theme.CREAM
                    )
                ],
            ),
        ]

    trait_rows = [
        ft.Row(
            controls=[
                ft.Text(t.label, width=48, weight=ft.FontWeight.BOLD, color=theme.BROWN),
                _bar(t.liked_avg),
                ft.Text(DIRECTION_TEXT[t.direction], size=13, color=theme.TEXT_MUTED),
            ]
        )
        for t in dna.traits
    ]
    sentences = [
        ft.Text(f"· {t.sentence}", color=theme.BROWN)
        for t in dna.traits
        if t.direction != "unknown"
    ]
    coffee_pct = round(dna.coffee_share * 100)
    highlight = next((t for t in dna.traits if t.direction in ("high", "low")), None)
    so_says = (
        f"기록 {dna.rated}개를 보니, {highlight.sentence.replace('했어요', '하셨어요')}."
        if highlight
        else "아직은 뚜렷한 경향이 없어요. 다양하게 마셔 보며 기록을 더 남겨 주세요."
    )

    evidence = [
        ft.TextButton(
            f"{format_when(b.brewed_at)} · {b.bean.name} · 만족도 {b.tasting.satisfaction}점",
            on_click=lambda _, b=b: on_open(b),
        )
        for b in dna.evidence
    ]
    return [
        speech_bubble(Line(Who.SO, so_says)),
        section(
            "Taste DNA",
            f"만족도를 매긴 기록 {dna.rated}개 중 좋았던(4~5점) 기록 {dna.liked}개 기준",
            [
                *trait_rows,
                ft.Text("막대는 좋았던 기록의 평균 점수예요", size=12, color=theme.TEXT_MUTED),
                *sentences,
                ft.Row(
                    wrap=True,
                    spacing=6,
                    controls=[
                        tag(f"커피 {coffee_pct}% · 차 {100 - coffee_pct}%"),
                        *[
                            tag(f, bgcolor="#E8F0E0", color=theme.TEA_GREEN)
                            for f in dna.top_flavors
                        ],
                    ],
                ),
            ],
        ),
        section("근거가 된 기록", "만족도가 높았던 기록", evidence),
    ]


def me_view(
    schema_version: int,
    quiz: SavedQuiz | None,
    dna: TasteDNA | NotEnough,
    on_quiz: Callable[[], None],
    on_open: Callable[[Brew], None],
) -> ft.Control:
    return ft.Column(
        spacing=theme.SPACING,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            header("나의 취향", "취향 유형과 Taste DNA"),
            _quiz_section(quiz, on_quiz),
            *_dna_section(dna, on_open),
            ft.Text(
                f"버전 {__version__} · 데이터 스키마 v{schema_version}",
                size=theme.CAPTION_SIZE,
                color=theme.TEXT_MUTED,
            ),
        ],
    )
