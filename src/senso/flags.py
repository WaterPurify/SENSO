"""나라 국기를 PNG로 그린다 (Pillow).

국기 이모지는 웹에서 이모지 글꼴을 인터넷에서 받아 와야 보인다. 앱은 인터넷 없이도
돌아가야 하므로(웹 서버는 no_cdn) 국기를 직접 그린다. 작게 보이는 아이콘이라
문장(紋章)·글자 같은 세부는 단순하게 줄였다.
"""

import io
import math
from collections.abc import Callable
from functools import cache

from PIL import Image, ImageDraw

W, H = 240, 160  # 3:2로 크게 그린 뒤 줄인다
OUT = (72, 48)

Draw = ImageDraw.ImageDraw
Color = str


def _hstripes(d: Draw, colors: list[Color], weights: list[float] | None = None) -> None:
    weights = weights or [1] * len(colors)
    total, y = sum(weights), 0.0
    for c, w in zip(colors, weights, strict=True):
        h = H * w / total
        d.rectangle([0, round(y), W, round(y + h)], fill=c)
        y += h


def _vstripes(d: Draw, colors: list[Color]) -> None:
    w = W / len(colors)
    for i, c in enumerate(colors):
        d.rectangle([round(i * w), 0, round((i + 1) * w), H], fill=c)


def _star(d: Draw, cx: float, cy: float, r: float, fill: Color, points: int = 5) -> None:
    inner = r * (0.382 if points == 5 else 0.6)
    pts = []
    for i in range(points * 2):
        rr = r if i % 2 == 0 else inner
        a = -math.pi / 2 + i * math.pi / points
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)


def _circle(d: Draw, cx: float, cy: float, r: float, fill: Color | None, outline=None, width=1):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=outline, width=width)


# ---- 나라별 --------------------------------------------------------------------------


def _et(d: Draw) -> None:
    _hstripes(d, ["#078930", "#FCDD09", "#DA121A"])
    _circle(d, 120, 80, 36, "#0F47AF")
    _star(d, 120, 82, 24, "#FCDD09")
    _star(d, 120, 82, 13, "#0F47AF")


def _ke(d: Draw) -> None:
    _hstripes(d, ["#000000", "#FFFFFF", "#BB0000", "#FFFFFF", "#006600"], [6, 1, 6, 1, 6])
    d.ellipse([96, 20, 144, 140], fill="#000000")
    d.ellipse([108, 20, 132, 140], fill="#BB0000")


def _rw(d: Draw) -> None:
    _hstripes(d, ["#00A1DE", "#FAD201", "#20603D"], [2, 1, 1])
    _star(d, 196, 36, 22, "#FAD201", points=12)
    _circle(d, 196, 36, 10, "#FAD201", outline="#00A1DE", width=2)


def _bi(d: Draw) -> None:
    d.polygon([(0, 0), (W, 0), (120, 80)], fill="#CE1126")
    d.polygon([(0, H), (W, H), (120, 80)], fill="#CE1126")
    d.polygon([(0, 0), (0, H), (120, 80)], fill="#1EB53A")
    d.polygon([(W, 0), (W, H), (120, 80)], fill="#1EB53A")
    d.line([(0, 0), (W, H)], fill="#FFFFFF", width=22)
    d.line([(0, H), (W, 0)], fill="#FFFFFF", width=22)
    _circle(d, 120, 80, 42, "#FFFFFF")
    for x, y in [(120, 64), (104, 92), (136, 92)]:
        _star(d, x, y, 11, "#CE1126", points=6)


def _tz(d: Draw) -> None:
    d.rectangle([0, 0, W, H], fill="#00A3DD")
    d.polygon([(0, 0), (W, 0), (0, H)], fill="#1EB53A")
    d.line([(0, H), (W, 0)], fill="#FCD116", width=56)
    d.line([(0, H), (W, 0)], fill="#000000", width=38)


def _ug(d: Draw) -> None:
    _hstripes(d, ["#000000", "#FCDC04", "#D90000"] * 2)
    _circle(d, 120, 80, 32, "#FFFFFF")


