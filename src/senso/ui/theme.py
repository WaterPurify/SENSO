"""SENSO 색상과 글자 크기. 따뜻한 아이보리 배경 + 짙은 브라운."""

import flet as ft

IVORY = "#FAF6EE"
CREAM = "#F1E8D8"
BROWN = "#4A2C1D"
BROWN_LIGHT = "#8B5E3C"
TEXT_MUTED = "#6B5B4E"
TEA_GREEN = "#5E7A4A"  # So(차) 강조색

TITLE_SIZE = 26
HEADING_SIZE = 20
BODY_SIZE = 16
CAPTION_SIZE = 14

SPACING = 16


def app_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=BROWN,
        color_scheme=ft.ColorScheme(
            primary=BROWN,
            on_primary=IVORY,
            secondary=BROWN_LIGHT,
            tertiary=TEA_GREEN,
            surface=IVORY,
            on_surface=BROWN,
            on_surface_variant=TEXT_MUTED,
        ),
        use_material3=True,
    )


def apply(page: ft.Page) -> None:
    page.theme = app_theme()
    page.theme_mode = ft.ThemeMode.LIGHT  # 다크 모드는 MVP 이후
    page.bgcolor = IVORY
