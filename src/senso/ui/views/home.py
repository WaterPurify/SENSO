"""① 홈·기록 목록. W1에서는 빈 상태와 버튼만 있다."""

from collections.abc import Callable

import flet as ft

from senso.ui import theme
from senso.ui.components.empty_state import empty_state
from senso.ui.components.header import header


def home_view(on_not_ready: Callable[[str], None]) -> ft.Control:
    return ft.Column(
        spacing=theme.SPACING,
        controls=[
            header("SENSO", "Sen & So와 함께 찾는 나만의 한 잔"),
            ft.Row(
                spacing=12,
                controls=[
                    ft.FilledButton(
                        "새 기록",
                        icon=ft.Icons.ADD,
                        height=48,
                        expand=True,
                        on_click=lambda _: on_not_ready("새 기록"),
                    ),
                    ft.OutlinedButton(
                        "원두 등록",
                        icon=ft.Icons.COFFEE,
                        height=48,
                        expand=True,
                        on_click=lambda _: on_not_ready("원두 등록"),
                    ),
                ],
            ),
            empty_state(
                ft.Icons.LOCAL_CAFE_OUTLINED,
                "아직 기록이 없어요",
                "원두를 등록하고 첫 한 잔을 기록해 보세요.\n"
                "Sen이 다음 레시피를 함께 고민해 줄게요.",
            ),
        ],
    )
