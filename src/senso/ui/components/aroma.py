"""향(냄새) 평가 입력과 표시. 계열을 고르면 그 안의 세부 향이 펼쳐진다 (플레이버 휠처럼)."""

import flet as ft

from senso.domain.aroma import AROMA_INTENSITY, AROMAS, AromaGroup, groups_by_key
from senso.domain.bean import BeanKind
from senso.ui import theme
from senso.ui.components.inputs import ScoreInput


def _dot(color: str, size: int = 10) -> ft.Control:
    return ft.Container(width=size, height=size, border_radius=size / 2, bgcolor=color)


def _tint(color: str) -> str:
    """계열 색을 아주 옅게 (#RRGGBB → 18% 불투명)."""
    return f"#2E{color.lstrip('#')}"


class AromaPicker:
    def __init__(
        self,
        kind: BeanKind,
        groups: tuple[str, ...] | list[str] = (),
        notes: tuple[str, ...] | list[str] = (),
        intensity: int | None = None,
    ):
        self.kind = kind
        self._groups: tuple[AromaGroup, ...] = AROMAS[kind]
        known = groups_by_key(kind)
        self._selected_groups = [g for g in groups if g in known]
        all_notes = {n for g in self._groups for n in g.notes}
        self._selected_notes = [n for n in notes if n in all_notes]
        self.intensity = ScoreInput("aroma_intensity", intensity, labels=AROMA_INTENSITY)

        self._group_chips = [
            ft.Chip(
                label=ft.Text(g.label),
                leading=_dot(g.color),
                data=g.key,
                selected=g.key in self._selected_groups,
                show_checkmark=False,
                selected_color=_tint(g.color),
                bgcolor="#FFFFFF",
                on_select=self._on_group,
            )
            for g in self._groups
        ]
        self._notes_box = ft.Column(spacing=8)
        self.control = ft.Column(
            spacing=10,
            controls=[
                ft.Text("향 (냄새)", weight=ft.FontWeight.BOLD, color=theme.BROWN),
                ft.Text(
                    "어떤 향이 났나요? 큰 계열을 고르면 세부 향을 고를 수 있어요.",
                    size=12,
                    color=theme.TEXT_MUTED,
                ),
                ft.Row(wrap=True, spacing=8, run_spacing=8, controls=self._group_chips),
                self._notes_box,
                self.intensity.control,
            ],
        )
        self._render_notes()

    # ---- 값 ---------------------------------------------------------------
    @property
    def groups(self) -> list[str]:
        return [g.key for g in self._groups if g.key in self._selected_groups]

    @property
    def notes(self) -> list[str]:
        return list(self._selected_notes)

    # ---- 이벤트 -------------------------------------------------------------
    def _on_group(self, e: ft.Event) -> None:
        key = e.control.data
        if e.control.selected:
            if key not in self._selected_groups:
                self._selected_groups.append(key)
        else:
            self._selected_groups = [g for g in self._selected_groups if g != key]
            group = groups_by_key(self.kind)[key]
            self._selected_notes = [n for n in self._selected_notes if n not in group.notes]
        self._render_notes()
        self.control.update()

    def _on_note(self, e: ft.Event) -> None:
        note = e.control.data
        if e.control.selected and note not in self._selected_notes:
            self._selected_notes.append(note)
        elif not e.control.selected:
            self._selected_notes = [n for n in self._selected_notes if n != note]

    def _render_notes(self) -> None:
        rows: list[ft.Control] = []
        for g in self._groups:
            if g.key not in self._selected_groups:
                continue
            rows.append(
                ft.Container(
                    border=ft.Border.only(left=ft.BorderSide(3, g.color)),
                    padding=ft.Padding.only(left=10),
                    content=ft.Row(
                        wrap=True,
                        spacing=6,
                        run_spacing=6,
                        controls=[
                            ft.Text(g.label, size=12, color=g.color, weight=ft.FontWeight.BOLD),
                            *[
                                ft.Chip(
                                    label=ft.Text(n, size=13),
                                    data=n,
                                    selected=n in self._selected_notes,
                                    show_checkmark=False,
                                    selected_color=_tint(g.color),
                                    bgcolor="#FFFFFF",
                                    on_select=self._on_note,
                                )
                                for n in g.notes
                            ],
                        ],
                    ),
                )
            )
        self._notes_box.controls = rows
        self._notes_box.visible = bool(rows)


def aroma_summary(
    kind: BeanKind, groups: tuple[str, ...], notes: tuple[str, ...]
) -> list[ft.Control]:
    """상세 화면용: 계열별로 색 점과 세부 향을 한 줄씩."""
    known = groups_by_key(kind)
    rows: list[ft.Control] = []
    for key in groups:
        g = known.get(key)
        if g is None:
            continue
        inner = [n for n in notes if n in g.notes]
        rows.append(
            ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    _dot(g.color, 12),
                    ft.Text(g.label, weight=ft.FontWeight.BOLD, color=theme.BROWN, width=72),
                    ft.Text(" · ".join(inner) if inner else "-", color=theme.BROWN, expand=True),
                ],
            )
        )
    return rows
