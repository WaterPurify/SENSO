"""사진 저장. 고른 사진을 줄여서 앱 데이터 폴더(photos/)에 JPEG로 보관한다."""

import io
import uuid
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_SIDE = 1280
MAX_INPUT_BYTES = 20 * 1024 * 1024
MAX_INPUT_PIXELS = 25_000_000
JPEG_QUALITY = 85


class PhotoError(ValueError):
    pass


def prepare_photo(data: bytes) -> bytes:
    """입력을 검사하고 미리보기용 JPEG를 만든다. 저장 전에는 디스크에 쓰지 않는다."""
    if len(data) > MAX_INPUT_BYTES:
        raise PhotoError("사진이 너무 커요 (20MB 이하)")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.width * source.height > MAX_INPUT_PIXELS:
                    raise PhotoError("사진 해상도가 너무 커요 (2,500만 픽셀 이하)")
                # JPEG는 가능한 경우 디코딩 단계부터 축소한다.
                source.draft("RGB", (MAX_SIDE, MAX_SIDE))
                source.thumbnail((MAX_SIDE, MAX_SIDE))
                img = ImageOps.exif_transpose(source).convert("RGB")
                output = io.BytesIO()
                # 위치 등 원본 메타데이터를 저장하지 않는다.
                img.save(output, "JPEG", quality=JPEG_QUALITY, optimize=True, exif=b"")
                return output.getvalue()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise PhotoError("사진 해상도가 너무 커요") from e
    except (UnidentifiedImageError, OSError, ValueError) as e:
        if isinstance(e, PhotoError):
            raise
        raise PhotoError("이 파일은 사진으로 열 수 없어요 (JPG, PNG를 써 주세요)") from e


def save_prepared_photo(data: bytes, directory: Path) -> str:
    """검증·축소한 사진을 저장한다. 실패한 파일은 남기지 않는다."""
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.jpg"
    path = directory / name
    try:
        path.write_bytes(data)
    except OSError as e:
        path.unlink(missing_ok=True)
        raise PhotoError("사진을 저장하지 못했어요. 저장 공간을 확인해 주세요.") from e
    return name


def save_photo(data: bytes, directory: Path) -> str:
    return save_prepared_photo(prepare_photo(data), directory)


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
    except (OSError, PhotoError):
        pass
