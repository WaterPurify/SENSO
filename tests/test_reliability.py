import asyncio
import io
import json
import sqlite3
import zipfile
from datetime import datetime
from types import SimpleNamespace

import flet as ft
import pytest

from senso import app, auth, config, export
from senso.auth import AuthError, AuthStore
from senso.db.bean_repo import BeanRepository
from senso.db.database import open_database
from senso.domain.bean import BeanKind, validate_bean
from senso.sessions import DataSession
from test_security_and_ui import PASSWORD, Page, button, walk


@pytest.fixture(autouse=True)
def quick_hash(monkeypatch):
    monkeypatch.setattr(auth, "ITERATIONS", 1000)


def seed(root):
    store = AuthStore(root)
    user = store.register("alice", PASSWORD)
    conn = open_database(user.directory(root) / "senso.db")
    BeanRepository(conn).create(validate_bean(BeanKind.TEA, "세작"))
    conn.close()
    return store, user


def test_old_accounts_upgrade_keeps_credentials(tmp_path):
    conn = sqlite3.connect(tmp_path / "accounts.db")
    conn.execute(
        "CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT UNIQUE, "
        "salt BLOB, password_hash BLOB)"
    )
    salt = b"s" * 32
    user_id = "a" * 32
    conn.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?)",
        (user_id, "alice", salt, auth._hash(PASSWORD, salt)),
    )
    conn.commit()
    conn.close()
    store = AuthStore(tmp_path)
    assert store.login("alice", PASSWORD).session_version == 0
    AuthStore(tmp_path)  # migration is idempotent
    assert store.login("alice", PASSWORD).id == user_id


def test_other_device_read_and_write_revoked_after_password_change(tmp_path):
    store, user = seed(tmp_path)
    first, other = DataSession(store, user), DataSession(store, user)
    first.user = store.change_password(user, PASSWORD, "new-coffee-ritual-2026")
    assert len(BeanRepository(first).list(BeanKind.TEA)) == 1
    with pytest.raises(AuthError):
        BeanRepository(other).list(BeanKind.TEA)
    with pytest.raises(AuthError):
        BeanRepository(other).create(validate_bean(BeanKind.TEA, "blocked"))
    with pytest.raises(AuthError):
        store.change_password(user, "new-coffee-ritual-2026", "another-tea-ritual-2026")
    first.close()
    other.close()


def test_failed_delete_remains_blocked_and_can_retry(tmp_path, monkeypatch):
    store, user = seed(tmp_path)
    session = DataSession(store, user)
    real_remove = auth.shutil.rmtree
    monkeypatch.setattr(auth.shutil, "rmtree", lambda _: (_ for _ in ()).throw(OSError("busy")))
    with pytest.raises(OSError):
        store.delete_account(user, PASSWORD)
    with pytest.raises(AuthError):
        store.login(user.username, PASSWORD)
    with pytest.raises(AuthError):
        BeanRepository(session).list(BeanKind.TEA)
    with pytest.raises(AuthError):
        store.register(user.username, PASSWORD)
    session.close()
    monkeypatch.setattr(auth.shutil, "rmtree", real_remove)
    store.finish_delete(user.id)
    assert not (tmp_path / "users" / user.id).exists()
    assert store.register(user.username, PASSWORD).id != user.id


def test_worker_export_and_account_isolation(tmp_path):
    store, user = seed(tmp_path)
    other = store.register("bob", PASSWORD)
    conn = open_database(other.directory(tmp_path) / "senso.db")
    BeanRepository(conn).create(validate_bean(BeanKind.COFFEE, "private"))
    conn.close()
    result = asyncio.run(asyncio.to_thread(export.export_account, store, user, datetime.now()))
    with zipfile.ZipFile(io.BytesIO(result)) as archive:
        data = json.loads(archive.read("data.json"))
        assert [bean["name"] for bean in data["beans"]] == ["세작"]
        assert "accounts.db" not in archive.namelist()
        assert "users" not in data


