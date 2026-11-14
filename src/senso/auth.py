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
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from senso import config
from senso.passwords import weakness

ITERATIONS = 600_000
MAX_FAILURES = 5
LOCK_SECONDS = 300
USERNAME = re.compile(r"^[a-z0-9_]{3,32}$")

# 접속 주소(IP)별·전체 제한. 아이디별 제한만 있으면 여러 아이디를 돌아가며 시도하는
# 공격(비밀번호 스프레이)을 막지 못한다. 키는 'ip:<주소>', 'global'로 아이디와 겹치지 않는다.
IP_MAX_FAILURES = 20
IP_WINDOW = 900  # 15분
IP_LOCK_SECONDS = 900
GLOBAL_MAX_FAILURES = 200
GLOBAL_WINDOW = 300
GLOBAL_LOCK_SECONDS = 60
# 회원가입: 주소별 1시간에 3개, 전체 1시간에 50개
SIGNUP_PER_IP = 3
SIGNUP_GLOBAL = 50
SIGNUP_WINDOW = 3600

BUSY = "로그인 시도가 많아요. 잠시 뒤 다시 시도해 주세요."


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
                CREATE TABLE IF NOT EXISTS signup_events (
                    client TEXT NOT NULL, at REAL NOT NULL
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

    def register(self, username: str, password: str, client: str | None = None) -> User:
        name = normalized_username(username)
        check_new_password(password, name)
        now = time.time()
        key = _client_key(client)
        with self.connection() as conn:
            conn.execute("DELETE FROM signup_events WHERE at < ?", (now - SIGNUP_WINDOW,))
            total = conn.execute("SELECT COUNT(*) FROM signup_events").fetchone()[0]
            mine = conn.execute(
                "SELECT COUNT(*) FROM signup_events WHERE client = ?", (key,)
            ).fetchone()[0]
        if mine >= SIGNUP_PER_IP or total >= SIGNUP_GLOBAL:
            raise AuthError("지금은 회원가입이 많아요. 1시간 뒤 다시 시도해 주세요.")
        salt = secrets.token_bytes(32)
        digest = _hash(password, salt)
        user = User(uuid.uuid4().hex, name)
        try:
            with self.connection() as conn:
                conn.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user.id, name, salt, digest))
                conn.execute("INSERT INTO signup_events VALUES (?, ?)", (key, now))
        except sqlite3.IntegrityError:
            raise AuthError("이미 사용 중인 아이디예요.") from None
        return user

    @staticmethod
    def _blocked(conn: sqlite3.Connection, keys: list[str], now: float) -> bool:
        marks = ",".join("?" * len(keys))
        row = conn.execute(
            f"SELECT MAX(blocked_until) FROM login_attempts WHERE username IN ({marks})", keys
        ).fetchone()
        return bool(row[0] and row[0] > now)

    @staticmethod
    def _record_failure(
        conn: sqlite3.Connection, key: str, now: float, limit: int, window: int, lock: int
    ) -> None:
        attempt = conn.execute("SELECT * FROM login_attempts WHERE username = ?", (key,)).fetchone()
        recent = attempt["failures"] if attempt and attempt["updated_at"] > now - window else 0
        failures = recent + 1
        conn.execute(
            "INSERT OR REPLACE INTO login_attempts VALUES (?, ?, ?, ?)",
            (key, failures, now + lock if failures >= limit else 0, now),
        )

    def login(self, username: str, password: str, client: str | None = None) -> User:
        name = normalized_username(username)
        failure = "아이디 또는 비밀번호를 확인해 주세요."
        if not 1 <= len(password) <= 128:
            raise AuthError(failure)
        now = time.time()
        guards = [_client_key(client), "global"]
        with self.connection() as conn:
            if self._blocked(conn, guards, now):
                raise AuthError(BUSY)
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
            self._record_failure(conn, guards[0], now, IP_MAX_FAILURES, IP_WINDOW, IP_LOCK_SECONDS)
            self._record_failure(
                conn, "global", now, GLOBAL_MAX_FAILURES, GLOBAL_WINDOW, GLOBAL_LOCK_SECONDS
            )
        raise AuthError(failure)

    # ---- 로그인한 사용자의 계정 관리 ---------------------------------------------

    def change_password(self, user: User, current: str, new: str, client: str | None = None):
        """지금 비밀번호를 확인한 뒤 바꾼다. 확인 실패는 로그인 실패와 같이 센다."""
        self.login(user.username, current, client)
        check_new_password(new, user.username)
        if hmac.compare_digest(current.encode(), new.encode()):
            raise AuthError("지금 비밀번호와 다른 비밀번호를 입력해 주세요.")
        salt = secrets.token_bytes(32)
        with self.connection() as conn:
            conn.execute(
                "UPDATE users SET salt = ?, password_hash = ? WHERE id = ?",
                (salt, _hash(new, salt), user.id),
            )

    def delete_account(
        self,
        user: User,
        password: str,
        client: str | None = None,
        before_delete: Callable[[], None] | None = None,
    ) -> None:
        """비밀번호를 확인한 뒤 계정과 그 계정의 기록·사진을 모두 지운다. 되돌릴 수 없다.

        before_delete: 확인이 끝난 뒤, 지우기 직전에 부른다 (열린 DB 연결 닫기 등).
        """
        self.login(user.username, password, client)
        if before_delete:
            before_delete()
        directory = user.directory(self.root)  # UUID 검증을 거친 경로
        with self.connection() as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user.id,))
            conn.execute("DELETE FROM login_attempts WHERE username = ?", (user.username,))
        shutil.rmtree(directory, ignore_errors=True)


def check_new_password(password: str, username: str | None = None) -> None:
    if not 12 <= len(password) <= 128:
        raise AuthError("비밀번호는 12~128자로 입력해 주세요.")
    reason = weakness(password, username)
    if reason:
        raise AuthError(reason)


def _client_key(client: str | None) -> str:
    """접속 주소를 제한용 키로. 알 수 없으면 한데 묶는다."""
    return "ip:" + ((client or "unknown").strip()[:64] or "unknown")


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
