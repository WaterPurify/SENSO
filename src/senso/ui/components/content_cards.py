"""SENSO 소식 카드 (유튜브·인스타그램). 누르면 새 창으로 연다. 주소가 없으면 '준비 중'."""

from collections.abc import Awaitable, Callable

import flet as ft

from senso import art
from senso.content import PLATFORM_NAMES, ContentLink
from senso.ui import theme
from senso.ui.components.bookmark import bookmark_button
from senso.ui.components.brew_card import tag


def content_card(
    link: ContentLink,
    on_open: Callable[[str], Awaitable[None]],
    bookmarked: bool,
    on_bookmark: Callable[[ContentLink], bool],
) -> ft.Control:
    ready = link.url is not None

    async def open_link(_: ft.Event) -> None:
        if link.url:
            await on_open(link.url)

    return ft.Container(
        bgcolor="#FFFFFF",
        border_radius=16,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        ink=ready,
        on_click=open_link if ready else None,
        content=ft.Column(
            spacing=0,
            controls=[
                ft.Container(
                    height=120,
                    image=ft.DecorationImage(
                        src=art.content_art(link.platform), fit=ft.BoxFit.COVER
                    ),
                ),
                ft.Container(
                    padding=ft.Padding.only(left=14, right=4, top=10, bottom=10),
                    content=ft.Row(
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Column(
                                spacing=4,
                                expand=True,
                                controls=[
                                    ft.Row(
                                        spacing=6,
                                        controls=[
                                            tag(PLATFORM_NAMES.get(link.platform, link.platform)),
                                            tag(
                                                "보러 가기" if ready else "준비 중",
                                                bgcolor="#E8F0E0" if ready else "#EEEEEE",
                                                color=theme.TEA_GREEN if ready else "#666666",
                                            ),
                                        ],
                                    ),
                                    ft.Text(
                                        link.title, weight=ft.FontWeight.BOLD, color=theme.BROWN
                                    ),
                                    ft.Text(link.description, size=13, color=theme.TEXT_MUTED),
                                ],
                            ),
                            bookmark_button(bookmarked, lambda: on_bookmark(link)),
                        ],
                    ),
                ),
            ],
        ),
    )


def content_section(
    links: list[ContentLink],
    on_open: Callable[[str], Awaitable[None]],
    is_bookmarked: Callable[[str], bool],
    on_bookmark: Callable[[ContentLink], bool],
) -> ft.Control | None:
    if not links:
        return None
    return ft.Column(
        spacing=10,
        controls=[
            ft.Text("SENSO 소식", size=18, weight=ft.FontWeight.BOLD, color=theme.BROWN),
            ft.Text(
                "영상과 사진은 새 창(유튜브·인스타그램)에서 열려요.",
                size=12,
                color=theme.TEXT_MUTED,
            ),
            ft.ResponsiveRow(
                spacing=12,
                run_spacing=12,
                controls=[
                    ft.Container(
                        col={"xs": 12, "sm": 6, "md": 12},
                        content=content_card(link, on_open, is_bookmarked(link.key), on_bookmark),
                    )
                    for link in links
                ],
            ),
        ],
    )
