"""오늘의 말씀 한 잔 기록. 하루에 한 장."""

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class WordCard:
    id: int
    day: date
    mood: str
    verse_ref: str
    note: str | None
    saved: bool
    created_at: datetime


class AlreadyToday(Exception):
    """오늘은 이미 카드를 받았다."""


_COLUMNS = "id, day, mood, verse_ref, note, saved, created_at"


def _to_card(row: sqlite3.Row) -> WordCard:
    return WordCard(
        id=row["id"],
        day=date.fromisoformat(row["day"]),
        mood=row["mood"],
        verse_ref=row["verse_ref"],
        note=row["note"],
        saved=bool(row["saved"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class WordRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def for_day(self, day: date) -> WordCard | None:
        row = self.conn.execute(
            f"SELECT {_COLUMNS} FROM word_cards WHERE day = ?", (day.isoformat(),)
        ).fetchone()
        return _to_card(row) if row else None

    def get(self, card_id: int) -> WordCard | None:
        row = self.conn.execute(
            f"SELECT {_COLUMNS} FROM word_cards WHERE id = ?", (card_id,)
        ).fetchone()
        return _to_card(row) if row else None

    def create(
        self, day: date, mood: str, verse_ref: str, note: str | None, now: datetime
    ) -> WordCard:
        note = (note or "").strip() or None
        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO word_cards (day, mood, verse_ref, note, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (day.isoformat(), mood, verse_ref, note, now.isoformat(timespec="minutes")),
                )
        except sqlite3.IntegrityError as e:
            raise AlreadyToday(day.isoformat()) from e
        card = self.get(cur.lastrowid)
        assert card is not None
        return card

    def set_saved(self, card_id: int, saved: bool) -> None:
        with self.conn:
            self.conn.execute("UPDATE word_cards SET saved = ? WHERE id = ?", (int(saved), card_id))

    def saved(self) -> list[WordCard]:
        """말씀 노트: 저장한 카드, 최신순."""
        rows = self.conn.execute(
            f"SELECT {_COLUMNS} FROM word_cards WHERE saved = 1 ORDER BY day DESC"
        ).fetchall()
        return [_to_card(r) for r in rows]