def test_export_missing_photo_size_and_revoked_session(tmp_path, monkeypatch):
    store, user = seed(tmp_path)
    path = tmp_path / "users" / user.id / "senso.db"
    conn = open_database(path)
    conn.execute("UPDATE beans SET photo_path = 'missing.jpg'")
    conn.commit()
    conn.close()
    with pytest.raises(export.ExportError, match="사진이 없어요"):
        export.export_account(store, user, datetime.now())
    monkeypatch.setattr(export, "MAX_EXPORT_BYTES", 1)
    with pytest.raises(export.ExportError, match="기록이 커서"):
        export.export_account(store, user, datetime.now())
    store.begin_delete(user, PASSWORD)
    with pytest.raises(export.ExportError, match="만료"):
        export.export_account(store, user, datetime.now())


def test_export_button_calls_real_worker_and_recovers(tmp_path, monkeypatch):
    store, user = seed(tmp_path)
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(ft.Control, "update", lambda _: None)
    monkeypatch.setattr(ft.Control, "page", property(lambda _: None))
    saved = []

    async def save_file(self, **kwargs):
        saved.append(kwargs["src_bytes"])

    monkeypatch.setattr(ft.FilePicker, "save_file", save_file)
    page = Page()
    app.authenticated_main(page, user, store)
    page.navigation_bar.on_change(SimpleNamespace(control=SimpleNamespace(selected_index=3)))
    export_button = button(page.controls[0], "내 데이터 내보내기 (ZIP)")
    asyncio.run(export_button.on_click(None))
    assert zipfile.is_zipfile(io.BytesIO(saved[0]))
    assert not export_button.disabled

    def fail(*args):
        raise OSError("disk unavailable")

    monkeypatch.setattr(app, "export_account", fail)
    asyncio.run(export_button.on_click(None))
    assert not export_button.disabled
    assert "내보내지 못했어요" in page.dialog.content
    page.on_close(None)


def test_two_live_pages_password_change_keeps_current_device(tmp_path, monkeypatch):
    store, user = seed(tmp_path)
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(ft.Control, "update", lambda _: None)
    first, other = Page(), Page()
    app.authenticated_main(first, user, store)
    app.authenticated_main(other, user, store)
    first.navigation_bar.on_change(SimpleNamespace(control=SimpleNamespace(selected_index=3)))
    button(first.controls[0], "비밀번호 바꾸기").on_click(None)
    fields = [c for c in walk(first.dialog) if isinstance(c, ft.TextField)]
    for field, value in zip(
        fields, [PASSWORD, "new-coffee-ritual-2026", "new-coffee-ritual-2026"], strict=True
    ):
        field.value = value
    asyncio.run(button(first.dialog, "바꾸기").on_click(None))
    assert button(other.appbar, "로그인")
    assert button(first.appbar, "로그아웃")
    first.navigation_bar.on_change(SimpleNamespace(control=SimpleNamespace(selected_index=0)))
    first.on_close(None)


def test_deleted_account_cannot_use_open_connection_or_recreate_directory(tmp_path):
    store, user = seed(tmp_path)
    old = DataSession(store, user)
    store.delete_account(user, PASSWORD)
    with pytest.raises(AuthError):
        BeanRepository(old).list(BeanKind.TEA)
    with pytest.raises(AuthError):
        DataSession(store, user)
    assert not (tmp_path / "users" / user.id).exists()
    old.close()


def test_idle_page_detects_revocation_from_another_process(tmp_path, monkeypatch):
    store, user = seed(tmp_path)
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(ft.Control, "update", lambda _: None)
    page = Page()
    tasks = []
    page.run_task = lambda fn, **kwargs: tasks.append(fn)
    app.authenticated_main(page, user, store)
    # Bypass the in-process registry, as an administrator/another worker would.
    store.change_password(user, PASSWORD, "new-coffee-ritual-2026")

    async def tick(_):
        pass

    monkeypatch.setattr(app.asyncio, "sleep", tick)
    watch = next(fn for fn in tasks if fn.__name__ == "watch_idle")
    asyncio.run(watch())
    assert button(page.appbar, "로그인")
