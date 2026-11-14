"""취향 유형 테스트: 한 문항씩 보여 주고, 끝나면 결과 카드."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import flet as ft

from senso.characters.lines import Line, Who
from senso.taste.card import render_card
from senso.taste.quiz import QUESTIONS, QuizResult, score
from senso.ui import theme
from senso.ui.components.character import speech_bubble


@dataclass
class QuizDeps:
    on_done: Callable[[list[int], QuizResult], None]  # 결과 저장
    on_close: Callable[[], None]
    save_png: Callable[[bytes, str], Awaitable[None]]


def quiz_view(deps: QuizDeps) -> ft.Control:
    answers: list[int] = []
    root = ft.Column(spacing=theme.SPACING, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def header(title: str, on_back) -> ft.Control:
        return ft.Row(
            controls=[
                ft.IconButton(ft.Icons.ARROW_BACK, tooltip="뒤로", on_click=lambda _: on_back()),
                ft.Text(
                    title, size=theme.HEADING_SIZE, weight=ft.FontWeight.BOLD, color=theme.BROWN
                ),
            ]
        )

    def back() -> None:
        if answers:
            answers.pop()
            render_question()
        else:
            deps.on_close()

    def choose(i: int) -> None:
        answers.append(i)
        if len(answers) == len(QUESTIONS):
            result = score(answers)
            deps.on_done(list(answers), result)
            render_result(result)
        else:
            render_question()

    def render_question(first: bool = False) -> None:
        n = len(answers)
        q = QUESTIONS[n]
        root.controls = [
            header("취향 유형 테스트", back),
            ft.ProgressBar(value=n / len(QUESTIONS), color=theme.BROWN, bgcolor=theme.CREAM),
            ft.Text(f"{n + 1} / {len(QUESTIONS)}", size=theme.CAPTION_SIZE, color=theme.TEXT_MUTED),
            ft.Text(
                q.text, size=theme.HEADING_SIZE + 2, weight=ft.FontWeight.BOLD, color=theme.BROWN
            ),
            *[
                ft.OutlinedButton(
                    c.text,
                    height=56,
                    style=ft.ButtonStyle(
                        bgcolor="#FFFFFF",
                        shape=ft.RoundedRectangleBorder(radius=14),
                        text_style=ft.TextStyle(
                            size=theme.BODY_SIZE, font_family=theme.FONT_FAMILY
                        ),
                    ),
                    on_click=lambda _, i=i: choose(i),
                )
                for i, c in enumerate(q.choices)
            ],
        ]
        if not first:  # 처음에는 아직 화면에 붙기 전이라 update()를 부르면 안 된다
            root.update()

    def render_result(result: QuizResult) -> None:
        png = render_card(result)
        t = result.type
        who = Who.SEN if t.side == "sen" else Who.SO
        hello = (
            f"너는 {t.name}이구나! 기록을 쌓으면 진짜 취향이 더 또렷해질 거야."
            if who is Who.SEN
            else f"{t.name}이시군요. 기록이 쌓이면 Taste DNA로 더 자세히 알려 드릴게요."
        )

        async def on_save(_: ft.Event) -> None:
            await deps.save_png(png, f"SENSO_{t.code}.png")

        root.controls = [
            header("테스트 결과", deps.on_close),
            speech_bubble(Line(who, hello)),
            ft.Container(
                alignment=ft.Alignment.CENTER,
                content=ft.Image(
                    src=png,
                    width=300,
                    height=533,
                    fit=ft.BoxFit.CONTAIN,
                    border_radius=16,
                ),
            ),
            ft.FilledButton(
                "카드 이미지 저장", icon=ft.Icons.DOWNLOAD, height=48, on_click=on_save
            ),
            ft.Row(
                spacing=12,
                controls=[
                    ft.OutlinedButton(
                        "다시 하기",
                        icon=ft.Icons.REPLAY,
                        expand=True,
                        height=44,
                        on_click=lambda _: restart(),
                    ),
                    ft.OutlinedButton(
                        "닫기",
                        icon=ft.Icons.CHECK,
                        expand=True,
                        height=44,
                        on_click=lambda _: deps.on_close(),
                    ),
                ],
            ),
        ]
        root.update()

    def restart() -> None:
        answers.clear()
        render_question()

    render_question(first=True)
    return root
