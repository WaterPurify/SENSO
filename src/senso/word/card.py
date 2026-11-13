"""말씀 카드 이미지 (1080×1920, 인스타그램 스토리 크기)."""

import io
from datetime import date

from PIL import Image, ImageDraw

from senso.taste.card import ACCENT, ASSETS, BROWN, CREAM, HEIGHT, IVORY, MUTED, WIDTH
from senso.taste.card import _center as center
from senso.taste.card import _font as font
from senso.taste.card import _wrap as wrap
from senso.word.moods import TRANSLATION, Mood, Verse

WEEKDAYS = "월화수목금토일"
SIDE_NAMES = {"sen": "Sen", "so": "So"}


def render_word_card(mood: Mood, verse: Verse, day: date) -> bytes:
    accent = ACCENT[mood.side]
    img = Image.new("RGB", (WIDTH, HEIGHT), IVORY)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, WIDTH, 24], fill=accent)
    y = center(draw, 100, "오늘의 말씀 한 잔", font(40, bold=True), accent) + 30
    when = f"{day.month}월 {day.day}일 ({WEEKDAYS[day.weekday()]}) · {mood.label}"
    y = center(draw, y, when, font(36), MUTED) + 50

    with Image.open(ASSETS / "characters" / f"{mood.side}.png") as ch:
        ch = ch.convert("RGBA")
        ch.thumbnail((380, 380), Image.LANCZOS)
        img.paste(ch, ((WIDTH - ch.width) // 2, y), ch)
        y += ch.height + 60

    # 본문: 길면 글자를 줄인다
    for size in (54, 50, 46, 42):
        body = font(size)
        lines = wrap(draw, verse.text, body, WIDTH - 200)
        if len(lines) <= 8:
            break
    for line in lines:
        y = center(draw, y, line, body, BROWN) + int(size * 0.55)
    y += 30
    y = center(draw, y, f"{verse.ref} ({TRANSLATION})", font(38, bold=True), accent) + 70

    medi = font(38)
    for line in wrap(draw, verse.meditation, medi, WIDTH - 240):
        y = center(draw, y, line, medi, MUTED) + 20

    # 함께 건네는 한 잔
    box_top = HEIGHT - 330
    draw.rounded_rectangle([140, box_top, WIDTH - 140, box_top + 130], radius=40, fill=CREAM)
    center(
        draw,
        box_top + 42,
        f"{SIDE_NAMES[mood.side]}가 건네는 한 잔 · {mood.drink}",
        font(38, bold=True),
        BROWN,
    )

    center(draw, HEIGHT - 120, "SENSO · Sen & So와 함께하는 하루 한 잔", font(34), MUTED)

    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
