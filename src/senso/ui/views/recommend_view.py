"""다음 레시피 제안 화면."""

from collections.abc import Callable
from dataclasses import dataclass

import flet as ft

from senso.domain.brew import Brew
from senso.origin import with_flag
from senso.recommend.engine import NoRecommendation, Recommendation, Result
from senso.text import josa, quote
from senso.ui import theme
from senso.ui.components.brew_card import format_when, tag
from senso.ui.components.inputs import section


@dataclass
class RecommendDeps:
    on_back: Callable[[], None]
    on_edit: Callable[[Brew], None]
    # W6: 제안대로 새 기록 만들기, 비교 표, 캐릭터 말풍선
    on_brew_again: Callable[[Brew, Recommendation], None] | None = None
    extra_top: Callable[[Brew, Result], list[ft.Control]] | None = None
    extra_bottom: Callable[[Brew, Result], list[ft.Control]] | None = None


def change_card(rec: Recommendation) -> ft.Control:
    return ft.Container(
        bgcolor=theme.CREAM,
        border_radius=12,
        padding=16,
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Text(
                    f"바꿀 조건: {rec.field_label}",
                    size=theme.CAPTION_SIZE + 1,
                    color=theme.TEXT_MUTED,
                ),
                ft.Row(
                    wrap=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(rec.from_value, size=theme.HEADING_SIZE, color=theme.TEXT_MUTED),
                        ft.Icon(ft.Icons.ARROW_FORWARD, color=theme.BROWN),
                        ft.Text(
                            rec.to_value,
                            size=theme.HEADING_SIZE,
                            weight=ft.FontWeight.BOLD,
                            color=theme.BROWN,
                        ),
                    ],
                ),
                *(
                    [
                        ft.Text(
                            "그라인더마다 눈금이 달라 방향만 알려 드려요.",
                            size=13,
                            color=theme.TEXT_MUTED,
                        )
                    ]
                    if rec.direction_only
                    else []
                ),
            ],
        ),
    )


def recommend_view(brew: Brew, result: Result, deps: RecommendDeps) -> ft.Control:
    body: list[ft.Control] = []
    if isinstance(result, Recommendation):
        body.append(
            section(
                f"{josa(quote(result.goal_label), '을')} 위한 제안",
                "한 번에 한 가지 조건만 바꿔요",
                [
                    change_card(result),
                    ft.Text(result.reason, size=theme.BODY_SIZE, color=theme.BROWN),
                    *(
                        [ft.Text(result.note, size=theme.CAPTION_SIZE + 1, color=theme.TEXT_MUTED)]
                        if result.note
                        else []
                    ),
                ],
            )
        )
        if deps.on_brew_again:
            body.append(
                ft.FilledButton(
                    "이 레시피로 새 기록",
                    icon=ft.Icons.REPLAY,
                    height=48,
                    on_click=lambda _: deps.on_brew_again(brew, result),
                )
            )
    else:
        body.append(_no_recommendation(brew, result, deps))

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
                            ft.Text(
                                "다음 레시피",
                                size=theme.HEADING_SIZE,
                                weight=ft.FontWeight.BOLD,
                                color=theme.BROWN,
                            ),
                            ft.Text(
                                f"{with_flag(brew.bean.name, brew.bean.origin)} · "
                                f"{format_when(brew.brewed_at)} 기록 기준",
                                size=theme.CAPTION_SIZE,
                                color=theme.TEXT_MUTED,
                            ),
                        ],
                    ),
                ]
            ),
            ft.Row(
                controls=[
                    tag(f"규칙 기반 제안 ({result.method})", bgcolor="#EEEEEE", color="#555555"),
                ]
            ),
            *(deps.extra_top(brew, result) if deps.extra_top else []),
            *body,
            *(deps.extra_bottom(brew, result) if deps.extra_bottom else []),
        ],
    )


def _no_recommendation(brew: Brew, result: NoRecommendation, deps: RecommendDeps) -> ft.Control:
    titles = {
        "no_tasting": "먼저 맛을 알려 주세요",
        "satisfied": "지금 레시피를 지켜 봐요",
        "conflict": "바람이 서로 부딪쳐요",
        "unclear": "어느 쪽으로 바꿀지 알려 주세요",
        "missing": "기록이 조금 더 필요해요",
        "unsupported": "아직 준비 중인 제안이에요",
        "limit": "더 바꾸기 어려워요",
    }
    controls: list[ft.Control] = [ft.Text(result.reason, size=theme.BODY_SIZE, color=theme.BROWN)]
    if result.kind in {"no_tasting", "conflict", "unclear", "missing"}:
        label = "평가 추가" if result.kind == "no_tasting" else "기록 고치기"
        controls.append(
            ft.OutlinedButton(
                label, icon=ft.Icons.EDIT_OUTLINED, on_click=lambda _: deps.on_edit(brew)
            )
        )
    return section(titles.get(result.kind, "제안할 수 없어요"), None, controls)
