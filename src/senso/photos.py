"""사진 저장. 고른 사진을 줄여서 앱 데이터 폴더(photos/)에 JPEG로 보관한다."""

import io
import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_SIDE = 1280
MAX_INPUT_BYTES = 20 * 1024 * 1024
JPEG_QUALITY = 85


class PhotoError(ValueError):
    pass


def save_photo(data: bytes, directory: Path) -> str:
    """사진을 저장하고 파일 이름을 돌려준다. 이미지가 아니면 PhotoError."""
    if len(data) > MAX_INPUT_BYTES:
        raise PhotoError("사진이 너무 커요 (20MB 이하)")
    try:
        with Image.open(io.BytesIO(data)) as img:
            img = ImageOps.exif_transpose(img)  # 폰 사진의 회전 정보 반영
            img = img.convert("RGB")
            img.thumbnail((MAX_SIDE, MAX_SIDE))
            name = f"{uuid.uuid4().hex}.jpg"
            directory.mkdir(parents=True, exist_ok=True)
            img.save(directory / name, "JPEG", quality=JPEG_QUALITY, optimize=True)
    except (UnidentifiedImageError, OSError) as e:
        raise PhotoError("이 파일은 사진으로 열 수 없어요 (JPG, PNG를 써 주세요)") from e
    return name


def _safe_path(name: str, directory: Path) -> Path:
    path = (directory / name).resolve()
    if path.parent != directory.resolve():
        raise PhotoError("잘못된 사진 경로예요")
    return path


def load_photo(name: str, directory: Path) -> bytes | None:
    """사진 내용을 읽는다. 파일이 없으면 None (화면에서는 사진 없이 표시)."""
    try:
        return _safe_path(name, directory).read_bytes()
    except (OSError, PhotoError):
        return None


def delete_photo(name: str, directory: Path) -> None:
    try:
        _safe_path(name, directory).unlink(missing_ok=True)
    except PhotoError:
        pass
