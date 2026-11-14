"""내 데이터 내보내기: 계정의 기록 전체(JSON)와 사진을 ZIP 하나로."""

import io
import json
import sqlite3
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

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.txt", README)
        zf.writestr("data.json", json.dumps(data, ensure_ascii=False, indent=2, default=str))
        if photo_dir.is_dir():
            for photo in sorted(photo_dir.iterdir()):
                # 심볼릭 링크 등은 건너뛰고, 이 폴더 안의 보통 파일만 담는다
                if photo.is_file() and not photo.is_symlink():
                    zf.write(photo, f"photos/{photo.name}")
    return buf.getvalue()
