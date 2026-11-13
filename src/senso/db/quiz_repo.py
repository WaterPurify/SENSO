"""취향 테스트 결과 저장소."""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SavedQuiz:
    id: int
    taken_at: datetime
    answers: tuple[int, ...]
    type_code: str


class QuizRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save(self, answers: list[int], type_code: str, taken_at: datetime) -> SavedQuiz:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO quiz_results (taken_at, answers, type_code) VALUES (?, ?, ?)",
                (taken_at.isoformat(timespec="minutes"), json.dumps(answers), type_code),
            )
        return SavedQuiz(
            cur.lastrowid, taken_at.replace(second=0, microsecond=0), tuple(answers), type_code
        )

    def latest(self) -> SavedQuiz | None:
        row = self.conn.execute(
            "SELECT id, taken_at, answers, type_code FROM quiz_results "
            "ORDER BY taken_at DESC, id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        return SavedQuiz(row[0], datetime.fromisoformat(row[1]), tuple(json.loads(row[2])), row[3])
