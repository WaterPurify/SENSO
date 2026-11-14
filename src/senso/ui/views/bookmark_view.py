"""책갈피 탭: 저장해 둔 기록·원두·차·말씀 카드·상품·소식을 한곳에."""

from collections.abc import Callable
from dataclasses import dataclass

import flet as ft

from senso.db.bookmark_repo import Bookmark
from senso.db.word_repo import WordCard
from senso.ui import theme
from senso.ui.components.banner import hero_banner
from senso.ui.components.empty_state import empty_state
from senso.ui.components.inputs import section

KIND_INFO = {
    "brew": ("기록", ft.Icons.LOCAL_CAFE_OUTLINED),
    "bean": ("원두·차", ft.Icons.COFFEE_OUTLINED),
    "product": ("쇼핑", ft.Icons.STOREFRONT_OUTLINED),
    "content": ("SENSO 소식", ft.Icons.PLAY_CIRCLE_OUTLINE),
}


@dataclass
class BookmarkDeps:
    on_open: Callable[[Bookmark], None]
    on_remove: Callable[[Bookmark], None]
    on_open_word: Callable[[WordCard], None]


def _row(icon: str, title: str, subtitle: str | None, on_open, on_remove=None) -> ft.Control:
    actions: list[ft.Control] = []
    if on_remove:
        actions.append(
            ft.IconButton(
                ft.Icons.BOOKMARK_REMOVE_OUTLINED,
                tooltip="책갈피에서 빼기",
                icon_color=theme.TEXT_MUTED,
                on_click=lambda _: on_remove(),
            )
        )
    return ft.Container(
        bgcolor="#FFFFFF",
        border_radius=12,
        padding=ft.Padding.only(left=12, right=4, top=6, bottom=6),
        ink=True,
        on_click=lambda _: on_open(),
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=theme.BROWN_LIGHT),
                ft.Column(
                    spacing=2,
                    expand=True,
                    controls=[
                        ft.Text(title, weight=ft.FontWeight.BOLD, color=theme.BROWN),
                        *([ft.Text(subtitle, size=12, color=theme.TEXT_MUTED)] if subtitle else []),
                    ],
                ),
                *actions,
                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=theme.TEXT_MUTED),
            ]
        ),
    )


def bookmark_view(
    marks: list[Bookmark],
    words: list[WordCard],
    word_label: Callable[[WordCard], str],
    deps: BookmarkDeps,
) -> ft.Control:
    controls: list[ft.Control] = [
        hero_banner("bookmark", "책갈피", "다시 보고 싶은 것을 모아 두는 곳", eyebrow="BOOKMARKS"),
    ]
    if not marks and not words:
        controls.append(
            empty_state(
                ft.Icons.BOOKMARK_BORDER,
                "아직 책갈피가 없어요",
                "기록·원두·차 화면이나 쇼핑, SENSO 소식에서\n책갈피 단추를 눌러 모아 보세요.",
            )
        )
        return ft.Column(spacing=theme.SPACING, controls=controls)

    for kind, (label, icon) in KIND_INFO.items():
        items = [m for m in marks if m.kind == kind]
        if not items:
            continue
        controls.append(
            section(
                label,
                f"{len(items)}개",
                [
                    _row(
                        icon,
                        m.title,
                        None,
                        on_open=lambda m=m: deps.on_open(m),
                        on_remove=lambda m=m: deps.on_remove(m),
                    )
                    for m in items
                ],
            )
        )
    if words:
        controls.append(
            section(
                "말씀 노트",
                f"{len(words)}개 · 말씀 카드에서 저장한 구절",
                [
                    _row(
                        ft.Icons.MENU_BOOK_OUTLINED,
                        c.verse_ref,
                        word_label(c),
                        on_open=lambda c=c: deps.on_open_word(c),
                    )
                    for c in words
                ],
            )
        )
    return ft.Column(
        spacing=theme.SPACING,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=controls,
    )
