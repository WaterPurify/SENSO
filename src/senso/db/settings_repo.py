"""앱 설정 (키-값)."""

import sqlite3

WORD_ENABLED = "word_enabled"  # 오늘의 말씀 한 잔: '1' 켬, '0' 끔, 없음 = 아직 고르지 않음


class SettingsRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def set(self, key: str, value: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO app_settings (key, value) VALUES (?, ?) "
                "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def get_flag(self, key: str) -> bool | None:
        value = self.get(key)
        return None if value is None else value == "1"

    def set_flag(self, key: str, on: bool) -> None:
        self.set(key, "1" if on else "0")
