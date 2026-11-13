"""원두·차 저장소. 화면 코드는 SQL을 직접 쓰지 않고 이 클래스를 쓴다."""

# 메서드 이름 list가 내장 list를 가리므로 타입 표기를 문자열로 미룬다
from __future__ import annotations

import sqlite3
from datetime import date

from senso.domain.bean import Bean, BeanDraft, BeanKind

_COLUMNS = (
    "id, kind, name, producer, produced_on, roast_level, tea_type, origin, photo_path, is_sample"
)


def _to_bean(row: sqlite3.Row) -> Bean:
    return Bean(
        id=row["id"],
        kind=BeanKind(row["kind"]),
        name=row["name"],
        producer=row["producer"],
        produced_on=date.fromisoformat(row["produced_on"]) if row["produced_on"] else None,
        roast_level=row["roast_level"],
        tea_type=row["tea_type"],
        origin=row["origin"],
        photo_path=row["photo_path"],
        is_sample=bool(row["is_sample"]),
    )


def _values(draft: BeanDraft) -> tuple:
    return (
        draft.name,
        draft.producer,
        draft.produced_on.isoformat() if draft.produced_on else None,
        draft.roast_level,
        draft.tea_type,
        draft.origin,
    )


class BeanRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list(self, kind: BeanKind) -> list[Bean]:
        """삭제하지 않은 항목을 최근 수정한 순서로."""
        rows = self.conn.execute(
            f"SELECT {_COLUMNS} FROM beans WHERE kind = ? AND deleted_at IS NULL "
            "ORDER BY updated_at DESC, id DESC",
            (kind.value,),
        ).fetchall()
        return [_to_bean(r) for r in rows]

    def list_all(self) -> list[Bean]:
        """커피와 차를 함께. 커피 먼저, 각각 최근 수정한 순서로."""
        return self.list(BeanKind.COFFEE) + self.list(BeanKind.TEA)

    def get(self, bean_id: int, include_deleted: bool = False) -> Bean | None:
        sql = f"SELECT {_COLUMNS} FROM beans WHERE id = ?"
        if not include_deleted:
            sql += " AND deleted_at IS NULL"
        row = self.conn.execute(sql, (bean_id,)).fetchone()
        return _to_bean(row) if row else None

    def create(
        self, draft: BeanDraft, photo_path: str | None = None, is_sample: bool = False
    ) -> Bean:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO beans (kind, name, producer, produced_on, roast_level, tea_type, "
                "origin, photo_path, is_sample) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (draft.kind.value, *_values(draft), photo_path, int(is_sample)),
            )
        bean = self.get(cur.lastrowid)
        assert bean is not None
        return bean

    def update(self, bean_id: int, draft: BeanDraft, photo_path: str | None) -> Bean:
        """내용과 사진을 함께 바꾼다. 종류(커피/차)는 바꾸지 않는다."""
        with self.conn:
            cur = self.conn.execute(
                "UPDATE beans SET name = ?, producer = ?, produced_on = ?, roast_level = ?, "
                "tea_type = ?, origin = ?, photo_path = ?, updated_at = datetime('now') "
                "WHERE id = ? AND deleted_at IS NULL",
                (*_values(draft), photo_path, bean_id),
            )
        if cur.rowcount == 0:
            raise LookupError(f"원두를 찾을 수 없어요 (id={bean_id})")
        bean = self.get(bean_id)
        assert bean is not None
        return bean

    def soft_delete_samples(self) -> None:
        """예시 원두·차를 목록에서 숨긴다 (실제 기록에 쓰였을 수 있어 행은 남긴다)."""
        with self.conn:
            self.conn.execute(
                "UPDATE beans SET deleted_at = datetime('now') "
                "WHERE is_sample = 1 AND deleted_at IS NULL"
            )

    def soft_delete(self, bean_id: int) -> None:
        """목록에서만 숨긴다. 이 원두를 쓴 과거 기록은 그대로 남는다."""
        with self.conn:
            self.conn.execute(
                "UPDATE beans SET deleted_at = datetime('now') WHERE id = ? AND deleted_at IS NULL",
                (bean_id,),
            )
