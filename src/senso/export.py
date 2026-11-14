"""내 데이터 내보내기: 계정의 기록 전체(JSON)와 사진을 ZIP 하나로."""

import io
import json
import sqlite3
import threading
import zipfile
from datetime import datetime
from pathlib import Path

README = """SENSO 내 데이터 내보내기

- data.json : 원두·차, 추출 기록, 추천, 취향 테스트, 말씀 카드, 설정 (표 이름별 목록)
- photos/   : 원두·차 사진

이 파일에는 개인 기록이 들어 있어요. 안전한 곳에 보관해 주세요.
"""


def export_zip(conn: sqlite3.Connection, photo_dir: Path, now: datetime) -> bytes:
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
    ]
    data: dict[str, object] = {
        "exported_at": now.isoformat(timespec="minutes"),
        "schema_version": conn.execute("PRAGMA user_version").fetchone()[0],
    }
    for table in tables:
        cur = conn.execute(f'SELECT * FROM "{table}"')  # 이름은 sqlite_master에서 온 것
        columns = [c[0] for c in cur.description]
        data[table] = [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]

    payload = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    if len(payload.encode("utf-8")) > MAX_EXPORT_BYTES:
        raise ExportError("기록이 너무 커요. 관리자에게 백업을 요청해 주세요.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.txt", README)
        zf.writestr("data.json", payload)
        if photo_dir.is_dir():
            for photo in sorted(photo_dir.iterdir()):
                # 심볼릭 링크 등은 건너뛰고, 이 폴더 안의 보통 파일만 담는다
                if photo.is_file() and not photo.is_symlink():
                    zf.write(photo, f"photos/{photo.name}")
    return buf.getvalue()


class ExportError(ValueError):
    pass


# Bound the complete download, including uncompressed input, within the 768 MiB
# production container. One export per process; the UI can retry when busy.
_export_slot = threading.Lock()
MAX_EXPORT_BYTES = 32 * 1024 * 1024


def export_account(store, user, now: datetime) -> bytes:
    """Open/close SQLite in the worker thread; never pass a UI connection here."""
    if not _export_slot.acquire(blocking=False):
        raise ExportError("다른 내보내기가 진행 중이에요. 잠시 뒤 다시 시도해 주세요.")
    try:
        with store.connection() as auth:
            auth.execute("BEGIN")
            row = auth.execute(
                "SELECT session_version, deleting FROM users WHERE id = ?", (user.id,)
            ).fetchone()
            if not row or row["deleting"] or row["session_version"] != user.session_version:
                raise ExportError("로그인이 만료됐어요. 다시 로그인해 주세요.")
            directory = store.root / "users" / user.id
            path = directory / "senso.db"
            if path.stat().st_size > MAX_EXPORT_BYTES:
                raise ExportError(
                    "기록이 커서 ZIP으로 내보낼 수 없어요. 관리자에게 백업을 요청해 주세요."
                )
            conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
            try:
                conn.execute("BEGIN")
                photos = directory / "photos"
                before = _photo_snapshot(photos)
                referenced = conn.execute(
                    "SELECT photo_path FROM beans WHERE photo_path IS NOT NULL"
                ).fetchall()
                if any(name not in before for (name,) in referenced if name):
                    raise ExportError(
                        "기록에 연결된 사진이 없어요. 관리자에게 확인을 요청해 주세요."
                    )
                if path.stat().st_size + sum(v[0] for v in before.values()) > MAX_EXPORT_BYTES:
                    raise ExportError(
                        "사진과 기록이 커서 ZIP으로 내보낼 수 없어요. "
                        "관리자에게 백업을 요청해 주세요."
                    )
                result = export_zip(conn, photos, now)
                if before != _photo_snapshot(photos):
                    raise ExportError("사진이 변경됐어요. 저장을 마친 뒤 다시 내보내 주세요.")
                if len(result) > MAX_EXPORT_BYTES:
                    raise ExportError("ZIP 파일이 너무 커요. 관리자에게 백업을 요청해 주세요.")
                return result
            finally:
                conn.close()
    finally:
        _export_slot.release()


def _photo_snapshot(directory: Path) -> dict:
    result = {}
    if directory.is_symlink():
        raise ExportError("사진 폴더를 확인해야 해요. 관리자에게 문의해 주세요.")
    if directory.exists():
        for path in directory.iterdir():
            if path.is_symlink() or not path.is_file():
                raise ExportError("사진 폴더를 확인해야 해요. 관리자에게 문의해 주세요.")
            stat = path.stat()
            result[path.name] = (stat.st_size, stat.st_mtime_ns, stat.st_ino)
    return result
