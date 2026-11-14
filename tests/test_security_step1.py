"""보안 1단계: 주소별·전체 로그인 제한, 가입 제한, 약한 비밀번호, 비밀번호 변경,
계정 삭제, 내 데이터 내보내기, 말씀 메모 미저장."""

import io
import json
import zipfile
from datetime import date, datetime

import pytest

from senso import auth
from senso.auth import AuthError, AuthStore
from senso.db.bean_repo import BeanRepository
from senso.db.database import open_database
from senso.db.word_repo import WordRepository
from senso.domain.bean import BeanKind, validate_bean
from senso.export import export_zip
from senso.passwords import weakness

PASSWORD = "safe-test-password-123"
NOW = datetime(2026, 11, 14, 9, 0)


@pytest.fixture(autouse=True)
def fast_hash(monkeypatch):
    # 테스트에서는 해시 반복을 줄여 빠르게 (규칙 검증이 목적)
    monkeypatch.setattr(auth, "ITERATIONS", 1000)


# ---- 약한 비밀번호 ----------------------------------------------------------------


@pytest.mark.parametrize(
    "password",
    [
        "password1234",
        "Password!2026",
        "qwerty123456",
        "123456789012",
        "aaaaaaaaaaaa",
        "abcabcabcabc",
        "abcdefghijkl",
        "1q2w3e4r5t6y",
        "iloveyou!!!!",
        "saranghae1004",
    ],
)
def test_weak_passwords(password):
    assert weakness(password) is not None


def test_password_with_username_is_weak():
    assert weakness("my-alice-coffee-2026", "alice") is not None


@pytest.mark.parametrize(
    "password", [PASSWORD, "coffee-lover-at-jeju-2026", "산미가 좋은 아침 한 잔", "Tq8#mZ2!vLp9"]
)
def test_good_passwords(password):
    assert weakness(password, "alice") is None


def test_register_rejects_weak(tmp_path):
    with pytest.raises(AuthError):
        AuthStore(tmp_path).register("alice", "password1234")


# ---- 주소별·전체 로그인 제한 ---------------------------------------------------------


def test_ip_lock_stops_password_spraying(tmp_path, monkeypatch):
    """여러 아이디를 돌아가며 틀려도, 같은 주소에서 일정 횟수가 넘으면 막힌다."""
    monkeypatch.setattr(auth, "IP_MAX_FAILURES", 4)
    store = AuthStore(tmp_path)
    store.register("victim", PASSWORD, "10.0.0.9")
    for i in range(4):  # 아이디별 제한(5회)에는 걸리지 않게 아이디를 바꿔 가며
        with pytest.raises(AuthError):
            store.login(f"user{i}", "wrong-password", "10.0.0.1")
    with pytest.raises(AuthError, match="잠시 뒤"):
        store.login("victim", PASSWORD, "10.0.0.1")  # 맞는 비밀번호여도 이 주소는 잠김
    assert store.login("victim", PASSWORD, "10.0.0.2").username == "victim"  # 다른 주소는 괜찮음


def test_global_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "GLOBAL_MAX_FAILURES", 3)
    store = AuthStore(tmp_path)
    store.register("alice", PASSWORD, "10.0.0.9")
    for i in range(3):
        with pytest.raises(AuthError):
            store.login("ghost", "wrong-password", f"10.0.1.{i}")
    with pytest.raises(AuthError, match="잠시 뒤"):
        store.login("alice", PASSWORD, "10.0.2.1")


def test_signup_limit_per_client(tmp_path):
    store = AuthStore(tmp_path)
    for i in range(auth.SIGNUP_PER_IP):
        store.register(f"member{i}", PASSWORD, "10.0.0.5")
    with pytest.raises(AuthError, match="회원가입"):
        store.register("onemore", PASSWORD, "10.0.0.5")
    assert store.register("other", PASSWORD, "10.0.0.6").username == "other"


# ---- 비밀번호 변경·계정 삭제 ------------------------------------------------------------


def test_change_password(tmp_path):
    store = AuthStore(tmp_path)
    user = store.register("alice", PASSWORD)
    new = "new-coffee-ritual-2026"
    with pytest.raises(AuthError):
        store.change_password(user, "wrong-password", new)
    with pytest.raises(AuthError):
        store.change_password(user, PASSWORD, "password1234")  # 약한 새 비밀번호
    with pytest.raises(AuthError):
        store.change_password(user, PASSWORD, PASSWORD)  # 같은 비밀번호
    updated = store.change_password(user, PASSWORD, new)
    with pytest.raises(AuthError):
        store.login("alice", PASSWORD)
    assert store.login("alice", new) == updated
    assert updated.session_version == user.session_version + 1


def test_delete_account_removes_everything(tmp_path):
    store = AuthStore(tmp_path)
    user = store.register("alice", PASSWORD)
    other = store.register("bob", PASSWORD)
    directory = user.directory(tmp_path)
    conn = open_database(directory / "senso.db")
    BeanRepository(conn).create(validate_bean(BeanKind.COFFEE, "예가체프"))
    conn.close()
    (directory / "photos").mkdir()
    (directory / "photos" / "a.jpg").write_bytes(b"x")

    with pytest.raises(AuthError):
        store.delete_account(user, "wrong-password")
    assert directory.exists()

    called = []
    store.delete_account(user, PASSWORD, before_delete=lambda: called.append(True))
    assert called == [True]
    assert not directory.exists()
    with pytest.raises(AuthError):
        store.login("alice", PASSWORD)
    assert other.directory(tmp_path).exists()  # 다른 계정은 그대로
    assert store.register("alice", PASSWORD).id != user.id  # 같은 아이디로 새로 가입 가능


# ---- 내보내기 ------------------------------------------------------------------------


def test_export_zip(tmp_path):
    conn = open_database(tmp_path / "senso.db")
    BeanRepository(conn).create(validate_bean(BeanKind.TEA, "세작", origin="제주"))
    photos = tmp_path / "photos"
    photos.mkdir()
    (photos / "p1.jpg").write_bytes(b"jpeg")
    data = export_zip(conn, photos, NOW)
    conn.close()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = set(zf.namelist())
        assert {"README.txt", "data.json", "photos/p1.jpg"} <= names
        body = json.loads(zf.read("data.json"))
    assert body["beans"][0]["name"] == "세작"
    assert body["beans"][0]["origin"] == "제주"
    assert "word_cards" in body and "brews" in body


# ---- 말씀 메모 ------------------------------------------------------------------------


def test_old_word_notes_are_forgotten(tmp_path):
    """v6 마이그레이션은 예전에 저장된 한 줄을 지운다."""
    import shutil

    from senso.db.database import MIGRATIONS_DIR, available_migrations, connect, migrate

    old = tmp_path / "v5"
    old.mkdir()
    for version, path in available_migrations():
        if version <= 5:
            shutil.copy(path, old / path.name)
    c = connect(tmp_path / "old.db")
    migrate(c, old)
    WordRepository(c).create(date(2026, 11, 13), "sad", "시편 34:18", "아주 개인적인 이야기", NOW)
    assert migrate(c, MIGRATIONS_DIR) >= 6
    card = WordRepository(c).for_day(date(2026, 11, 13))
    assert card.note is None and card.verse_ref == "시편 34:18"
    c.close()
