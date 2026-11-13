"""기록 화면에서 쓰는 입력 부품: 1~5점 선택, 칩 선택."""

from collections.abc import Callable, Iterable

import flet as ft

from senso.domain.brew import SCORE_FIELDS
from senso.ui import theme

_BTN = 40
_GAP = 8


class ScoreInput:
    """1~5점 버튼. 같은 점수를 다시 누르면 '미입력'으로 돌아간다(중간 점수와 구분)."""

    def __init__(self, key: str, value: int | None = None):
        label, low, high = SCORE_FIELDS[key]
        self.key = key
        self.value = value
        self._buttons = [
            ft.Container(
                width=_BTN,
                height=_BTN,
                border_radius=_BTN / 2,
                alignment=ft.Alignment.CENTER,
                data=i,
                on_click=self._on_click,
                tooltip=f"{i}점",
                content=ft.Text(str(i), weight=ft.FontWeight.BOLD),
            )
            for i in range(1, 6)
        ]
        self._status = ft.Text(size=theme.CAPTION_SIZE)
        width = _BTN * 5 + _GAP * 4
        self.control = ft.Column(
            spacing=4,
            controls=[
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.Text(label, weight=ft.FontWeight.BOLD, color=theme.BROWN, width=56),
                        self._status,
                    ],
                ),
                ft.Row(spacing=_GAP, controls=self._buttons),
                ft.Container(
                    width=width,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(low, size=12, color=theme.TEXT_MUTED),
                            ft.Text(high, size=12, color=theme.TEXT_MUTED),
                        ],
                    ),
                ),
            ],
        )
        self._render()

    def _on_click(self, e: ft.Event) -> None:
        score = e.control.data
        self.value = None if self.value == score else score
        self._render()
        self.control.update()

    def _render(self) -> None:
        for btn in self._buttons:
            selected = btn.data == self.value
            btn.bgcolor = theme.BROWN if selected else "#FFFFFF"
            btn.border = ft.Border.all(1, theme.BROWN if selected else "#D9CBB8")
            btn.content.color = theme.IVORY if selected else theme.BROWN
        if self.value is None:
            self._status.value = "미입력"
            self._status.color = theme.TEXT_MUTED
        else:
            self._status.value = f"{self.value}점"
            self._status.color = theme.BROWN


class ChipGroup:
    """여러 개를 고르는 칩. exclusive에 있는 값은 다른 값과 함께 고를 수 없다."""

    def __init__(
        self,
        options: Iterable[tuple[str, str]],
        selected: Iterable[str] = (),
        exclusive: Iterable[str] = (),
        on_change: Callable[[], None] | None = None,
    ):
        self.exclusive = set(exclusive)
        self.on_change = on_change
        chosen = set(selected)
        self._chips = [
            ft.Chip(
                label=ft.Text(text),
                data=key,
                selected=key in chosen,
                show_checkmark=False,
                selected_color=theme.CREAM,
                bgcolor="#FFFFFF",
                on_select=self._on_select,
            )
            for key, text in options
        ]
        self.control = ft.Row(wrap=True, spacing=8, run_spacing=8, controls=self._chips)

    @property
    def value(self) -> list[str]:
        return [c.data for c in self._chips if c.selected]

    def _on_select(self, e: ft.Event) -> None:
        chip = e.control
        if chip.selected:
            for other in self._chips:
                if other is chip:
                    continue
                if chip.data in self.exclusive or other.data in self.exclusive:
                    other.selected = False
        self.control.update()
        if self.on_change:
            self.on_change()


def section(title: str, subtitle: str | None, controls: list[ft.Control]) -> ft.Control:
    """흰 카드 안에 제목과 입력들을 묶는다."""
    head: list[ft.Control] = [
        ft.Text(title, size=theme.HEADING_SIZE - 2, weight=ft.FontWeight.BOLD, color=theme.BROWN)
    ]
    if subtitle:
        head.append(ft.Text(subtitle, size=theme.CAPTION_SIZE, color=theme.TEXT_MUTED))
    return ft.Container(
        bgcolor="#FFFFFF",
        border_radius=16,
        padding=16,
        content=ft.Column(
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[ft.Column(spacing=2, controls=head), *controls],
        ),
    )
