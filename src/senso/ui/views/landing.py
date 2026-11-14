"""로그인 전 소개. 공개된 예시만 표시하며 개인 저장소는 열지 않는다."""

from collections.abc import Callable

import flet as ft

from senso.ui import theme

DESKTOP_WIDTH = 1160


def eyebrow(text: str) -> ft.Text:
    return ft.Text(text, size=11, color=theme.TEXT_MUTED)


def example_recipe() -> ft.Control:
    values = ft.ResponsiveRow(
        columns=4,
        spacing=8,
        controls=[
            ft.Column(
                col=1,
                spacing=3,
                controls=[
                    ft.Text(label, size=12, color=theme.TEXT_MUTED),
                    ft.Text(value, size=20, color=theme.BROWN),
                ],
            )
            for label, value in [
                ("원두", "15g"),
                ("물", "250g"),
                ("온도", "92°C"),
                ("시간", "2:30"),
            ]
        ],
    )
    return ft.Container(
        bgcolor="#FFFDFA",
        border_radius=16,
        padding=24,
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Row(
                    wrap=True,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("COFFEE · 핸드드립 · 예시", size=12, color=theme.TEA_GREEN),
                        ft.Text("★ 4.0", size=14, color=theme.BROWN),
                    ],
                ),
                ft.Text("에티오피아 예가체프", size=23, weight=ft.FontWeight.BOLD),
                ft.Text("꽃향, 산뜻한 산미, 깔끔한 여운.", size=14, color=theme.TEXT_MUTED),
                values,
                ft.Divider(color="#E6DFD3"),
                ft.Text("Sen의 다음 한 잔", size=13, color=theme.TEA_GREEN),
                ft.Text("산미가 강했다면, 다음에는 조금 더 곱게 내려 볼까요?", size=14),
            ],
        ),
    )


def landing_view(on_signup: Callable[[], None], on_example: Callable[[], None]) -> ft.Control:
    copy = ft.Column(
        col={"xs": 12, "md": 6},
        spacing=22,
        controls=[
            eyebrow("A LITTLE RITUAL, EVERY DAY"),
            ft.Text(
                "오늘의 한 잔이,\n내일의 취향이 되도록.",
                size=36,
                weight=ft.FontWeight.BOLD,
                color=theme.BROWN,
            ),
            ft.Text(
                "원두부터 마지막 한 모금까지.\n커피와 차를 기록하고, 나에게 맞는 레시피를 찾아요.",
                size=16,
                color=theme.TEXT_MUTED,
            ),
            ft.Row(
                wrap=True,
                spacing=12,
                run_spacing=8,
                controls=[
                    ft.FilledButton(
                        "무료로 시작하기",
                        icon=ft.Icons.ARROW_FORWARD,
                        height=48,
                        on_click=lambda _: on_signup(),
                    ),
                    ft.TextButton("예시 기록 둘러보기", on_click=lambda _: on_example()),
                ],
            ),
            ft.Row(
                wrap=True,
                spacing=10,
                controls=[
                    ft.CircleAvatar(content=ft.Text("Sen"), bgcolor=theme.CREAM, color=theme.BROWN),
                    ft.CircleAvatar(
                        content=ft.Text("So"), bgcolor="#E0E7D8", color=theme.TEA_GREEN
                    ),
                    ft.Text(
                        "커피를 좋아하는 Sen,\n차를 좋아하는 So와 함께해요.",
                        size=13,
                        color=theme.TEXT_MUTED,
                    ),
                ],
            ),
        ],
    )
    stage = ft.Container(
        col={"xs": 12, "md": 6},
        bgcolor="#EDE4D5",
        border_radius=28,
        padding=24,
        content=ft.Column(
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                eyebrow("YOUR NEXT FAVORITE CUP · 예시 기록"),
                ft.Icon(ft.Icons.COFFEE_ROUNDED, size=80, color=theme.BROWN_LIGHT),
                ft.Text("a moment for yourself.", italic=True, size=15, color=theme.TEXT_MUTED),
                example_recipe(),
            ],
        ),
    )
    steps = ft.ResponsiveRow(
        spacing=24,
        run_spacing=24,
        controls=[
            ft.Column(
                col={"xs": 12, "sm": 4},
                spacing=7,
                controls=[
                    eyebrow(number),
                    ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(description, size=14, color=theme.TEXT_MUTED),
                ],
            )
            for number, title, description in [
                ("01 — RECORD", "한 잔을 남기고", "원두와 추출 조건을 간단히 기록해요."),
                ("02 — TASTE", "나의 맛을 찾고", "좋았던 맛과 아쉬웠던 점을 남겨요."),
                (
                    "03 — BREW AGAIN",
                    "다음 한 잔을 더 맛있게",
                    "지난 레시피에서 한 가지씩 바꿔봐요.",
                ),
            ]
        ],
    )
    return ft.Column(
        spacing=32,
        controls=[
            ft.ResponsiveRow(
                spacing=32,
                run_spacing=28,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[copy, stage],
            ),
            ft.Divider(color="#E6DFD3"),
            steps,
            ft.Divider(color="#E6DFD3"),
            ft.Text("senso — 한 잔에서 시작하는 나의 취향", size=12, color=theme.TEXT_MUTED),
        ],
    )
