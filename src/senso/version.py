"""화면에 보여 줄 버전과 빌드 정보.

버전 번호(__version__)만으로는 웹에 새 코드가 올라갔는지 알 수 없어서, 빌드 표시를 함께 보여 준다.
  1. 환경 변수 SENSO_BUILD (운영용 이미지를 만들 때 넣는다)
  2. git 커밋 (개발용: 저장소 폴더가 연결돼 있을 때)
  3. 소스 코드 지문 (위 둘이 없을 때. 코드가 바뀌면 값이 바뀐다)
"""

import hashlib
import os
import subprocess
from functools import cache
from pathlib import Path

from senso import __version__

PACKAGE = Path(__file__).resolve().parent
REPO = PACKAGE.parents[1]


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-c", f"safe.directory={REPO.as_posix()}", "-C", str(REPO), *args],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def source_fingerprint() -> str:
    """패키지 안 .py·.sql 파일 내용으로 만든 짧은 지문."""
    digest = hashlib.sha256()
    for path in sorted(PACKAGE.rglob("*")):
        if path.suffix in (".py", ".sql") and "__pycache__" not in path.parts:
            digest.update(path.relative_to(PACKAGE).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:7]


@cache
def build_info() -> str:
    env = os.getenv("SENSO_BUILD", "").strip()
    if env and env != "unknown":
        return env[:40]
    if (REPO / ".git").exists():
        commit = _git("rev-parse", "--short=7", "HEAD")
        if commit:
            date = _git("log", "-1", "--format=%cd", "--date=short") or ""
            dirty = " +수정중" if _git("status", "--porcelain", "--untracked-files=no") else ""
            return f"{commit} · {date}{dirty}".strip(" ·")
    return f"코드 {source_fingerprint()}"


def version_label() -> str:
    """예: 'v0.8.0 · 빌드 8b362f5 · 2026-11-14'"""
    return f"v{__version__} · 빌드 {build_info()}"