def _mw(d: Draw) -> None:
    _hstripes(d, ["#000000", "#CE1126", "#339E35"])
    d.pieslice([90, 22, 150, 82], 180, 360, fill="#CE1126")


def _cd(d: Draw) -> None:
    d.rectangle([0, 0, W, H], fill="#007FFF")
    d.line([(0, H), (W, 0)], fill="#F7D618", width=46)
    d.line([(0, H), (W, 0)], fill="#CE1021", width=32)
    _star(d, 44, 40, 28, "#F7D618")


def _ye(d: Draw) -> None:
    _hstripes(d, ["#CE1126", "#FFFFFF", "#000000"])


def _co(d: Draw) -> None:
    _hstripes(d, ["#FCD116", "#003893", "#CE1126"], [2, 1, 1])


def _br(d: Draw) -> None:
    d.rectangle([0, 0, W, H], fill="#009C3B")
    d.polygon([(20, 80), (120, 16), (220, 80), (120, 144)], fill="#FFDF00")
    _circle(d, 120, 80, 36, "#002776")
    d.arc([76, 52, 172, 140], 205, 320, fill="#FFFFFF", width=6)


def _gt(d: Draw) -> None:
    _vstripes(d, ["#4997D0", "#FFFFFF", "#4997D0"])
    _circle(d, 120, 80, 18, None, outline="#6C8E3C", width=5)


def _cr(d: Draw) -> None:
    _hstripes(d, ["#002B7F", "#FFFFFF", "#CE1126", "#FFFFFF", "#002B7F"], [1, 1, 2, 1, 1])


def _pa(d: Draw) -> None:
    d.rectangle([0, 0, W, H], fill="#FFFFFF")
    d.rectangle([120, 0, W, 80], fill="#D21034")
    d.rectangle([0, 80, 120, H], fill="#005293")
    _star(d, 60, 40, 20, "#005293")
    _star(d, 180, 120, 20, "#D21034")


def _hn(d: Draw) -> None:
    _hstripes(d, ["#0073CF", "#FFFFFF", "#0073CF"])
    for x, y in [(120, 80), (96, 68), (144, 68), (96, 92), (144, 92)]:
        _star(d, x, y, 8, "#0073CF")


def _sv(d: Draw) -> None:
    _hstripes(d, ["#0F47AF", "#FFFFFF", "#0F47AF"])
    _circle(d, 120, 80, 16, None, outline="#C8A400", width=5)


def _ni(d: Draw) -> None:
    _hstripes(d, ["#0067C6", "#FFFFFF", "#0067C6"])
    d.polygon([(120, 62), (100, 96), (140, 96)], outline="#0067C6", width=5)


def _mx(d: Draw) -> None:
    _vstripes(d, ["#006847", "#FFFFFF", "#CE1126"])
    _circle(d, 120, 80, 18, "#8C6239")


def _pe(d: Draw) -> None:
    _vstripes(d, ["#D91023", "#FFFFFF", "#D91023"])


def _bo(d: Draw) -> None:
    _hstripes(d, ["#D52B1E", "#F9E300", "#007934"])


def _ec(d: Draw) -> None:
    _hstripes(d, ["#FFDD00", "#034EA2", "#ED1C24"], [2, 1, 1])
    _circle(d, 120, 80, 18, "#8C6239")


def _jm(d: Draw) -> None:
    d.polygon([(0, 0), (W, 0), (120, 80)], fill="#009B3A")
    d.polygon([(0, H), (W, H), (120, 80)], fill="#009B3A")
    d.polygon([(0, 0), (0, H), (120, 80)], fill="#000000")
    d.polygon([(W, 0), (W, H), (120, 80)], fill="#000000")
    d.line([(0, 0), (W, H)], fill="#FED100", width=26)
    d.line([(0, H), (W, 0)], fill="#FED100", width=26)


