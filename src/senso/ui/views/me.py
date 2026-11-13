"""나: Taste DNA와 설정. 내용은 W7에서 채운다."""

import flet as ft

from senso import __version__
from senso.ui import theme
from senso.ui.components.empty_state import empty_state
from senso.ui.components.header import header


def me_view(schema_version: int) -> ft.Control:
    return ft.Column(
        spacing=theme.SPACING,
        controls=[
            header("나의 취향", "Taste DNA"),
            empty_state(
                ft.Icons.INSIGHTS_OUTLINED,
                "기록이 쌓이면 Taste DNA가 생겨요",
                "기록을 5개 이상 남기면\nSo가 당신의 취향을 설명해 줄게요.",
            ),
            ft.Text(
                f"버전 {__version__} · 데이터 스키마 v{schema_version}",
                size=theme.CAPTION_SIZE,
                color=theme.TEXT_MUTED,
            ),
        ],
    )
