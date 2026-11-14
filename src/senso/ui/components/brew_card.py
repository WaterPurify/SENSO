"""홈 목록의 기록 카드."""

from collections.abc import Callable
from datetime import datetime

import flet as ft

from senso.domain.bean import BeanKind
from senso.domain.brew import Brew, format_number, format_time
from senso.ui import theme
from senso.ui.components.flag import flagged_name

WEEKDAYS = "월화수목금토일"


def format_when(when: datetime) -> str:
    return f"{when.month}월 {when.day}일 ({WEEKDAYS[when.weekday()]}) {when:%H:%M}"


def tag(text: str, bgcolor: str = theme.CREAM, color: str = theme.BROWN) -> ft.Control:
    return ft.Container(
        bgcolor=bgcolor,
        border_radius=10,
        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
        content=ft.Text(text, size=12, color=color, weight=ft.FontWeight.W_600),
    )


def satisfaction_tag(brew: Brew) -> ft.Control:
    score = brew.tasting.satisfaction
    if score is None:
        return tag("평가 전", bgcolor="#FFF1D6", color="#8A5A00")
    return tag("★" * score + "☆" * (5 - score), bgcolor="#FFFFFF")


def brew_card(brew: Brew, on_open: Callable[[Brew], None]) -> ft.Control:
    kind_icon = (
        ft.Icons.COFFEE_OUTLINED
        if brew.kind is BeanKind.COFFEE
        else ft.Icons.EMOJI_FOOD_BEVERAGE_OUTLINED
    )
    tags: list[ft.Control] = [satisfaction_tag(brew)]
    if brew.iced:
        tags.append(tag("아이스", bgcolor="#E3F0F7", color="#1F5A7A"))
    if brew.based_on_brew_id:
        tags.append(
            tag(
                "제안 적용" if brew.based_on_rec_id else "다시 추출",
                bgcolor="#E8F0E0",
                color=theme.TEA_GREEN,
            )
        )
    if brew.is_sample:
        tags.append(tag("예시", bgcolor="#EEEEEE", color="#555555"))

    sub = format_when(brew.brewed_at)
    if brew.dripper:
        sub += f" · {brew.dripper}"

    return ft.Card(
        bgcolor="#FFFFFF",
        elevation=0.5,
        margin=0,
        content=ft.Container(
            padding=12,
            border_radius=12,
            ink=True,
            on_click=lambda _: on_open(brew),
            content=ft.Row(
                spacing=14,
                controls=[
                    ft.Container(
                        width=48,
                        height=48,
                        border_radius=24,
                        bgcolor=theme.CREAM,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(kind_icon, color=theme.BROWN_LIGHT),
                    ),
                    ft.Column(
                        spacing=4,
                        expand=True,
                        controls=[
                            flagged_name(
                                brew.bean.name,
                                brew.bean.origin,
                                size=theme.BODY_SIZE + 1,
                                weight=ft.FontWeight.BOLD,
                                color=theme.BROWN,
                            ),
                            ft.Text(sub, size=theme.CAPTION_SIZE, color=theme.TEXT_MUTED),
                            ft.Text(
                                f"{format_number(brew.recipe.dose_g)}g / "
                                f"{format_number(brew.recipe.water_g)}g · "
                                f"{format_number(brew.recipe.temp_c, '°C')} · "
                                f"{format_time(brew.recipe.time_s)}",
                                size=13,
                                color=theme.TEXT_MUTED,
                            ),
                            ft.Row(spacing=6, wrap=True, controls=tags),
                        ],
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color=theme.TEXT_MUTED),
                ],
            ),
        ),
    )