def _us(d: Draw) -> None:
    _hstripes(d, ["#B22234", "#FFFFFF"] * 6 + ["#B22234"])
    cw, ch = W * 0.4, H * 7 / 13
    d.rectangle([0, 0, cw, ch], fill="#3C3B6E")
    for row in range(4):
        for col in range(5):
            _circle(d, 10 + col * 19, 11 + row * 19, 3.5, "#FFFFFF")


def _id(d: Draw) -> None:
    _hstripes(d, ["#FF0000", "#FFFFFF"])


def _pg(d: Draw) -> None:
    d.polygon([(0, 0), (W, 0), (W, H)], fill="#CE1126")
    d.polygon([(0, 0), (0, H), (W, H)], fill="#000000")
    _circle(d, 172, 48, 18, "#FCD116")
    for x, y in [(44, 96), (64, 120), (44, 136), (28, 116)]:
        _star(d, x, y, 7, "#FFFFFF")


def _vn(d: Draw) -> None:
    d.rectangle([0, 0, W, H], fill="#DA251D")
    _star(d, 120, 84, 50, "#FFFF00")


def _th(d: Draw) -> None:
    _hstripes(d, ["#A51931", "#F4F5F8", "#2D2A4A", "#F4F5F8", "#A51931"], [1, 1, 2, 1, 1])


def _la(d: Draw) -> None:
    _hstripes(d, ["#CE1126", "#002868", "#CE1126"], [1, 2, 1])
    _circle(d, 120, 80, 32, "#FFFFFF")


def _mm(d: Draw) -> None:
    _hstripes(d, ["#FECB00", "#34B233", "#EA2839"])
    _star(d, 120, 88, 64, "#FFFFFF")


def _in(d: Draw) -> None:
    _hstripes(d, ["#FF9933", "#FFFFFF", "#138808"])
    _circle(d, 120, 80, 21, None, outline="#000080", width=4)
    _circle(d, 120, 80, 5, "#000080")


def _lk(d: Draw) -> None:
    d.rectangle([0, 0, W, H], fill="#FFB700")
    d.rectangle([10, 10, 50, H - 10], fill="#005F56")
    d.rectangle([50, 10, 90, H - 10], fill="#FF5B00")
    d.rectangle([100, 10, W - 10, H - 10], fill="#8D153A")
    _circle(d, 165, 80, 22, None, outline="#FFB700", width=5)


def _np(d: Draw) -> None:
    # 직사각형이 아닌 두 삼각기. 투명 배경 위에 가운데 정렬
    x0, w = 64, 112

    def shape(inset: float) -> list[tuple[float, float]]:
        return [
            (x0 + inset, inset),
            (x0 + w - inset * 2.2, H * 0.5 - inset * 0.6),
            (x0 + w * 0.32 + inset, H * 0.5 - inset * 0.6),
            (x0 + w - inset * 2.2, H - inset),
            (x0 + inset, H - inset),
        ]

    d.polygon(shape(0), fill="#003893")
    d.polygon(shape(7), fill="#DC143C")
    _circle(d, x0 + 34, 46, 12, "#FFFFFF")
    _star(d, x0 + 34, 116, 15, "#FFFFFF", points=12)


def _cn(d: Draw) -> None:
    d.rectangle([0, 0, W, H], fill="#DE2910")
    _star(d, 40, 40, 24, "#FFDE00")
    for x, y in [(80, 16), (96, 32), (96, 56), (80, 72)]:
        _star(d, x, y, 8, "#FFDE00")


def _tw(d: Draw) -> None:
    d.rectangle([0, 0, W, H], fill="#FE0000")
    d.rectangle([0, 0, 120, 80], fill="#000095")
    _star(d, 60, 40, 28, "#FFFFFF", points=12)
    _circle(d, 60, 40, 15, "#000095")
    _circle(d, 60, 40, 12, "#FFFFFF")


def _jp(d: Draw) -> None:
    d.rectangle([0, 0, W, H], fill="#FFFFFF")
    _circle(d, 120, 80, 48, "#BC002D")


