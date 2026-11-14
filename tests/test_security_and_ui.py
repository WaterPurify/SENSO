import asyncio
import io
import sqlite3
from dataclasses import fields
from datetime import datetime
from types import SimpleNamespace

import flet as ft
import pytest
from PIL import Image

from senso import app, config, photos
from senso.auth import AuthError, AuthStore
from senso.db.bean_repo import BeanRepository
from senso.db.brew_repo import BrewRepository
from senso.db.database import open_database
from senso.domain.bean import BeanKind, validate_bean
from senso.domain.brew import validate_brew
from senso.ui.views.bean_form import FormDeps, bean_form_view

PASSWORD = "safe-test-password-123"


def png(size=(40, 20)):
    output = io.BytesIO()
    Image.new("RGB", size, "red").save(output, "PNG")
    return output.getvalue()


def walk(control):
    if not isinstance(control, ft.BaseControl):
        return
    yield control
    for field in fields(control):
        if field.name.startswith("_"):
            continue
        value = getattr(control, field.name)
        for child in value if isinstance(value, list) else [value]:
            if isinstance(child, ft.BaseControl):
                yield from walk(child)


def button(control, text):
    return next(c for c in walk(control) if getattr(c, "content", None) == text)


class Page:
    def __init__(self):
        self.controls = []
        self.dialog = None
        self.web = True

    def clean(self):
        self.controls = []

    def add(self, control):
        self.controls.append(control)

    def update(self):
        pass

    def run_task(self, *args, **kwargs):
        pass

    def show_dialog(self, dialog):
        self.dialog = dialog

    def pop_dialog(self):
        self.dialog = None


@pytest.fixture
def ui(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(ft.Control, "update", lambda self: None)
    return Page()


def test_password_hash_and_login(tmp_path):
    store = AuthStore(tmp_path)
    user = store.register("Alice", PASSWORD)
    assert store.login(" alice ", PASSWORD) == user
    with store.connection() as conn:
        row = conn.execute("SELECT * FROM users").fetchone()
        assert row["password_hash"] != PASSWORD.encode()
        assert len(row["salt"]) == 32
    with pytest.raises(AuthError):
        store.register("ALICE", PASSWORD)
    with pytest.raises(AuthError):
        store.login("alice", "wrong")
    with pytest.raises(AuthError):
        store.register("../escape", PASSWORD)


def test_login_lock_survives_new_store(tmp_path):
    store = AuthStore(tmp_path)
    store.register("alice", PASSWORD)
    for _ in range(5):
        with pytest.raises(AuthError):
            store.login("alice", "wrong")
    with pytest.raises(AuthError, match="5분"):
        AuthStore(tmp_path).login("alice", PASSWORD)


def test_accounts_isolate_records_photos_and_legacy(tmp_path):
    legacy = open_database(tmp_path / "senso.db")
    BeanRepository(legacy).create(validate_bean(BeanKind.COFFEE, "legacy-private"))
    legacy.close()
    store = AuthStore(tmp_path)
    alice = store.register("alice", PASSWORD)
    bob = store.register("bob", PASSWORD)
    a = open_database(alice.directory(tmp_path) / "senso.db")
    b = open_database(bob.directory(tmp_path) / "senso.db")
    try:
        assert BeanRepository(a).list_all() == []
        BeanRepository(a).create(validate_bean(BeanKind.COFFEE, "Alice only"))
        photo = photos.save_photo(png(), alice.directory(tmp_path) / "photos")
        assert BeanRepository(b).list_all() == []
        assert photos.load_photo(photo, bob.directory(tmp_path) / "photos") is None
    finally:
        a.close()
        b.close()


def test_login_gate_and_logout(ui, tmp_path):
    store = AuthStore(tmp_path)
    store.register("alice", PASSWORD)
    app.main(ui)
    assert ui.navigation_bar is None
    assert not (tmp_path / "users").exists()
    button(ui.appbar, "로그인").on_click(None)
    inputs = [c for c in walk(ui.dialog) if isinstance(c, ft.TextField)]
    inputs[0].value, inputs[1].value = "alice", PASSWORD
    asyncio.run(button(ui.dialog, "로그인").on_click(None))
    assert ui.navigation_bar is not None
    button(ui.appbar, "로그아웃").on_click(None)
    assert ui.navigation_bar is None
    assert "Alice only" not in str(ui.controls)


def test_home_shows_20_then_40_then_45(ui, tmp_path):
    user = AuthStore(tmp_path).register("alice", PASSWORD)
    conn = open_database(user.directory(tmp_path) / "senso.db")
    bean = BeanRepository(conn).create(validate_bean(BeanKind.COFFEE, "coffee"))
    draft = validate_brew(bean=bean, bean_id=bean.id, dose_g="15", water_g="250")
    repo = BrewRepository(conn)
    for _ in range(45):
        repo.create(draft, datetime(2026, 11, 14))
    assert repo.count() == 45
    assert len(repo.list(limit=21)) == 21
    conn.close()
    app.authenticated_main(ui, user)
    for count in (20, 40, 45):
        texts = [c.value for c in walk(ui.controls[0]) if isinstance(c, ft.Text)]
        assert f"최근 기록 {count}개" in texts
        if count < 45:
            button(ui.controls[0], "더 보기").on_click(None)
        else:
            assert not any(getattr(c, "content", None) == "더 보기" for c in walk(ui.controls[0]))
    ui.navigation_bar.on_change(SimpleNamespace(control=SimpleNamespace(selected_index=0)))
    assert any(isinstance(c, ft.Text) and c.value == "최근 기록 20개" for c in walk(ui.controls[0]))
    ui.on_close(None)


def test_pixel_limit_rejected_before_decode(monkeypatch):
    monkeypatch.setattr(photos, "MAX_INPUT_PIXELS", 10)
    with pytest.raises(photos.PhotoError, match="해상도"):
        photos.prepare_photo(png())


def test_pillow_bomb_is_user_error(monkeypatch):
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 10)
    with pytest.raises(photos.PhotoError, match="해상도"):
        photos.prepare_photo(png())


