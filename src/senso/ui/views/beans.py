"""② 원두·차 목록. 등록 기능은 W2에서 만든다."""

import flet as ft

from senso.ui import theme
from senso.ui.components.empty_state import empty_state
from senso.ui.components.header import header


def beans_view() -> ft.Control:
    return ft.Column(
        spacing=theme.SPACING,
        controls=[
            header("원두·차", "내가 가진 원두와 찻잎"),
            empty_state(
                ft.Icons.INVENTORY_2_OUTLINED,
                "등록한 원두·차가 없어요",
                "자주 마시는 원두나 차를 등록해 두면\n기록할 때 바로 고를 수 있어요.",
            ),
        ],
    )
