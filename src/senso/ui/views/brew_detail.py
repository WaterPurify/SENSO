"""④ 기록 상세: 원했던 맛 / 레시피 / 실제로 느낀 맛 / 연결된 기록."""

from collections.abc import Callable
from dataclasses import dataclass

import flet as ft

from senso.db.brew_repo import BrewRepository
from senso.domain.aroma import AROMA_INTENSITY
from senso.domain.bean import LABELS, ROAST_LEVELS, TEA_TYPES, BeanKind
from senso.domain.brew import NEXT_WISHES, SCORE_FIELDS, Brew, format_number, format_time
from senso.ui import theme
from senso.ui.components.aroma import aroma_summary
from senso.ui.components.brew_card import format_when, satisfaction_tag, tag
from senso.ui.components.flag import flagged_name
from senso.ui.components.inputs import section
from senso.ui.components.tea_info import tea_info_card


@dataclass
class DetailDeps:
    brews: BrewRepository
    notify: Callable[[str], None]
    confirm: Callable[[str, str, str, Callable[[], None]], None]
    on_back: Callable[[], None]
    on_edit: Callable[[Brew], None]
    on_open: Callable[[int], None]
    on_deleted: Callable[[], None]
    on_recommend: Callable[[Brew], None] | None = None
    on_compare: Callable[[int, int], None] | None = None  # (이전 기록 id, 이 기록 id)


def info_row(label: str, value: str) -> ft.Control:
    return ft.Row(
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[
            ft.Text(label, width=96, color=theme.TEXT_MUTED, size=theme.CAPTION_SIZE + 1),
            ft.Text(value, expand=True, color=theme.BROWN, size=theme.BODY_SIZE),
        ],
    )


def recipe_rows(brew: Brew) -> list[ft.Control]:
    r = brew.recipe
    coffee = brew.kind is BeanKind.COFFEE
    rows = [
        info_row("원두량" if coffee else "찻잎 양", format_number(r.dose_g, "g")),
        info_row("물양", format_number(r.water_g, "g")),
        info_row("비율", f"1 : {r.ratio:.1f}"),
        info_row("수온", format_number(r.temp_c, "°C")),
    ]
    if coffee:
        rows.append(info_row("분쇄도", r.grind or "-"))
    rows.append(info_row("추출 시간", format_time(r.time_s)))
    if brew.iced:
        rows.append(info_row("얼음량", format_number(r.ice_g, "g")))
    rows.append(info_row("추출 도구", brew.dripper or "-"))
    if coffee:
        rows.append(info_row("그라인더", brew.grinder or "-"))
    if brew.notes:
        rows.append(info_row("메모", brew.notes))
    return rows


def score_row(key: str, value: int | None, labels: tuple[str, str, str] | None = None):
    label, low, high = labels or SCORE_FIELDS[key]
    dots = [
        ft.Container(
            width=14,
            height=14,
            border_radius=7,
            bgcolor=theme.BROWN if value is not None and i <= value else "#E9DFD1",
        )
        for i in range(1, 6)
    ]
    text = "미입력" if value is None else f"{value}점"
    return ft.Row(
        controls=[
            ft.Text(label, width=56, color=theme.TEXT_MUTED, size=theme.CAPTION_SIZE + 1),
            ft.Row(spacing=4, controls=dots),
            ft.Text(text, color=theme.BROWN if value is not None else theme.TEXT_MUTED, size=13),
            ft.Text(f"({low}→{high})", color=theme.TEXT_MUTED, size=12),
        ]
    )


def bean_line(brew: Brew) -> str:
    b = brew.bean
    parts = [LABELS[b.kind].title]
    if b.producer:
        parts.append(b.producer)
    if b.kind is BeanKind.COFFEE and b.roast_level and b.roast_level != "unknown":
        parts.append(ROAST_LEVELS.get(b.roast_level, b.roast_level))
    if b.kind is BeanKind.TEA and b.tea_type:
        parts.append(TEA_TYPES.get(b.tea_type, b.tea_type))
    return " · ".join(parts)


