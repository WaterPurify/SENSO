"""앱 데이터(DB, 사진)를 저장할 위치."""

import os
from pathlib import Path

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


def db_path() -> Path:
    return data_dir() / DB_FILENAME


def photos_dir() -> Path:
    path = data_dir() / "photos"
    path.mkdir(parents=True, exist_ok=True)
    return path
