"""앱 데이터(DB, 사진)를 저장할 위치."""

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DB_FILENAME = "senso.db"


def data_dir() -> Path:
    """데이터 폴더 경로를 돌려준다. 폴더가 없으면 만든다.

    1. SENSO_DATA_DIR: 직접 지정 (Docker에서는 /data 볼륨)
    2. FLET_APP_STORAGE_DATA: 폰에 설치된 앱의 전용 저장소 (Flet이 설정)
    3. 둘 다 없으면 프로젝트의 .data/ 폴더 (Git에서 제외)
    """
    env = os.getenv("SENSO_DATA_DIR") or os.getenv("FLET_APP_STORAGE_DATA")
    path = Path(env) if env else Path(__file__).resolve().parents[2] / ".data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def now() -> datetime:
    """현지 시각(초 단위 없음, 시간대 정보 없음).

    폰·PC에서는 기기 시각을 쓴다. Docker처럼 시각이 UTC인 곳에서는
    SENSO_TZ(예: Asia/Seoul)로 시간대를 지정한다.
    """
    tz = os.getenv("SENSO_TZ")
    current = datetime.now(ZoneInfo(tz)) if tz else datetime.now()
    return current.replace(tzinfo=None, second=0, microsecond=0)


def db_path() -> Path:
    return data_dir() / DB_FILENAME


def photos_dir() -> Path:
    path = data_dir() / "photos"
    path.mkdir(parents=True, exist_ok=True)
    return path
