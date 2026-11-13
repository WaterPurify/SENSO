"""① 홈·기록 목록."""

from collections.abc import Callable

import flet as ft

from senso.domain.brew import Brew
from senso.ui import theme
from senso.ui.components.brew_card import brew_card
from senso.ui.components.empty_state import empty_state
from senso.ui.components.header import header


def home_view(
    brews: list[Brew],
    on_new: Callable[[], None],
    on_add_coffee: Callable[[], None],
    on_open: Callable[[Brew], None],
    top: list[ft.Control] | None = None,
    bottom: list[ft.Control] | None = None,
) -> ft.Control:
    controls: list[ft.Control] = [
        header("SENSO", "Sen & So와 함께 찾는 나만의 한 잔"),
        *(top or []),
        ft.Row(
            spacing=12,
            controls=[
                ft.FilledButton(
                    "새 기록",
                    icon=ft.Icons.ADD,
                    height=48,
                    expand=True,
                    on_click=lambda _: on_new(),
                ),
                ft.OutlinedButton(
                    "원두 등록",
                    icon=ft.Icons.COFFEE,
                    height=48,
                    expand=True,
                    on_click=lambda _: on_add_coffee(),
                ),
            ],
        ),
    ]
    if brews:
        controls.append(
            ft.Text(f"최근 기록 {len(brews)}개", size=theme.CAPTION_SIZE, color=theme.TEXT_MUTED)
        )
        controls += [brew_card(b, on_open) for b in brews]
    else:
        controls.append(
            empty_state(
                ft.Icons.LOCAL_CAFE_OUTLINED,
                "아직 기록이 없어요",
                "원두를 등록하고 첫 한 잔을 기록해 보세요.\n"
                "Sen이 다음 레시피를 함께 고민해 줄게요.",
            )
        )
    controls += bottom or []
    return ft.Column(spacing=12, controls=controls)
