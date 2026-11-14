"""오늘의 말씀 한 잔: 소개, 기분 고르기, 말씀 카드, 신앙 소개."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date

import flet as ft

from senso.characters.lines import Line, Who
from senso.db.word_repo import WordCard
from senso.ui import theme
from senso.ui.components.brew_card import tag
from senso.ui.components.character import speech_bubble
from senso.ui.components.inputs import section
from senso.word.card import render_word_card
from senso.word.moods import HELPLINES, MOODS, TRANSLATION, Mood, Verse, is_crisis

WEEKDAYS = "월화수목금토일"
SIDE_WHO = {"sen": Who.SEN, "so": Who.SO}
NOTE_MAX = 80


def _day_text(day: date) -> str:
    return f"{day.month}월 {day.day}일 ({WEEKDAYS[day.weekday()]})"


def _title_row(title: str, on_back: Callable[[], None]) -> ft.Control:
    return ft.Row(
        controls=[
            ft.IconButton(ft.Icons.ARROW_BACK, tooltip="뒤로", on_click=lambda _: on_back()),
            ft.Text(title, size=theme.HEADING_SIZE, weight=ft.FontWeight.BOLD, color=theme.BROWN),
        ]
    )


def _support_note() -> ft.Control:
    return ft.Text(
        "말씀이 상담을 대신하지는 않아요. 마음이 많이 힘들면 109(자살예방상담전화, 24시간)에 전화해 주세요.",
        size=12,
        color=theme.TEXT_MUTED,
    )


# ---- 홈 화면에 붙는 카드 ------------------------------------------------------------


def word_intro(on_enable: Callable[[], None], on_decline: Callable[[], None]) -> ft.Control:
    """아직 켜고 끄기를 고르지 않은 사용자에게 한 번 소개."""
    return section(
        "새 기능 · 오늘의 말씀 한 잔",
        "원하는 분만 켜는 무료 기능이에요",
        [
            ft.Text(
                "하루 한 번 오늘 마음을 고르면, So가 어울리는 차·커피 한 잔과 "
                "성경 말씀 한 구절을 건네 드려요. 언제든 '나' 탭에서 끌 수 있어요.",
                color=theme.BROWN,
            ),
            ft.Row(
                spacing=12,
                controls=[
                    ft.FilledButton(
                        "켜기", icon=ft.Icons.CHECK, expand=True, on_click=lambda _: on_enable()
                    ),
                    ft.OutlinedButton("괜찮아요", expand=True, on_click=lambda _: on_decline()),
                ],
            ),
        ],
    )


def word_home(today: WordCard | None, on_pick: Callable[[], None], on_open) -> ft.Control:
    if today is None:
        return ft.Column(
            spacing=8,
            controls=[
                speech_bubble(
                    Line(Who.SO, "오늘 마음은 어때요? 마음에 맞는 말씀 한 구절을 골라 드릴게요.")
                ),
                ft.OutlinedButton(
                    "오늘 마음 고르기",
                    icon=ft.Icons.FAVORITE_BORDER,
                    height=44,
                    on_click=lambda _: on_pick(),
                ),
            ],
        )
    return ft.Row(
        wrap=True,
        spacing=8,
        run_spacing=8,
        controls=[
            ft.OutlinedButton(
                "오늘의 말씀 다시 보기",
                icon=ft.Icons.MENU_BOOK_OUTLINED,
                height=44,
                on_click=lambda _: on_open(today),
            ),
            ft.TextButton(
                "마음 다시 고르기",
                icon=ft.Icons.REFRESH,
                height=44,
                on_click=lambda _: on_pick(),
            ),
        ],
    )


# ---- 기분 고르기 -------------------------------------------------------------------


@dataclass
class PickDeps:
    on_back: Callable[[], None]
    on_pick: Callable[[str, str | None], None]  # (기분 키, 적은 한 줄)


def word_pick_view(deps: PickDeps) -> ft.Control:
    root = ft.Column(spacing=theme.SPACING, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    note = ft.TextField(
        label="한 줄로 적어도 돼요 (선택)",
        hint_text="예) 내일 발표가 걱정돼요",
        max_length=NOTE_MAX,
    )

    def choose(mood: Mood) -> None:
        if is_crisis(note.value):
            render_crisis(mood)
        else:
            deps.on_pick(mood.key, note.value)

    def render_pick(first: bool = False) -> None:
        root.controls = [
            _title_row("오늘의 말씀 한 잔", deps.on_back),
            speech_bubble(Line(Who.SO, "오늘 마음은 어때요? 가장 가까운 걸 하나 골라 주세요.")),
            note,
            *[
                ft.OutlinedButton(
                    m.label,
                    height=52,
                    style=ft.ButtonStyle(
                        bgcolor="#FFFFFF",
                        shape=ft.RoundedRectangleBorder(radius=14),
                        text_style=ft.TextStyle(
                            size=theme.BODY_SIZE, font_family=theme.FONT_FAMILY
                        ),
                    ),
                    on_click=lambda _, m=m: choose(m),
                )
                for m in MOODS
            ],
            ft.Text("마음이 바뀌면 언제든 다시 고를 수 있어요.", size=12, color=theme.TEXT_MUTED),
        ]
        if not first:
            root.update()

    def render_crisis(mood: Mood) -> None:
        root.controls = [
            _title_row("잠깐만요", render_pick),
            speech_bubble(
                Line(
                    Who.SO,
                    "많이 힘드셨군요. 혼자 견디지 않아도 돼요. 지금 이야기를 들어 줄 수 있는 분들이 있어요.",
                )
            ),
            section(
                "지금 도움을 받을 수 있는 곳",
                "전화하면 바로 상담할 수 있어요",
                [
                    ft.Row(
                        controls=[
                            ft.Text(
                                num,
                                size=theme.HEADING_SIZE,
                                weight=ft.FontWeight.BOLD,
                                color=theme.BROWN,
                                width=130,
                            ),
                            ft.Text(desc, color=theme.BROWN, expand=True),
                        ]
                    )
                    for num, desc in HELPLINES
                ],
            ),
            ft.Text(
                "말씀은 상담이나 치료를 대신하지 않아요. 먼저 꼭 도움을 요청해 주세요.",
                color=theme.BROWN,
            ),
            ft.OutlinedButton(
                "말씀 카드도 보기",
                icon=ft.Icons.MENU_BOOK_OUTLINED,
                height=44,
                on_click=lambda _: deps.on_pick(mood.key, note.value),
            ),
            ft.TextButton("닫기", on_click=lambda _: deps.on_back()),
        ]
        root.update()

    render_pick(first=True)
    return root


# ---- 말씀 카드 ---------------------------------------------------------------------


@dataclass
class CardDeps:
    on_back: Callable[[], None]
    set_saved: Callable[[int, bool], None]
    save_png: Callable[[bytes, str], Awaitable[None]]
    on_faith: Callable[[], None]
    notify: Callable[[str], None]
    on_repick: Callable[[], None] | None = None  # 다시 고르기


def word_card_view(card: WordCard, mood: Mood, verse: Verse, deps: CardDeps) -> ft.Control:
    who = SIDE_WHO[mood.side]
    state = {"saved": card.saved}
    save_btn = ft.OutlinedButton(expand=True, height=44)

    def render_save_btn() -> None:
        save_btn.content = "노트에 저장됨" if state["saved"] else "말씀 노트에 저장"
        save_btn.icon = ft.Icons.BOOKMARK if state["saved"] else ft.Icons.BOOKMARK_BORDER

    def toggle(_: ft.Event) -> None:
        state["saved"] = not state["saved"]
        deps.set_saved(card.id, state["saved"])
        deps.notify("말씀 노트에 저장했어요." if state["saved"] else "말씀 노트에서 뺐어요.")
        render_save_btn()
        save_btn.update()

    save_btn.on_click = toggle
    render_save_btn()

    async def on_png(_: ft.Event) -> None:
        png = render_word_card(mood, verse, card.day)
        await deps.save_png(png, f"SENSO_말씀_{card.day.isoformat()}.png")

    giver = "So" if who is Who.SO else "Sen"
    hello = (
        f"{mood.drink} 한 잔과 함께 이 말씀을 건네요."
        if who is Who.SO
        else f"오늘은 {mood.drink} 어때? 이 말씀이랑 같이!"
    )
    controls: list[ft.Control] = [
        _title_row("오늘의 말씀 한 잔", deps.on_back),
        ft.Row(
            wrap=True,
            spacing=6,
            controls=[
                tag(_day_text(card.day)),
                tag(mood.label, bgcolor="#E8F0E0", color=theme.TEA_GREEN),
            ],
        ),
        speech_bubble(Line(who, hello)),
        ft.Container(
            bgcolor="#FFFFFF",
            border=ft.Border.all(1, "#E9DFD1"),
            border_radius=16,
            padding=20,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Text(verse.text, size=theme.BODY_SIZE + 2, color=theme.BROWN),
                    ft.Text(
                        f"{verse.ref} ({TRANSLATION})",
                        weight=ft.FontWeight.BOLD,
                        color=theme.BROWN_LIGHT,
                    ),
                    ft.Divider(color="#E9DFD1"),
                    ft.Text(verse.meditation, color=theme.TEXT_MUTED, italic=True),
                ],
            ),
        ),
        ft.Container(
            bgcolor=theme.CREAM,
            border_radius=14,
            padding=14,
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.EMOJI_FOOD_BEVERAGE_OUTLINED
                        if who is Who.SO
                        else ft.Icons.COFFEE_OUTLINED,
                        color=theme.BROWN,
                    ),
                    ft.Text(
                        f"{giver}가 건네는 한 잔 · {mood.drink}", color=theme.BROWN, expand=True
                    ),
                ]
            ),
        ),
    ]
    if card.note:
        controls.append(ft.Text(f"내가 적은 한 줄: {card.note}", size=13, color=theme.TEXT_MUTED))
    controls += [
        ft.Row(
            spacing=12,
            controls=[
                save_btn,
                ft.OutlinedButton(
                    "카드 이미지 저장",
                    icon=ft.Icons.DOWNLOAD,
                    expand=True,
                    height=44,
                    on_click=on_png,
                ),
            ],
        ),
    ]
    if deps.on_repick:
        controls.append(
            ft.OutlinedButton(
                "마음 다시 고르기",
                icon=ft.Icons.REFRESH,
                height=44,
                on_click=lambda _: deps.on_repick(),
            )
        )
    controls += [
        ft.TextButton(
            "신앙이 궁금하다면", icon=ft.Icons.CHURCH_OUTLINED, on_click=lambda _: deps.on_faith()
        ),
        _support_note(),
    ]
    return ft.Column(
        spacing=theme.SPACING,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=controls,
    )


# ---- 신앙이 궁금하다면 -------------------------------------------------------------

FAITH_PARAGRAPHS = (
    "SENSO를 만든 사람은 기독교 신앙을 가지고 있어요. 환대·나눔·쉼이라는 SENSO의 가치도 "
    "그 신앙에서 출발했어요.",
    "성경은 하나님이 사람을 사랑하셔서 예수 그리스도를 보내셨고, 누구든지 지친 모습 그대로 "
    "나아올 수 있다고 말해요. 오늘 받은 말씀 한 구절이 그 이야기의 작은 입구가 되면 좋겠어요.",
    "더 알고 싶다면 이렇게 시작해 보세요.",
)
FAITH_STEPS = (
    "요한복음을 하루 한 장씩 천천히 읽어 보기",
    "가까운 교회의 예배나 소모임에 편하게 들러 보기",
    "궁금한 것을 신앙을 가진 친구나 목회자에게 물어보기",
)


def faith_view(on_back: Callable[[], None]) -> ft.Control:
    return ft.Column(
        spacing=theme.SPACING,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            _title_row("신앙이 궁금하다면", on_back),
            speech_bubble(Line(Who.DUO, "궁금한 만큼만, 천천히 둘러보세요. 강요하지 않을게요.")),
            *[ft.Text(p, color=theme.BROWN) for p in FAITH_PARAGRAPHS],
            *[ft.Text(f"· {s}", color=theme.BROWN) for s in FAITH_STEPS],
            ft.Text(
                "말씀 한 잔 기능은 '나' 탭에서 언제든 끌 수 있어요. 커피·차 기능은 그대로 쓸 수 있어요.",
                size=13,
                color=theme.TEXT_MUTED,
            ),
        ],
    )


# ---- '나' 탭 섹션 ------------------------------------------------------------------


def word_me_section(
    enabled: bool,
    notes: list[WordCard],
    on_toggle: Callable[[bool], None],
    on_open: Callable[[WordCard], None],
    on_faith: Callable[[], None],
) -> ft.Control:
    labels = {m.key: m.label for m in MOODS}
    items: list[ft.Control] = [
        ft.Switch(
            label="오늘의 말씀 한 잔 켜기",
            value=enabled,
            on_change=lambda e: on_toggle(bool(e.control.value)),
        ),
    ]
    if notes:
        items.append(ft.Text(f"말씀 노트 {len(notes)}개", size=13, color=theme.TEXT_MUTED))
        items += [
            ft.TextButton(
                f"{_day_text(c.day)} · {c.verse_ref} · {labels.get(c.mood, '')}",
                on_click=lambda _, c=c: on_open(c),
            )
            for c in notes
        ]
    elif enabled:
        items.append(
            ft.Text("마음에 드는 말씀을 저장하면 여기에 모여요.", size=13, color=theme.TEXT_MUTED)
        )
    items.append(
        ft.TextButton(
            "신앙이 궁금하다면", icon=ft.Icons.CHURCH_OUTLINED, on_click=lambda _: on_faith()
        )
    )
    return section("오늘의 말씀 한 잔", "원하는 분만 켜는 무료 기능 · 하루 1회", items)
