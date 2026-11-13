"""추천 저장소. '이 레시피로 새 기록'을 누를 때 어떤 제안을 따랐는지 남긴다."""

import sqlite3
from dataclasses import dataclass

from senso.recommend.engine import Recommendation


@dataclass(frozen=True)
class SavedRecommendation:
    id: int
    source_brew_id: int
    changed_field: str
    from_value: str | None
    to_value_or_direction: str
    reason: str
    method: str


class RecommendationRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save(self, source_brew_id: int, rec: Recommendation) -> SavedRecommendation:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO recommendations (source_brew_id, changed_field, from_value, "
                "to_value_or_direction, reason, method) VALUES (?, ?, ?, ?, ?, ?)",
                (source_brew_id, rec.field, rec.from_value, rec.to_value, rec.reason, rec.method),
            )
        saved = self.get(cur.lastrowid)
        assert saved is not None
        return saved

    def get(self, rec_id: int) -> SavedRecommendation | None:
        row = self.conn.execute(
            "SELECT id, source_brew_id, changed_field, from_value, to_value_or_direction, reason, "
            "method FROM recommendations WHERE id = ?",
            (rec_id,),
        ).fetchone()
        return SavedRecommendation(*row) if row else None
