import flet as ft

from senso.ui import theme


def header(title: str, subtitle: str | None = None) -> ft.Control:
    """화면 맨 위의 제목과 짧은 설명."""
    controls: list[ft.Control] = [
        ft.Text(title, size=theme.TITLE_SIZE, weight=ft.FontWeight.BOLD, color=theme.BROWN)
    ]
    if subtitle:
        controls.append(ft.Text(subtitle, size=theme.BODY_SIZE, color=theme.TEXT_MUTED))
    return ft.Column(spacing=4, controls=controls)
