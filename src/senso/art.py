"""앱이 직접 그리는 그림: 배경 무늬, 화면 맨 위 배너, 상품 그림, 소식 카드 그림.

외부 사진을 쓰지 않으므로 저작권·다운로드 걱정이 없다. 모두 Pillow로 그려 PNG 바이트로 돌려주고,
같은 그림은 한 번만 그린다(cache).
"""

import io
import math
import random
from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ASSETS = Path(__file__).resolve().parents[1] / "assets"

IVORY = (250, 246, 238)
CREAM = (241, 232, 216)
CARAMEL = (214, 176, 128)
BROWN = (74, 44, 29)
BEAN = (122, 78, 48)
LEAF = (110, 140, 84)
SAGE = (214, 228, 200)

# 배너 색 (위·아래 그라데이션)과 캐릭터
BANNERS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int], str]] = {
    "home": ((246, 232, 210), (226, 196, 158), "duo"),
    "coffee": ((240, 224, 204), (206, 166, 122), "sen"),
    "tea": ((236, 242, 226), (196, 214, 176), "so"),
    "shop": ((248, 230, 214), (222, 178, 150), "duo"),
    "bookmark": ((242, 234, 222), (214, 196, 170), "so"),
}


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _gradient(size: tuple[int, int], top, bottom, diagonal: bool = True) -> Image.Image:
    """위→아래(살짝 대각선) 그라데이션. 작은 그림을 만들어 늘려서 빠르게 그린다."""
    w, h = size
    small = Image.new("RGB", (16, 16))
    px = small.load()
    for y in range(16):
        for x in range(16):
            t = (y / 15 * 0.7 + x / 15 * 0.3) if diagonal else y / 15
            px[x, y] = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom, strict=True))
    return small.resize((w, h), Image.BILINEAR)


