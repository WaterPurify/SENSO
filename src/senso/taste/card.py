"""취향 유형 결과 카드 이미지 (1080×1920, 인스타그램 스토리 크기)."""

import io
from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from senso.taste.quiz import FLAVOR_NAMES, FLAVORS, QuizResult

ASSETS = Path(__file__).resolve().parents[2] / "assets"
WIDTH, HEIGHT = 1080, 1920

IVORY = (250, 246, 238)
CREAM = (241, 232, 216)
BROWN = (74, 44, 29)
MUTED = (107, 91, 78)
ACCENT = {"sen": (139, 94, 60), "so": (94, 122, 74)}


@cache
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "Pretendard-Bold.otf" if bold else "Pretendard-Regular.otf"
    return ImageFont.truetype(str(ASSETS / "fonts" / name), size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    """한국어는 글자 단위로 줄을 나눈다 (띄어쓰기 기준을 먼저 시도)."""
    lines: list[str] = []
    current = ""
    for word in text.split(" "):
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
            continue
        if current:
            lines.append(current)
        current = ""
        for ch in word:
            if draw.textlength(current + ch, font=font) > max_width and current:
                lines.append(current)
                current = ch
            else:
                current += ch
    if current:
        lines.append(current)
    return lines


def _center(draw, y: int, text: str, font, fill) -> int:
    w = draw.textlength(text, font=font)
    draw.text(((WIDTH - w) / 2, y), text, font=font, fill=fill)
    bbox = font.getbbox(text)
    return y + (bbox[3] - bbox[1])


def render_card(result: QuizResult) -> bytes:
    t = result.type
    accent = ACCENT[t.side]
    img = Image.new("RGB", (WIDTH, HEIGHT), IVORY)
    draw = ImageDraw.Draw(img)

    # 위쪽 띠와 제목
    draw.rectangle([0, 0, WIDTH, 24], fill=accent)
    y = _center(draw, 110, "SENSO 취향 유형 테스트", _font(40), MUTED) + 50
    y = _center(draw, y, "나는", _font(56), MUTED) + 30
    y = _center(draw, y, t.name, _font(112, bold=True), BROWN) + 60

    # 캐릭터
    with Image.open(ASSETS / "characters" / f"{t.side}.png") as ch:
        ch = ch.convert("RGBA")
        ch.thumbnail((560, 560), Image.LANCZOS)
        img.paste(ch, ((WIDTH - ch.width) // 2, y), ch)
        y += ch.height + 50

    # 설명
    body = _font(44)
    for line in _wrap(draw, t.summary, body, WIDTH - 200):
        y = _center(draw, y, line, body, BROWN) + 22
    y += 40

    # 맛 성향 막대
    total = max(1, max(result.flavor_scores.values()))
    bar_left, bar_right = 300, WIDTH - 140
    label_font = _font(40, bold=True)
    for f in FLAVORS:
        score = result.flavor_scores.get(f, 0)
        draw.text((140, y), FLAVOR_NAMES[f], font=label_font, fill=BROWN)
        draw.rounded_rectangle([bar_left, y + 8, bar_right, y + 44], radius=18, fill=CREAM)
        if score:
            right = bar_left + (bar_right - bar_left) * score / total
            draw.rounded_rectangle([bar_left, y + 8, right, y + 44], radius=18, fill=accent)
        y += 74
    y += 30

    # 추천
    pick_font = _font(40)
    y = _center(draw, y, "이런 걸 마셔 보세요", _font(40, bold=True), accent) + 24
    _center(draw, y, " · ".join(t.picks), pick_font, BROWN)

    # 아래쪽
    _center(draw, HEIGHT - 120, "Sen & So와 함께 찾는 나만의 한 잔", _font(36), MUTED)

    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
