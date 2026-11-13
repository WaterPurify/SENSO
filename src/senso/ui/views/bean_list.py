"""커피 탭 / 차 탭: 등록한 원두·차 목록."""

from collections.abc import Callable

import flet as ft

from senso.domain.bean import LABELS, ROAST_LEVELS, TEA_TYPES, Bean, BeanKind
from senso.text import josa
from senso.ui import theme
from senso.ui.components.empty_state import empty_state
from senso.ui.components.header import header

KIND_ICONS = {
    BeanKind.COFFEE: ft.Icons.COFFEE_OUTLINED,
    BeanKind.TEA: ft.Icons.EMOJI_FOOD_BEVERAGE_OUTLINED,
}
SUBTITLES = {
    BeanKind.COFFEE: "내가 가진 원두",
    BeanKind.TEA: "내가 가진 찻잎과 티백",
}
EMPTY_MESSAGES = {
    BeanKind.COFFEE: "자주 마시는 원두를 등록해 두면\n기록할 때 바로 고를 수 있어요.",
    BeanKind.TEA: "자주 마시는 차를 등록해 두면\nSo가 시간대에 맞는 차를 골라 줄 거예요.",
}


def _thumbnail(kind: BeanKind, photo: bytes | None) -> ft.Control:
    if photo:
        return ft.Image(src=photo, width=64, height=64, fit=ft.BoxFit.COVER, border_radius=12)
    return ft.Container(
        width=64,
        height=64,
        border_radius=12,
        bgcolor=theme.CREAM,
        alignment=ft.Alignment.CENTER,
        content=ft.Icon(KIND_ICONS[kind], color=theme.BROWN_LIGHT, size=32),
    )


def describe(bean: Bean) -> str:
    """카드 두 번째 줄: 로스터리 · 로스팅 정도 · 날짜."""
    parts: list[str] = []
    if bean.producer:
        parts.append(bean.producer)
    if bean.kind is BeanKind.COFFEE and bean.roast_level and bean.roast_level != "unknown":
        parts.append(ROAST_LEVELS.get(bean.roast_level, bean.roast_level))
    if bean.kind is BeanKind.TEA and bean.tea_type:
        parts.append(TEA_TYPES.get(bean.tea_type, bean.tea_type))
    if bean.produced_on:
        parts.append(bean.produced_on.strftime("%Y.%m.%d"))
    return " · ".join(parts) if parts else "상세 정보 없음"


def bean_card(bean: Bean, photo: bytes | None, on_open: Callable[[Bean], None]) -> ft.Control:
    return ft.Card(
        bgcolor="#FFFFFF",
        elevation=0.5,
        margin=0,
        content=ft.Container(
            padding=12,
            border_radius=12,
            ink=True,
            on_click=lambda _: on_open(bean),
            content=ft.Row(
                spacing=14,
                controls=[
                    _thumbnail(bean.kind, photo),
                    ft.Column(
                        spacing=2,
                        expand=True,
                        controls=[
                            ft.Text(
                                bean.name,
                                size=theme.BODY_SIZE + 1,
                                weight=ft.FontWeight.BOLD,
                                color=theme.BROWN,
                            ),
                            ft.Text(
                                describe(bean), size=theme.CAPTION_SIZE, color=theme.TEXT_MUTED
                            ),
                        ],
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color=theme.TEXT_MUTED),
                ],
            ),
        ),
    )


def bean_list_view(
    kind: BeanKind,
    beans: list[Bean],
    load_photo: Callable[[str], bytes | None],
    on_add: Callable[[], None],
    on_open: Callable[[Bean], None],
    top: list[ft.Control] | None = None,
) -> ft.Control:
    labels = LABELS[kind]
    controls: list[ft.Control] = [
        header(labels.title, SUBTITLES[kind]),
        *(top or []),
        ft.FilledButton(
            f"{labels.item} 등록",
            icon=ft.Icons.ADD,
            height=48,
            on_click=lambda _: on_add(),
        ),
    ]
    if beans:
        controls.append(ft.Text(f"{len(beans)}개", size=theme.CAPTION_SIZE, color=theme.TEXT_MUTED))
        controls += [
            bean_card(b, load_photo(b.photo_path) if b.photo_path else None, on_open) for b in beans
        ]
    else:
        controls.append(
            empty_state(
                KIND_ICONS[kind], f"등록한 {josa(labels.item, '이')} 없어요", EMPTY_MESSAGES[kind]
            )
        )
    return ft.Column(spacing=12, controls=controls)
