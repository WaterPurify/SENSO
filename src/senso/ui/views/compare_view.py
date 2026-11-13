"""이전 기록과 제안을 적용한 기록을 나란히 비교."""

from collections.abc import Callable

import flet as ft

from senso.characters.lines import compare_line
from senso.domain.brew import Brew
from senso.ui import theme
from senso.ui.components.brew_card import format_when
from senso.ui.components.character import speech_bubble
from senso.ui.components.compare import compare_table, recipe_values, tasting_values
from senso.ui.components.inputs import section


def _short(brew: Brew) -> str:
    return f"{brew.brewed_at.month}/{brew.brewed_at.day} {brew.brewed_at:%H:%M}"


def compare_view(before: Brew, after: Brew, on_back: Callable[[], None]) -> ft.Control:
    iced = before.iced or after.iced
    return ft.Column(
        spacing=theme.SPACING,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            ft.Row(
                controls=[
                    ft.IconButton(
                        ft.Icons.ARROW_BACK, tooltip="뒤로", on_click=lambda _: on_back()
                    ),
                    ft.Column(
                        spacing=0,
                        expand=True,
                        controls=[
                            ft.Text(
                                "기록 비교",
                                size=theme.HEADING_SIZE,
                                weight=ft.FontWeight.BOLD,
                                color=theme.BROWN,
                            ),
                            ft.Text(
                                f"{format_when(before.brewed_at)} → {format_when(after.brewed_at)}",
                                size=theme.CAPTION_SIZE,
                                color=theme.TEXT_MUTED,
                            ),
                        ],
                    ),
                ]
            ),
            speech_bubble(
                compare_line(after.kind, before.tasting.satisfaction, after.tasting.satisfaction)
            ),
            section(
                "레시피",
                "노란 칸이 달라진 조건이에요",
                [
                    compare_table(
                        f"이전 ({_short(before)})",
                        f"이번 ({_short(after)})",
                        recipe_values(before.recipe, before.kind, iced),
                        recipe_values(after.recipe, after.kind, iced),
                    )
                ],
            ),
            section(
                "실제로 느낀 맛",
                None,
                [
                    compare_table(
                        "이전",
                        "이번",
                        tasting_values(before.tasting),
                        tasting_values(after.tasting),
                    )
                ],
            ),
        ],
    )
