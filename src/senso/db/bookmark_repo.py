"""책갈피 저장소."""

# 메서드 이름 list가 내장 list를 가리므로 타입 표기를 문자열로 미룬다
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

KINDS = ("brew", "bean", "product", "content")
TITLE_MAX = 80


@dataclass(frozen=True)
class Bookmark:
    id: int
    kind: str
    ref: str
    title: str


class BookmarkRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def has(self, kind: str, ref: str | int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM bookmarks WHERE kind = ? AND ref = ?", (kind, str(ref))
        ).fetchone()
        return row is not None

    def toggle(self, kind: str, ref: str | int, title: str) -> bool:
        """있으면 빼고, 없으면 넣는다. 넣었으면 True."""
        if kind not in KINDS:
            raise ValueError(f"알 수 없는 책갈피 종류: {kind}")
        ref = str(ref)
        with self.conn:
            cur = self.conn.execute("DELETE FROM bookmarks WHERE kind = ? AND ref = ?", (kind, ref))
            if cur.rowcount:
                return False
            self.conn.execute(
                "INSERT INTO bookmarks (kind, ref, title) VALUES (?, ?, ?)",
                (kind, ref, (title or "이름 없음").strip()[:TITLE_MAX]),
            )
        return True

    def remove(self, kind: str, ref: str | int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM bookmarks WHERE kind = ? AND ref = ?", (kind, str(ref)))

    def list(self, kind: str | None = None) -> list[Bookmark]:
        sql = "SELECT id, kind, ref, title FROM bookmarks"
        args: tuple = ()
        if kind:
            sql += " WHERE kind = ?"
            args = (kind,)
        rows = self.conn.execute(sql + " ORDER BY created_at DESC, id DESC", args).fetchall()
        return [Bookmark(r["id"], r["kind"], r["ref"], r["title"]) for r in rows]
