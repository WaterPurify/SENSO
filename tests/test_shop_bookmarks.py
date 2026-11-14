"""쇼핑·책갈피·SENSO 소식 링크·그림."""

import io
import json

import pytest
from PIL import Image

from senso import app, art
from senso.content import load_links, safe_url
from senso.db.bookmark_repo import BookmarkRepository
from senso.db.database import open_database
from senso.shop import PRODUCTS, PRODUCTS_BY_KEY


@pytest.fixture
def marks(tmp_path):
    conn = open_database(tmp_path / "t.db")
    yield BookmarkRepository(conn)
    conn.close()


# ---- 책갈피 ------------------------------------------------------------------------


def test_toggle_and_list(marks):
    assert marks.list() == []
    assert marks.toggle("brew", 3, "예가체프 · 11월 14일") is True
    assert marks.toggle("product", "plus", "Plus 멤버십") is True
    assert marks.has("brew", "3") and marks.has("brew", 3)
    assert [m.kind for m in marks.list()] == ["product", "brew"]  # 최신순
    assert [m.ref for m in marks.list("brew")] == ["3"]
    assert marks.toggle("brew", 3, "다시 누름") is False  # 다시 누르면 빠짐
    assert not marks.has("brew", 3)
    marks.remove("product", "plus")
    assert marks.list() == []


def test_unknown_kind_rejected(marks):
    with pytest.raises(ValueError):
        marks.toggle("password", "x", "y")


def test_long_title_is_cut(marks):
    marks.toggle("content", "k", "가" * 200)
    assert len(marks.list()[0].title) == 80


# ---- 쇼핑 -------------------------------------------------------------------------


def test_products_from_business_plan():
    assert [p.key for p in PRODUCTS][:3] == ["tasting_box", "plus", "premium"]
    assert PRODUCTS_BY_KEY["tasting_box"].price == "12,900원"
    assert PRODUCTS_BY_KEY["plus"].price == "월 7,900원"
    assert PRODUCTS_BY_KEY["premium"].price == "월 29,000원"
    assert all(p.points for p in PRODUCTS)


# ---- SENSO 소식 링크 -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("platform", "url", "ok"),
    [
        ("youtube", "https://www.youtube.com/@senso", True),
        ("youtube", "https://youtu.be/abc123", True),
        ("instagram", "https://www.instagram.com/senso/", True),
        ("youtube", "http://www.youtube.com/@senso", False),  # https만
        ("youtube", "https://youtube.com.evil.example/", False),  # 비슷한 가짜 도메인
        ("youtube", "https://user:pw@youtube.com/", False),
        ("instagram", "https://www.youtube.com/@senso", False),  # 플랫폼과 도메인 불일치
        ("youtube", "javascript:alert(1)", False),
        ("youtube", "", False),
    ],
)
def test_safe_url(platform, url, ok):
    assert (safe_url(platform, url) is not None) is ok


def test_load_links_marks_empty_as_coming_soon(tmp_path):
    path = tmp_path / "links.json"
    path.write_text(
        json.dumps(
            {
                "items": [
                    {"key": "a", "platform": "youtube", "title": "영상", "url": ""},
                    {"key": "b", "platform": "instagram", "url": "https://instagram.com/x"},
                    {"key": "c", "platform": "tiktok", "url": "https://tiktok.com/x"},
                    {"key": "d", "platform": "youtube", "url": "https://evil.example/"},
                ]
            }
        ),
        encoding="utf-8",
    )
    links = load_links(path)
    assert [x.key for x in links] == ["a", "b", "d"]  # 모르는 플랫폼은 뺀다
    assert links[0].url is None  # 준비 중
    assert links[1].url == "https://instagram.com/x"
    assert links[2].url is None  # 허용하지 않은 도메인은 열지 않음


def test_bundled_links_file_is_valid():
    links = load_links()
    assert links and all(x.platform in ("youtube", "instagram") for x in links)


def test_broken_links_file(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{ not json", encoding="utf-8")
    assert load_links(path) == []


# ---- 그림 --------------------------------------------------------------------------


@pytest.mark.parametrize("key", list(art.BANNERS))
def test_banner_png(key):
    with Image.open(io.BytesIO(art.banner(key))) as img:
        assert img.format == "PNG" and img.size == (1200, 300)


@pytest.mark.parametrize("key", [p.key for p in PRODUCTS])
def test_product_art_png(key):
    with Image.open(io.BytesIO(art.product_art(key))) as img:
        assert img.size == (480, 480)


def test_other_art():
    for platform in ("youtube", "instagram", "other"):
        with Image.open(io.BytesIO(art.content_art(platform))) as img:
            assert img.size == (640, 360)
    with Image.open(io.BytesIO(art.pattern_tile())) as img:
        assert img.size == (260, 260)


# ---- 하단 탭 ------------------------------------------------------------------------


def test_six_tabs_in_requested_order():
    assert [label for _, _, label in app.TABS] == ["기록", "커피", "차", "나", "쇼핑", "책갈피"]
    assert (app.TAB_ME, app.TAB_SHOP, app.TAB_BOOKMARK) == (3, 4, 5)
