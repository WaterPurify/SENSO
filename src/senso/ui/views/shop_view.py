"""쇼핑 탭: 출시 예정 상품. 결제는 없고 '출시 알림 받기'와 책갈피만."""

from collections.abc import Callable
from dataclasses import dataclass

import flet as ft

from senso import art
from senso.characters.lines import Line, Who
from senso.shop import PRODUCTS, Product
from senso.ui import theme
from senso.ui.components.banner import hero_banner
from senso.ui.components.bookmark import bookmark_button
from senso.ui.components.brew_card import tag
from senso.ui.components.character import speech_bubble


@dataclass
class ShopDeps:
    is_notified: Callable[[str], bool]
    set_notified: Callable[[str, bool], None]
    is_bookmarked: Callable[[str], bool]
    on_bookmark: Callable[[Product], bool]
    notify: Callable[[str], None]


def product_card(p: Product, deps: ShopDeps) -> ft.Control:
    state = {"on": deps.is_notified(p.key)}
    notify_btn = ft.OutlinedButton(height=40)

    def render() -> None:
        notify_btn.content = "알림 신청됨" if state["on"] else "출시 알림 받기"
        notify_btn.icon = (
            ft.Icons.NOTIFICATIONS_ACTIVE if state["on"] else ft.Icons.NOTIFICATIONS_NONE
        )

    def toggle(_: ft.Event) -> None:
        state["on"] = not state["on"]
        deps.set_notified(p.key, state["on"])
        deps.notify(
            f"'{p.name}' 출시 소식을 받아 볼게요." if state["on"] else "출시 알림을 취소했어요."
        )
        render()
        notify_btn.update()

    notify_btn.on_click = toggle
    render()

    return ft.Container(
        bgcolor="#FFFFFF",
        border_radius=18,
        padding=14,
        content=ft.Row(
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Image(src=art.product_art(p.key), width=112, height=112, border_radius=16),
                ft.Column(
                    spacing=6,
                    expand=True,
                    controls=[
                        ft.Row(
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Column(
                                    spacing=4,
                                    expand=True,
                                    controls=[
                                        ft.Row(spacing=6, wrap=True, controls=[tag(p.tag)]),
                                        ft.Text(
                                            p.name,
                                            size=18,
                                            weight=ft.FontWeight.BOLD,
                                            color=theme.BROWN,
                                        ),
                                        ft.Text(
                                            p.price, weight=ft.FontWeight.BOLD, color="#9A4A2E"
                                        ),
                                    ],
                                ),
                                bookmark_button(
                                    deps.is_bookmarked(p.key), lambda: deps.on_bookmark(p)
                                ),
                            ],
                        ),
                        ft.Text(p.summary, color=theme.BROWN),
                        *[ft.Text(f"· {pt}", size=13, color=theme.TEXT_MUTED) for pt in p.points],
                        ft.Row([notify_btn]),
                    ],
                ),
            ],
        ),
    )


def shop_view(deps: ShopDeps) -> ft.Control:
    return ft.Column(
        spacing=theme.SPACING,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            hero_banner("shop", "SENSO 쇼핑", "취향에 맞춘 한 잔을 집으로", eyebrow="COMING SOON"),
            speech_bubble(
                Line(
                    Who.DUO,
                    "아직 준비 중이에요. 마음에 드는 상품에 출시 알림을 신청해 두면 먼저 알려 드릴게요.",
                )
            ),
            *[product_card(p, deps) for p in PRODUCTS],
            ft.Text(
                "아직 결제는 할 수 없어요. 가격과 구성은 출시 전에 바뀔 수 있어요. "
                "알림 신청은 이 기기 계정에만 기록돼요.",
                size=12,
                color=theme.TEXT_MUTED,
            ),
        ],
    )
