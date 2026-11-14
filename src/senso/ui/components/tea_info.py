"""차 종류별 알려진 특징 카드."""

import flet as ft

from senso.domain.bean import TEA_TYPES
from senso.domain.tea import DISCLAIMER, SOURCE, tea_info
from senso.ui import theme
from senso.ui.components.brew_card import tag


def tea_info_card(tea_type: str | None, compact: bool = False) -> ft.Control | None:
    info = tea_info(tea_type)
    if info is None:
        return None
    name = TEA_TYPES.get(tea_type or "", "차")
    tags = [
        tag(f"카페인 {info.caffeine}", bgcolor="#FFF1D6", color="#8A5A00"),
        *[tag(c, bgcolor="#E8F0E0", color=theme.TEA_GREEN) for c in info.components],
    ]
    points = info.points[:2] if compact else info.points
    return ft.Container(
        bgcolor="#F6F9F2",
        border=ft.Border.all(1, "#DCE6D2"),
        border_radius=14,
        padding=14,
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Text(
                    f"{name}의 알려진 특징",
                    weight=ft.FontWeight.BOLD,
                    color=theme.TEA_GREEN,
                ),
                ft.Row(wrap=True, spacing=6, run_spacing=6, controls=tags),
                *[ft.Text(f"· {p}", size=13, color=theme.BROWN) for p in points],
                ft.Text(f"우리는 법: {info.brew_tip}", size=13, color=theme.BROWN),
                ft.Text(f"{DISCLAIMER} 출처: {SOURCE}", size=11, color=theme.TEXT_MUTED),
            ],
        ),
    )
