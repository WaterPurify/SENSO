"""화면 맨 위 그림 배너 (senso.art가 그린 그림 위에 제목)."""

import flet as ft

from senso import art
from senso.ui import theme


def hero_banner(
    art_key: str, title: str, subtitle: str | None = None, eyebrow: str | None = None
) -> ft.Control:
    texts: list[ft.Control] = []
    if eyebrow:
        texts.append(ft.Text(eyebrow, size=11, color=theme.TEXT_MUTED))
    texts.append(ft.Text(title, size=26, weight=ft.FontWeight.BOLD, color=theme.BROWN))
    if subtitle:
        texts.append(ft.Text(subtitle, size=14, color=theme.BROWN))
    return ft.Container(
        height=150,
        border_radius=20,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        image=ft.DecorationImage(
            src=art.banner(art_key),
            fit=ft.BoxFit.COVER,
            alignment=ft.Alignment.CENTER_RIGHT,
        ),
        padding=ft.Padding.symmetric(horizontal=24, vertical=18),
        alignment=ft.Alignment.CENTER_LEFT,
        content=ft.Container(
            width=330,
            content=ft.Column(
                spacing=4,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=texts,
            ),
        ),
    )


def page_background(content: ft.Control) -> ft.Control:
    """앱 전체 배경: 아이보리 바탕에 옅은 커피콩·찻잎 무늬."""
    return ft.Container(
        expand=True,
        bgcolor=theme.IVORY,
        image=ft.DecorationImage(
            src=art.pattern_tile(),
            repeat=ft.ImageRepeat.REPEAT,
            fit=ft.BoxFit.NONE,
            opacity=0.9,
        ),
        content=content,
    )
