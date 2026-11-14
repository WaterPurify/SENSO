"""버전 표시: pyproject와 같은 번호, 빌드 표시."""

import tomllib
from pathlib import Path

from senso import __version__, version

ROOT = Path(__file__).resolve().parents[1]


def test_version_matches_pyproject():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == __version__


def test_changelog_mentions_current_version():
    assert f"## {__version__}" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def test_build_from_env(monkeypatch):
    version.build_info.cache_clear()
    monkeypatch.setenv("SENSO_BUILD", "abc1234 · 2026-11-14")
    try:
        assert version.version_label() == f"v{__version__} · 빌드 abc1234 · 2026-11-14"
    finally:
        version.build_info.cache_clear()


def test_fingerprint_without_git(monkeypatch, tmp_path):
    version.build_info.cache_clear()
    monkeypatch.delenv("SENSO_BUILD", raising=False)
    monkeypatch.setattr(version, "REPO", tmp_path)  # .git 없는 곳
    try:
        label = version.build_info()
        assert label == f"코드 {version.source_fingerprint()}"
        assert len(version.source_fingerprint()) == 7
    finally:
        version.build_info.cache_clear()
