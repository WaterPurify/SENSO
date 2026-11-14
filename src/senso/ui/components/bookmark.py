"""책갈피 단추: 누르면 저장/해제가 바뀐다."""

from collections.abc import Callable

import flet as ft

from senso.ui import theme


def bookmark_button(active: bool, on_toggle: Callable[[], bool]) -> ft.IconButton:
    """on_toggle은 저장소를 바꾸고 새 상태(저장됨=True)를 돌려준다."""

    def render(on: bool) -> None:
        btn.icon = ft.Icons.BOOKMARK if on else ft.Icons.BOOKMARK_BORDER
        btn.icon_color = theme.BROWN if on else theme.TEXT_MUTED
        btn.tooltip = "책갈피에서 빼기" if on else "책갈피에 넣기"

    def click(_: ft.Event) -> None:
        render(on_toggle())
        btn.update()

    btn = ft.IconButton(on_click=click)
    render(active)
    return btn
