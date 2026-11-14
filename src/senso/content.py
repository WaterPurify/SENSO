"""SENSO 소식 (유튜브·인스타그램 링크) 불러오기.

주소는 content_links.json에서 읽는다. 아무 주소나 열리지 않도록 https와 허용한 도메인만 통과시킨다.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

LINKS_FILE = Path(__file__).with_name("content_links.json")
ALLOWED_HOSTS = {
    "youtube": ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"),
    "instagram": ("instagram.com", "www.instagram.com"),
}
PLATFORM_NAMES = {"youtube": "YouTube", "instagram": "Instagram"}


@dataclass(frozen=True)
class ContentLink:
    key: str
    platform: str
    title: str
    description: str
    url: str | None  # None = 준비 중


def safe_url(platform: str, url: str | None) -> str | None:
    """https이고 그 플랫폼의 도메인일 때만 주소를 돌려준다."""
    if not url:
        return None
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in ALLOWED_HOSTS.get(platform, ()):
        return None
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        return None
    return parsed.geturl()


def load_links(path: Path = LINKS_FILE) -> list[ContentLink]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    links: list[ContentLink] = []
    for item in data.get("items", [])[:12]:
        if not isinstance(item, dict):
            continue
        platform = str(item.get("platform", ""))
        if platform not in ALLOWED_HOSTS:
            continue
        links.append(
            ContentLink(
                key=str(item.get("key", ""))[:40] or platform,
                platform=platform,
                title=str(item.get("title", ""))[:40] or PLATFORM_NAMES[platform],
                description=str(item.get("description", ""))[:80],
                url=safe_url(platform, item.get("url")),
            )
        )
    return links