def _bean(size: int, color=BEAN, alpha: int = 255) -> Image.Image:
    """커피콩 하나 (세로로 긴 타원 + 가운데 홈)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w, h = size * 0.62, size * 0.86
    box = [(size - w) / 2, (size - h) / 2, (size + w) / 2, (size + h) / 2]
    d.ellipse(box, fill=(*color, alpha))
    cx = size / 2
    d.arc(
        [cx - w * 0.28, box[1] + 2, cx + w * 0.28, box[3] - 2],
        250,
        110,
        fill=(*IVORY, alpha),
        width=max(2, size // 14),
    )
    return img


def _leaf(size: int, color=LEAF, alpha: int = 255) -> Image.Image:
    """찻잎 하나 (뾰족한 잎 + 잎맥)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = size / 2
    pts = []
    for i in range(41):
        t = i / 40
        y = size * 0.08 + t * size * 0.84
        half = math.sin(math.pi * t) ** 0.8 * size * 0.26
        pts.append((cx - half, y))
    pts += [(2 * cx - x, y) for x, y in reversed(pts)]
    d.polygon(pts, fill=(*color, alpha))
    d.line([(cx, size * 0.12), (cx, size * 0.9)], fill=(*IVORY, alpha), width=max(1, size // 22))
    return img


def _scatter(
    canvas: Image.Image, count: int, sizes: tuple[int, int], alpha: int, seed: int, area=None
):
    rnd = random.Random(seed)
    w, h = canvas.size
    x0, y0, x1, y1 = area or (0, 0, w, h)
    for i in range(count):
        s = rnd.randint(*sizes)
        piece = (_bean if i % 2 == 0 else _leaf)(s, alpha=alpha)
        piece = piece.rotate(rnd.uniform(0, 360), expand=True, resample=Image.BICUBIC)
        canvas.alpha_composite(
            piece, (rnd.randint(x0 - s // 2, x1 - s // 2), rnd.randint(y0 - s // 2, y1 - s // 2))
        )


@cache
def pattern_tile() -> bytes:
    """화면 배경에 깔리는 옅은 무늬 (반복해서 깐다)."""
    tile = Image.new("RGBA", (260, 260), (*IVORY, 255))
    _scatter(tile, 6, (26, 40), alpha=28, seed=7, area=(20, 20, 240, 240))
    return _png(tile)


def _character(name: str, height: int) -> Image.Image | None:
    path = ASSETS / "characters" / f"{name}.png"
    if not path.is_file():
        return None
    with Image.open(path) as ch:
        ch = ch.convert("RGBA")
        ratio = height / ch.height
        return ch.resize((max(1, round(ch.width * ratio)), height), Image.LANCZOS)


@cache
def banner(key: str, width: int = 1200, height: int = 300) -> bytes:
    """화면 맨 위 배너. 왼쪽은 글자를 올릴 자리로 비워 두고 오른쪽에 무늬와 캐릭터."""
    top, bottom, who = BANNERS.get(key, BANNERS["home"])
    img = _gradient((width, height), top, bottom).convert("RGBA")
    # 오른쪽에 커피콩·찻잎을 흩뿌린다
    _scatter(
        img, 18, (34, 70), alpha=70, seed=hash(key) % 1000, area=(width // 2, 0, width, height)
    )
    # 둥근 빛
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        [width * 0.62, -height * 0.4, width * 1.1, height * 1.2], fill=(255, 255, 255, 70)
    )
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(30)))
    ch = _character(who, int(height * 0.92))
    if ch is not None:
        img.alpha_composite(ch, (width - ch.width - int(width * 0.04), height - ch.height))
    # 글자가 잘 읽히도록 왼쪽을 살짝 밝게
    veil = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    vd = ImageDraw.Draw(veil)
    for x in range(width // 2):
        a = int(120 * (1 - x / (width / 2)))
        vd.line([(x, 0), (x, height)], fill=(*IVORY, a))
    img.alpha_composite(veil)
    return _png(img.convert("RGB"))


def _rounded(size: tuple[int, int], top, bottom) -> Image.Image:
    img = _gradient(size, top, bottom).convert("RGBA")
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=48, fill=255)
    img.putalpha(mask)
    return img


@cache
def product_art(key: str, size: int = 480) -> bytes:
    """쇼핑 상품 그림 (단순한 일러스트)."""
    s = size
    palette = {
        "tasting_box": ((246, 230, 206), (220, 184, 140)),
        "plus": ((236, 226, 246), (196, 178, 222)),
        "premium": ((246, 226, 206), (196, 150, 104)),
        "gift_set": ((248, 222, 214), (220, 160, 150)),
        "goods": ((228, 238, 222), (186, 206, 170)),
    }
    top, bottom = palette.get(key, palette["tasting_box"])
    img = _rounded((s, s), top, bottom)
    d = ImageDraw.Draw(img)
    _scatter(img, 8, (s // 14, s // 9), alpha=60, seed=len(key) * 31, area=(0, 0, s, s))
    c = s / 2
    if key in ("tasting_box", "premium"):
        # 상자 + 리본 + 작은 봉투 두 개
        d.rounded_rectangle(
            [c - s * 0.28, c - s * 0.12, c + s * 0.28, c + s * 0.26],
            radius=18,
            fill=(196, 150, 104),
        )
        d.polygon(
            [
                (c - s * 0.31, c - s * 0.12),
                (c + s * 0.31, c - s * 0.12),
                (c + s * 0.26, c - s * 0.2),
                (c - s * 0.26, c - s * 0.2),
            ],
            fill=(214, 172, 126),
        )
        d.rectangle([c - s * 0.03, c - s * 0.2, c + s * 0.03, c + s * 0.26], fill=(184, 74, 64))
        for dx in (-0.16, 0.16):
            d.rounded_rectangle(
                [c + s * dx - s * 0.07, c - s * 0.32, c + s * dx + s * 0.07, c - s * 0.14],
                radius=8,
                fill=IVORY,
                outline=BROWN,
                width=3,
            )
        if key == "premium":
            d.ellipse(
                [c + s * 0.18, c + s * 0.14, c + s * 0.34, c + s * 0.3],
                fill=(230, 190, 80),
                outline=BROWN,
                width=3,
            )
    elif key == "plus":
        # 멤버십 카드
        d.rounded_rectangle(
            [c - s * 0.3, c - s * 0.18, c + s * 0.3, c + s * 0.18], radius=24, fill=(120, 92, 170)
        )
        d.rounded_rectangle(
            [c - s * 0.24, c - s * 0.08, c - s * 0.1, c + s * 0.02], radius=6, fill=(230, 200, 120)
        )
        d.line([(c - s * 0.24, c + s * 0.1), (c + s * 0.2, c + s * 0.1)], fill=IVORY, width=8)
    elif key == "gift_set":
        d.rounded_rectangle(
            [c - s * 0.26, c - s * 0.1, c + s * 0.26, c + s * 0.28], radius=16, fill=(200, 96, 86)
        )
        d.rectangle([c - s * 0.3, c - s * 0.18, c + s * 0.3, c - s * 0.08], fill=(214, 112, 100))
        d.rectangle(
            [c - s * 0.035, c - s * 0.18, c + s * 0.035, c + s * 0.28], fill=(240, 210, 120)
        )
        d.ellipse([c - s * 0.13, c - s * 0.3, c, c - s * 0.17], outline=(240, 210, 120), width=10)
        d.ellipse([c, c - s * 0.3, c + s * 0.13, c - s * 0.17], outline=(240, 210, 120), width=10)
    else:
        # 굿즈: 머그컵
        d.rounded_rectangle(
            [c - s * 0.2, c - s * 0.2, c + s * 0.14, c + s * 0.24],
            radius=22,
            fill=IVORY,
            outline=BROWN,
            width=5,
        )
        d.arc([c + s * 0.06, c - s * 0.1, c + s * 0.3, c + s * 0.14], 270, 90, fill=BROWN, width=12)
        ch = _character("duo", int(s * 0.22))
        if ch is not None:
            img.alpha_composite(ch, (int(c - s * 0.03 - ch.width / 2), int(c - s * 0.1)))
    return _png(img)


@cache
def content_art(platform: str, size: tuple[int, int] = (640, 360)) -> bytes:
    """SENSO 소식 카드 그림. 상표 로고가 아닌 단순한 기호만 그린다."""
    w, h = size
    if platform == "youtube":
        img = _gradient(size, (60, 40, 32), (150, 70, 60)).convert("RGBA")
        _scatter(img, 10, (40, 70), alpha=40, seed=11)
        d = ImageDraw.Draw(img)
        # 영상: 둥근 재생 단추
        d.ellipse([w / 2 - 56, h / 2 - 56, w / 2 + 56, h / 2 + 56], fill=(255, 255, 255, 220))
        d.polygon(
            [(w / 2 - 16, h / 2 - 28), (w / 2 - 16, h / 2 + 28), (w / 2 + 30, h / 2)],
            fill=(150, 70, 60),
        )
    elif platform == "instagram":
        img = _gradient(size, (248, 214, 160), (176, 104, 128)).convert("RGBA")
        _scatter(img, 10, (40, 70), alpha=40, seed=13)
        d = ImageDraw.Draw(img)
        # 사진: 사진기 모양
        d.rounded_rectangle(
            [w / 2 - 70, h / 2 - 40, w / 2 + 70, h / 2 + 50], radius=14, fill=(255, 255, 255, 220)
        )
        d.rectangle([w / 2 - 26, h / 2 - 54, w / 2 + 10, h / 2 - 38], fill=(255, 255, 255, 220))
        d.ellipse([w / 2 - 28, h / 2 - 22, w / 2 + 28, h / 2 + 34], fill=(176, 104, 128))
        d.ellipse([w / 2 - 16, h / 2 - 10, w / 2 + 16, h / 2 + 22], fill=(248, 214, 160))
    else:
        img = _gradient(size, CREAM, CARAMEL).convert("RGBA")
        _scatter(img, 12, (40, 70), alpha=60, seed=17)
    return _png(img.convert("RGB"))