def _kr(img: Image.Image, d: Draw) -> None:
    d.rectangle([0, 0, W, H], fill="#FFFFFF")
    cx, cy, r = 120, 80, 40
    red, blue = "#CD2E3A", "#0047A0"

    # 태극: 가로로 그린 뒤 건·곤 대각선(왼쪽 위 → 오른쪽 아래) 방향으로 돌린다
    size = r * 2 + 4
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    c = size / 2
    ld.pieslice([c - r, c - r, c + r, c + r], 180, 360, fill=red)
    ld.pieslice([c - r, c - r, c + r, c + r], 0, 180, fill=blue)
    ld.ellipse([c - r, c - r / 2, c, c + r / 2], fill=red)
    ld.ellipse([c, c - r / 2, c + r, c + r / 2], fill=blue)
    angle = math.degrees(math.atan2(2, 3))
    layer = layer.rotate(-angle, resample=Image.BICUBIC)
    img.paste(layer, (round(cx - size / 2), round(cy - size / 2)), layer)

    # 4괘: 건(☰) 왼쪽 위, 감(☵) 오른쪽 위, 리(☲) 왼쪽 아래, 곤(☷) 오른쪽 아래
    trigrams = {
        (-3, -2): (True, True, True),
        (3, -2): (False, True, False),
        (-3, 2): (True, False, True),
        (3, 2): (False, False, False),
    }
    bar, gap, length, start = 7.0, 4.0, 40.0, 62.0
    for (dx, dy), lines in trigrams.items():
        n = math.hypot(dx, dy)
        ux, uy = dx / n, dy / n  # 바깥 방향
        vx, vy = -uy, ux  # 막대 방향
        for i, solid in enumerate(lines):
            dist = start + i * (bar + gap) + bar / 2
            px, py = cx + ux * dist, cy + uy * dist
            pieces = (
                [(0.0, length)]
                if solid
                else [(-(length + 5) / 4, (length - 5) / 2), ((length + 5) / 4, (length - 5) / 2)]
            )
            for off, ln in pieces:
                qx, qy = px + vx * off, py + vy * off
                corners = [
                    (
                        qx + vx * s * ln / 2 + ux * t * bar / 2,
                        qy + vy * s * ln / 2 + uy * t * bar / 2,
                    )
                    for s, t in [(-1, -1), (1, -1), (1, 1), (-1, 1)]
                ]
                d.polygon(corners, fill="#000000")


_PAINTERS: dict[str, Callable[[Draw], None]] = {
    "ET": _et, "KE": _ke, "RW": _rw, "BI": _bi, "TZ": _tz, "UG": _ug, "MW": _mw, "CD": _cd,
    "YE": _ye, "CO": _co, "BR": _br, "GT": _gt, "CR": _cr, "PA": _pa, "HN": _hn, "SV": _sv,
    "NI": _ni, "MX": _mx, "PE": _pe, "BO": _bo, "EC": _ec, "JM": _jm, "US": _us, "ID": _id,
    "PG": _pg, "VN": _vn, "TH": _th, "LA": _la, "MM": _mm, "IN": _in, "LK": _lk, "NP": _np,
    "CN": _cn, "TW": _tw, "JP": _jp,
}  # fmt: skip

# 흰 바탕이 많은 국기는 배경과 구분되게 얇은 테두리를 두른다
_BORDERED = {"JP", "KR", "PA", "ID", "YE", "GT", "PE", "SV", "HN", "NI", "MX", "CR", "TH"}


def supported(code: str) -> bool:
    return code in _PAINTERS or code == "KR"


@cache
def flag_png(code: str) -> bytes | None:
    """국기 PNG (72×48). 그릴 수 없는 나라면 None."""
    if not supported(code):
        return None
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if code == "KR":
        _kr(img, d)
    else:
        _PAINTERS[code](d)
    img = img.resize(OUT, Image.LANCZOS)
    if code in _BORDERED:
        ImageDraw.Draw(img).rectangle([0, 0, OUT[0] - 1, OUT[1] - 1], outline="#D9D2C5")
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
