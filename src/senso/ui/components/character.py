"""Sen & So 캐릭터 말풍선."""

import flet as ft

from senso.characters.lines import NAMES, Line, Who
from senso.ui import theme

IMAGES = {
    Who.SEN: "characters/sen.png",
    Who.SO: "characters/so.png",
    Who.DUO: "characters/duo.png",
}
ACCENT = {Who.SEN: theme.BROWN_LIGHT, Who.SO: theme.TEA_GREEN, Who.DUO: theme.BROWN}


def speech_bubble(line: Line, size: int = 72) -> ft.Control:
    """왼쪽에 캐릭터, 오른쪽에 말풍선."""
    width = size * (1.25 if line.who is Who.DUO else 0.7)
    return ft.Row(
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.END,
        controls=[
            ft.Image(
                src=IMAGES[line.who],
                height=size,
                width=width,
                fit=ft.BoxFit.CONTAIN,
                error_content=ft.Icon(ft.Icons.FACE, color=ACCENT[line.who]),
            ),
            ft.Container(
                expand=True,
                bgcolor="#FFFFFF",
                border=ft.Border.all(1, "#E9DFD1"),
                border_radius=ft.BorderRadius.only(
                    top_left=16, top_right=16, bottom_right=16, bottom_left=4
                ),
                padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                content=ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(
                            NAMES[line.who],
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=ACCENT[line.who],
                        ),
                        ft.Text(line.text, size=theme.BODY_SIZE - 1, color=theme.BROWN),
                    ],
                ),
            ),
        ],
    )