def brew_detail_view(brew: Brew, deps: DetailDeps) -> ft.Control:
    t = brew.tasting
    tags: list[ft.Control] = [satisfaction_tag(brew), tag("아이스" if brew.iced else "따뜻하게")]
    if brew.is_sample:
        tags.append(tag("예시", bgcolor="#EEEEEE", color="#555555"))

    # ---- 원했던 맛 ---------------------------------------------------------
    wanted = (
        ft.Row(wrap=True, spacing=6, controls=[tag(f) for f in brew.desired_flavors])
        if brew.desired_flavors
        else ft.Text("고르지 않았어요", color=theme.TEXT_MUTED)
    )

    # ---- 실제로 느낀 맛 -------------------------------------------------------
    if t.is_empty:
        felt: list[ft.Control] = [
            ft.Text("아직 평가가 없어요. 마셔 보고 느낀 맛을 남겨 주세요.", color=theme.TEXT_MUTED),
            ft.OutlinedButton(
                "평가 추가",
                icon=ft.Icons.RATE_REVIEW_OUTLINED,
                on_click=lambda _: deps.on_edit(brew),
            ),
        ]
    else:
        felt = [score_row(k, getattr(t, k)) for k in SCORE_FIELDS]
        if t.aromas or t.aroma_intensity:
            felt.append(ft.Divider(color="#EFE6D8"))
            felt.append(ft.Text("향", weight=ft.FontWeight.BOLD, color=theme.BROWN))
            felt += aroma_summary(brew.kind, t.aromas, t.aroma_notes)
            felt.append(score_row("aroma_intensity", t.aroma_intensity, AROMA_INTENSITY))
        if t.notes:
            felt.append(info_row("느낀 점", t.notes))
        if t.next_wish:
            felt.append(
                ft.Row(
                    wrap=True,
                    spacing=6,
                    controls=[
                        ft.Text("다음엔", color=theme.TEXT_MUTED, size=theme.CAPTION_SIZE + 1),
                        *[
                            tag(NEXT_WISHES.get(w, w), bgcolor="#E8F0E0", color=theme.TEA_GREEN)
                            for w in t.next_wish
                        ],
                    ],
                )
            )
        if t.next_memo:
            felt.append(info_row("다음 메모", t.next_memo))

    # ---- 연결된 기록 ---------------------------------------------------------
    links: list[ft.Control] = []
    if brew.based_on_brew_id:
        parent = deps.brews.get(brew.based_on_brew_id)
        if parent:
            links.append(
                ft.TextButton(
                    f"← {format_when(parent.brewed_at)} 기록의 제안으로 만든 기록이에요",
                    on_click=lambda _: deps.on_open(parent.id),
                )
            )
            if deps.on_compare:
                links.append(
                    ft.OutlinedButton(
                        "이전 기록과 비교",
                        icon=ft.Icons.COMPARE_ARROWS,
                        on_click=lambda _: deps.on_compare(parent.id, brew.id),
                    )
                )
    for child in deps.brews.derived_from(brew.id):
        links.append(
            ft.TextButton(
                f"→ {format_when(child.brewed_at)}에 이 기록을 바탕으로 다시 추출했어요",
                on_click=lambda _, cid=child.id: deps.on_open(cid),
            )
        )

    def on_delete(_: ft.Event) -> None:
        def really() -> None:
            deps.brews.delete(brew.id)
            deps.notify("기록을 지웠어요.")
            deps.on_deleted()

        deps.confirm(
            "기록을 지울까요?",
            f"{format_when(brew.brewed_at)} '{brew.bean.name}' 기록을 지우면 되돌릴 수 없어요.",
            "지우기",
            really,
        )

    actions: list[ft.Control] = []
    if deps.on_recommend:
        actions.append(
            ft.FilledButton(
                "다음 레시피 보기",
                icon=ft.Icons.AUTO_AWESOME,
                height=48,
                on_click=lambda _: deps.on_recommend(brew),
            )
        )
    actions.append(
        ft.Row(
            spacing=12,
            controls=[
                ft.OutlinedButton(
                    "고치기",
                    icon=ft.Icons.EDIT_OUTLINED,
                    height=44,
                    expand=True,
                    on_click=lambda _: deps.on_edit(brew),
                ),
                ft.OutlinedButton(
                    "지우기",
                    icon=ft.Icons.DELETE_OUTLINE,
                    height=44,
                    expand=True,
                    style=ft.ButtonStyle(color=ft.Colors.RED_700),
                    on_click=on_delete,
                ),
            ],
        )
    )

    return ft.Column(
        spacing=theme.SPACING,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            ft.Row(
                controls=[
                    ft.IconButton(
                        ft.Icons.ARROW_BACK, tooltip="뒤로", on_click=lambda _: deps.on_back()
                    ),
                    ft.Column(
                        spacing=0,
                        expand=True,
                        controls=[
                            flagged_name(
                                brew.bean.name,
                                brew.bean.origin,
                                size=theme.HEADING_SIZE,
                                weight=ft.FontWeight.BOLD,
                                color=theme.BROWN,
                            ),
                            ft.Text(
                                f"{format_when(brew.brewed_at)} · {bean_line(brew)}",
                                size=theme.CAPTION_SIZE,
                                color=theme.TEXT_MUTED,
                            ),
                        ],
                    ),
                ]
            ),
            ft.Row(wrap=True, spacing=6, controls=tags),
            section("원했던 맛", "추출 전에 고른 오늘의 선호", [wanted]),
            section("레시피", None, recipe_rows(brew)),
            section("실제로 느낀 맛", "마셔 본 뒤의 평가", felt),
            *(
                [card]
                if brew.kind is BeanKind.TEA and (card := tea_info_card(brew.bean.tea_type))
                else []
            ),
            *([section("연결된 기록", None, links)] if links else []),
            *actions,
        ],
    )
