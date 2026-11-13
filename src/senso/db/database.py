"""SQLite 연결과 스키마 마이그레이션.

마이그레이션은 migrations/NNN_*.sql 파일을 번호 순서대로 실행하고,
적용한 마지막 번호를 SQLite의 PRAGMA user_version에 기록한다.
"""

import re
import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_MIGRATION_NAME = re.compile(r"^(\d{3})_.+\.sql$")


def connect(path: Path | str) -> sqlite3.Connection:
    """DB에 연결한다. 외래 키 검사를 켜고, 행을 이름으로 읽을 수 있게 한다."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def available_migrations(directory: Path = MIGRATIONS_DIR) -> list[tuple[int, Path]]:
    found = []
    for file in directory.iterdir():
        match = _MIGRATION_NAME.match(file.name)
        if match:
            found.append((int(match.group(1)), file))
    found.sort()
    versions = [v for v, _ in found]
    if versions != list(range(1, len(versions) + 1)):
        raise RuntimeError(f"마이그레이션 번호가 1부터 연속되지 않습니다: {versions}")
    return found


def schema_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def migrate(conn: sqlite3.Connection, directory: Path = MIGRATIONS_DIR) -> int:
    """아직 적용하지 않은 마이그레이션을 실행하고 최종 버전을 돌려준다.

    파일 하나는 한 트랜잭션으로 실행되어, 중간에 실패하면 그 파일 전체가 취소된다.
    """
    current = schema_version(conn)
    for version, file in available_migrations(directory):
        if version <= current:
            continue
        sql = file.read_text(encoding="utf-8")
        try:
            conn.executescript(f"BEGIN;\n{sql}\nPRAGMA user_version = {version};\nCOMMIT;")
        except sqlite3.Error:
            if conn.in_transaction:
                conn.rollback()
            raise
        current = version
    return current


def open_database(path: Path | str) -> sqlite3.Connection:
    """연결하고 최신 스키마로 맞춘 뒤 돌려준다."""
    conn = connect(path)
    try:
        migrate(conn)
    except Exception:
        conn.close()
        raise
    return conn