def test_byte_limit(monkeypatch):
    monkeypatch.setattr(photos, "MAX_INPUT_BYTES", 10)
    with pytest.raises(photos.PhotoError, match="20MB"):
        photos.prepare_photo(png())


@pytest.mark.parametrize("save,fail", [(False, False), (True, False), (True, True)])
def test_photo_only_persisted_after_successful_save(ui, tmp_path, save, fail):
    conn = open_database(tmp_path / "form.db")
    repo = BeanRepository(conn)
    if fail:

        def broken(*args, **kwargs):
            raise sqlite3.OperationalError("disk full")

        repo.create = broken

    async def pick():
        return png()

    form = bean_form_view(
        BeanKind.COFFEE,
        None,
        FormDeps(
            repo=repo,
            photo_dir=tmp_path / "photos",
            pick_image=pick,
            notify=lambda _: None,
            confirm=lambda *args: None,
            close=lambda: form.dispose(),
        ),
    )
    name = next(c for c in walk(form) if isinstance(c, ft.TextField) and c.label == "원두 이름 *")
    name.value = "new coffee"
    asyncio.run(button(form, "사진 고르기").on_click(None))
    assert not list(tmp_path.glob("photos/*.jpg"))
    if save:
        button(form, "저장").on_click(None)
    form.dispose()
    assert len(list(tmp_path.glob("photos/*.jpg"))) == int(save and not fail)
    assert len(repo.list_all()) == int(save and not fail)
    conn.close()


def test_picker_finishing_after_navigation_does_not_save(ui, tmp_path):
    conn = open_database(tmp_path / "form.db")

    async def pick():
        form.dispose()
        return png()

    form = bean_form_view(
        BeanKind.COFFEE,
        None,
        FormDeps(
            repo=BeanRepository(conn),
            photo_dir=tmp_path / "photos",
            pick_image=pick,
            notify=lambda _: None,
            confirm=lambda *args: None,
            close=lambda: None,
        ),
    )
    asyncio.run(button(form, "사진 고르기").on_click(None))
    assert not list(tmp_path.glob("photos/*.jpg"))
    conn.close()


def test_legacy_import_preserves_source(monkeypatch, tmp_path):
    from senso.auth import create_account_cli

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr("sys.argv", ["senso.auth", "owner", "--import-legacy"])
    monkeypatch.setattr("getpass.getpass", lambda _: PASSWORD)
    conn = open_database(tmp_path / "senso.db")
    BeanRepository(conn).create(validate_bean(BeanKind.COFFEE, "old record"))
    conn.close()
    photo = photos.save_photo(png(), tmp_path / "photos")
    create_account_cli()
    user = AuthStore(tmp_path).login("owner", PASSWORD)
    conn = open_database(user.directory(tmp_path) / "senso.db")
    assert BeanRepository(conn).list_all()[0].name == "old record"
    conn.close()
    assert (tmp_path / "senso.db").exists()
    assert photos.load_photo(photo, tmp_path / "photos") == photos.load_photo(
        photo, user.directory(tmp_path) / "photos"
    )


def test_failed_photo_replacement_keeps_original(ui, tmp_path):
    conn = open_database(tmp_path / "form.db")
    repo = BeanRepository(conn)
    directory = tmp_path / "photos"
    original = photos.save_photo(png(), directory)
    bean = repo.create(validate_bean(BeanKind.COFFEE, "old"), photo_path=original)

    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("full")

    repo.update = fail

    async def pick():
        return png((20, 40))

    form = bean_form_view(
        BeanKind.COFFEE,
        bean,
        FormDeps(
            repo=repo,
            photo_dir=directory,
            pick_image=pick,
            notify=lambda _: None,
            confirm=lambda *args: None,
            close=lambda: None,
        ),
    )
    asyncio.run(button(form, "사진 바꾸기").on_click(None))
    button(form, "저장").on_click(None)
    assert [p.name for p in directory.iterdir()] == [original]
    assert repo.get(bean.id).photo_path == original
    form.dispose()
    conn.close()


def test_web_picker_cannot_read_server_paths(ui, tmp_path, monkeypatch):
    secret = tmp_path / "server-private.png"
    secret.write_bytes(png())

    async def forged_picker(self, **kwargs):
        return [SimpleNamespace(size=secret.stat().st_size, bytes=None, path=str(secret))]

    monkeypatch.setattr(ft.FilePicker, "pick_files", forged_picker)
    user = AuthStore(tmp_path).register("alice", PASSWORD)
    app.authenticated_main(ui, user)
    button(ui.controls[0], "원두 등록").on_click(None)
    asyncio.run(button(ui.controls[0], "사진 고르기").on_click(None))
    assert button(ui.controls[0], "사진 고르기") is not None
    ui.on_close(None)
