import flet as ft

from senso.ui import theme


def empty_state(icon: ft.IconData, title: str, message: str) -> ft.Control:
    """목록이 비었을 때 보여 주는 안내."""
    return ft.Container(
        padding=ft.Padding.symmetric(vertical=48, horizontal=24),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            controls=[
                ft.Icon(icon, size=56, color=theme.BROWN_LIGHT),
                ft.Text(
                    title,
                    size=theme.HEADING_SIZE,
                    weight=ft.FontWeight.BOLD,
                    color=theme.BROWN,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    message,
                    size=theme.BODY_SIZE,
                    color=theme.TEXT_MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
        ),
    )
