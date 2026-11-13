"""두 레시피·두 기록을 나란히 비교하는 표. 달라진 칸은 강조한다."""

import flet as ft

from senso.domain.bean import BeanKind
from senso.domain.brew import SCORE_FIELDS, Recipe, Tasting, format_number, format_time
from senso.ui import theme

HIGHLIGHT = "#FFF1D6"


def recipe_values(recipe: Recipe, kind: BeanKind, iced: bool) -> list[tuple[str, str]]:
    coffee = kind is BeanKind.COFFEE
    rows = [
        ("원두량" if coffee else "찻잎 양", format_number(recipe.dose_g, "g")),
        ("물양", format_number(recipe.water_g, "g")),
        ("비율", f"1 : {recipe.ratio:.1f}"),
        ("수온", format_number(recipe.temp_c, "°C")),
    ]
    if coffee:
        rows.append(("분쇄도", recipe.grind or "-"))
    rows.append(("추출 시간", format_time(recipe.time_s)))
    if iced:
        rows.append(("얼음량", format_number(recipe.ice_g, "g")))
    return rows


def tasting_values(t: Tasting) -> list[tuple[str, str]]:
    return [
        (SCORE_FIELDS[k][0], "-" if getattr(t, k) is None else f"{getattr(t, k)}점")
        for k in SCORE_FIELDS
    ]


def compare_table(
    left_title: str,
    right_title: str,
    left: list[tuple[str, str]],
    right: list[tuple[str, str]],
    overrides: dict[str, str] | None = None,
) -> ft.Control:
    """같은 순서의 (항목, 값) 목록 두 개를 비교한다. overrides로 오른쪽 값을 바꿔 보일 수 있다."""
    overrides = overrides or {}
    right_map = dict(right)

    def cell(text: str, bold: bool = False, color: str = theme.BROWN) -> ft.Control:
        return ft.Text(
            text,
            expand=1,
            size=theme.BODY_SIZE - 1,
            color=color,
            weight=ft.FontWeight.BOLD if bold else None,
        )

    rows: list[ft.Control] = [
        ft.Row(
            controls=[
                cell("", color=theme.TEXT_MUTED),
                cell(left_title, bold=True, color=theme.TEXT_MUTED),
                cell(right_title, bold=True),
            ]
        ),
        ft.Divider(height=1, color="#E9DFD1"),
    ]
    for label, lvalue in left:
        rvalue = overrides.get(label, right_map.get(label, "-"))
        changed = rvalue != lvalue
        rows.append(
            ft.Container(
                bgcolor=HIGHLIGHT if changed else None,
                border_radius=8,
                padding=ft.Padding.symmetric(horizontal=6, vertical=6),
                content=ft.Row(
                    controls=[
                        cell(label, color=theme.TEXT_MUTED),
                        cell(lvalue, color=theme.TEXT_MUTED if changed else theme.BROWN),
                        cell(rvalue, bold=changed),
                    ]
                ),
            )
        )
    return ft.Column(spacing=2, controls=rows)
