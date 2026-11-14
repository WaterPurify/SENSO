"""기록 목록과 빠른 작업 패널. 모바일에서는 주요 행동을 목록 위에 배치한다."""

from collections.abc import Callable

import flet as ft

from senso.domain.bean import BeanKind
from senso.domain.brew import Brew, format_number
from senso.taste.dna import MIN_BREWS
from senso.ui import theme
from senso.ui.components.brew_card import brew_card
from senso.ui.components.empty_state import empty_state
from senso.ui.views.landing import eyebrow


class HomeView(ft.Column):
    def adapt(self, width: float) -> None:
        self.mobile_actions.visible = width < 850
        self.desktop_actions.visible = width >= 850


def home_view(
    brews: list[Brew],
    on_new: Callable[[], None],
    on_add_coffee: Callable[[], None],
    on_open: Callable[[Brew], None],
    top: list[ft.Control] | None = None,
    bottom: list[ft.Control] | None = None,
    on_more: Callable[[], None] | None = None,
    *,
    kind: BeanKind | None = None,
    on_filter: Callable[[BeanKind | None], None],
    latest: Brew | None,
    on_repeat: Callable[[Brew], None],
    rated_count: int,
    on_taste: Callable[[], None],
    hero: ft.Control | None = None,
    side_extra: list[ft.Control] | None = None,
) -> ft.Control:
    filters = ft.Row(
        wrap=True,
        spacing=8,
        controls=[
            (ft.FilledButton if selected == kind else ft.OutlinedButton)(
                label, on_click=lambda _, value=selected: on_filter(value)
            )
            for label, selected in [("전체", None), ("커피", BeanKind.COFFEE), ("차", BeanKind.TEA)]
        ],
    )
    records: list[ft.Control] = [
        *(top or []),  # Sen·So 인사와 오늘의 말씀 한 잔: '나의 기록' 바로 위
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("나의 기록", size=22, weight=ft.FontWeight.BOLD),
                ft.Text("최신순", size=12, color=theme.TEXT_MUTED),
            ],
        ),
        filters,
    ]
    if brews:
        records.append(ft.Text(f"최근 기록 {len(brews)}개", size=14, color=theme.TEXT_MUTED))
        records += [brew_card(b, on_open) for b in brews]
    else:
        item = "커피" if kind is BeanKind.COFFEE else "차"
        records.append(
            empty_state(
                ft.Icons.LOCAL_CAFE_OUTLINED,
                "아직 기록이 없어요" if kind is None else f"아직 {item} 기록이 없어요",
                "원두나 차를 등록하고 첫 한 잔을 기록해 보세요.",
            )
        )
    if on_more:
        records.append(ft.TextButton("더 보기", on_click=lambda _: on_more()))
    records += bottom or []

    def actions() -> list[ft.Control]:
        return [
            ft.FilledButton(
                "새 한 잔 기록하기",
                icon=ft.Icons.ADD,
                height=48,
                width=float("inf"),
                on_click=lambda _: on_new(),
            ),
            ft.OutlinedButton(
                "최근 레시피로 다시 추출",
                icon=ft.Icons.REPLAY,
                width=float("inf"),
                disabled=latest is None,
                on_click=lambda _: on_repeat(latest) if latest else None,
            ),
        ]

    quick: list[ft.Control] = [
        eyebrow("TODAY’S RITUAL"),
        ft.Text("새로운 한 잔, 시작해요.", size=21, weight=ft.FontWeight.BOLD),
        ft.Text("오늘의 레시피와 느낌을 남겨보세요.", size=14, color=theme.TEXT_MUTED),
        *actions(),
    ]
    summary = (
        (
            f"{latest.bean.name} · {format_number(latest.recipe.dose_g)}g / "
            f"{format_number(latest.recipe.water_g)}g"
        )
        if latest
        else ("첫 기록을 남기면 레시피를 다시 사용할 수 있어요.")
    )
    quick += [
        ft.Text(summary, size=12, color=theme.TEXT_MUTED),
        ft.TextButton("원두 등록", icon=ft.Icons.COFFEE, on_click=lambda _: on_add_coffee()),
    ]
    taste = ft.Column(
        spacing=14,
        controls=[
            ft.Text("내 취향의 첫 단서", size=18, weight=ft.FontWeight.BOLD),
            ft.Text(
                "취향을 알아가는 중이에요."
                if rated_count < MIN_BREWS
                else "기록에서 찾은 취향을 확인해요.",
                size=14,
            ),
            ft.Text(
                "직접 남긴 기록에 만족도를 매겨주세요. 예시 기록은 분석에서 제외돼요.",
                size=13,
                color=theme.TEXT_MUTED,
            ),
            ft.ProgressBar(
                value=min(rated_count / MIN_BREWS, 1), color=theme.TEA_GREEN, bgcolor=theme.CREAM
            ),
            ft.Text(
                f"만족도를 남긴 기록 {rated_count}개 · 분석 기준 {MIN_BREWS}개",
                size=12,
                color=theme.TEXT_MUTED,
            ),
            ft.TextButton("내 취향 보기", on_click=lambda _: on_taste()),
        ],
    )
    mobile_actions = ft.Column(
        visible=False,
        spacing=8,
        controls=[
            *actions(),
            ft.TextButton("원두 등록", on_click=lambda _: on_add_coffee()),
        ],
    )
    desktop_actions = ft.Container(
        bgcolor="#EDE4D5",
        border_radius=18,
        padding=24,
        content=ft.Column(spacing=14, controls=quick),
    )
    sidebar = ft.Column(
        spacing=18,
        controls=[
            desktop_actions,
            ft.Container(bgcolor="#FFFDFA", border_radius=18, padding=24, content=taste),
            *(side_extra or []),
        ],
    )
    view = HomeView(
        spacing=26,
        controls=[
            hero
            or ft.Column(
                spacing=8,
                controls=[
                    eyebrow("MY DAILY BREW"),
                    ft.Text("오늘은 어떤 한 잔인가요?", size=30, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "잘 맞았던 레시피도, 작은 실험도 차곡차곡.", size=15, color=theme.TEXT_MUTED
                    ),
                ],
            ),
            mobile_actions,
            ft.ResponsiveRow(
                spacing=28,
                run_spacing=24,
                controls=[
                    ft.Column(col={"xs": 12, "md": 7}, spacing=14, controls=records),
                    ft.Container(col={"xs": 12, "md": 5}, content=sidebar),
                ],
            ),
        ],
    )
    view.mobile_actions = mobile_actions
    view.desktop_actions = desktop_actions
    return view
