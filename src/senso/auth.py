"""서버 측 계정 인증. 계정별 UUID 저장소로 기록과 사진을 분리한다."""

import argparse
import getpass
import hashlib
import hmac
import re
import secrets
import shutil
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from senso import config

ITERATIONS = 600_000
MAX_FAILURES = 5
LOCK_SECONDS = 300
USERNAME = re.compile(r"^[a-z0-9_]{3,32}$")


class AuthError(ValueError):
    pass


@dataclass(frozen=True)
class User:
    id: str
    username: str

    def directory(self, root: Path) -> Path:
        # DB 값이라도 경로로 쓰기 전에 검증한다.
        if uuid.UUID(self.id).hex != self.id:
            raise ValueError("잘못된 사용자 ID")
        path = root / "users" / self.id
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return path


def normalized_username(value: str) -> str:
    name = value.strip().lower()
    if not USERNAME.fullmatch(name):
        raise AuthError("아이디는 영문 소문자·숫자·밑줄로 3~32자 입력해 주세요.")
    return name


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)


class AuthStore:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "accounts.db"
        with self.connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                    salt BLOB NOT NULL, password_hash BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS login_attempts (
                    username TEXT PRIMARY KEY, failures INTEGER NOT NULL,
                    blocked_until REAL NOT NULL, updated_at REAL NOT NULL
                );
            """)
        self.path.chmod(0o600)

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def register(self, username: str, password: str) -> User:
        name = normalized_username(username)
        if not 12 <= len(password) <= 128:
            raise AuthError("비밀번호는 12~128자로 입력해 주세요.")
        salt = secrets.token_bytes(32)
        digest = _hash(password, salt)
        user = User(uuid.uuid4().hex, name)
        try:
            with self.connection() as conn:
                conn.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user.id, name, salt, digest))
        except sqlite3.IntegrityError:
            raise AuthError("이미 사용 중인 아이디예요.") from None
        return user

    def login(self, username: str, password: str) -> User:
        name = normalized_username(username)
        failure = "아이디 또는 비밀번호를 확인해 주세요."
        if not 1 <= len(password) <= 128:
            raise AuthError(failure)
        now = time.time()
        with self.connection() as conn:
            attempt = conn.execute(
                "SELECT * FROM login_attempts WHERE username = ?", (name,)
            ).fetchone()
            if attempt and attempt["blocked_until"] > now:
                raise AuthError("로그인 시도가 많아요. 5분 뒤 다시 시도해 주세요.")
            row = conn.execute("SELECT * FROM users WHERE username = ?", (name,)).fetchone()
        # 없는 계정도 같은 비용의 비밀번호 검증을 수행한다.
        digest = _hash(password, row["salt"] if row else bytes(32))
        valid = hmac.compare_digest(digest, row["password_hash"] if row else bytes(32))
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            attempt = conn.execute(
                "SELECT * FROM login_attempts WHERE username = ?", (name,)
            ).fetchone()
            if attempt and attempt["blocked_until"] > now:
                raise AuthError("로그인 시도가 많아요. 5분 뒤 다시 시도해 주세요.")
            if valid and row:
                conn.execute("DELETE FROM login_attempts WHERE username = ?", (name,))
                return User(row["id"], row["username"])
            failures = (
                attempt["failures"] if attempt and attempt["updated_at"] > now - LOCK_SECONDS else 0
            ) + 1
            conn.execute("DELETE FROM login_attempts WHERE updated_at < ?", (now - 86400,))
            conn.execute(
                "INSERT OR REPLACE INTO login_attempts VALUES (?, ?, ?, ?)",
                (name, failures, now + LOCK_SECONDS if failures >= MAX_FAILURES else 0, now),
            )
        raise AuthError(failure)


def create_account_cli() -> None:
    parser = argparse.ArgumentParser(description="SENSO 계정 생성 (서버 관리자용)")
    parser.add_argument("username")
    parser.add_argument(
        "--import-legacy",
        action="store_true",
        help="기존 개인용 DB·사진을 새 계정으로 복사 (앱을 중지하고 실행)",
    )
    args = parser.parse_args()
    root = config.data_dir()
    if args.import_legacy and not (root / config.DB_FILENAME).is_file():
        parser.error("가져올 기존 senso.db가 없습니다.")
    password = getpass.getpass("비밀번호 (12~128자): ")
    if password != getpass.getpass("비밀번호 확인: "):
        parser.error("비밀번호가 일치하지 않습니다.")
    store = AuthStore(root)
    user = store.register(args.username, password)
    directory = user.directory(root)
    try:
        if args.import_legacy:
            source = sqlite3.connect(root / config.DB_FILENAME)
            target = sqlite3.connect(directory / config.DB_FILENAME)
            try:
                source.backup(target)
            finally:
                source.close()
                target.close()
            if (root / "photos").is_dir():
                shutil.copytree(root / "photos", directory / "photos")
    except Exception:
        shutil.rmtree(directory)
        with store.connection() as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user.id,))
        raise
    print("계정을 만들었습니다. 기존 원본 데이터는 그대로 보존됩니다.")


if __name__ == "__main__":
    create_account_cli()
