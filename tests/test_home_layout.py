from dataclasses import replace
from datetime import datetime
from types import SimpleNamespace

import flet as ft
import pytest

from senso import app, config
from senso.auth import AuthStore
from senso.db.bean_repo import BeanRepository
from senso.db.brew_repo import BrewRepository
from senso.db.database import open_database
from senso.domain.bean import BeanKind, validate_bean
from senso.domain.brew import Tasting, validate_brew
from senso.recommend.apply import draft_from_brew
from senso.ui.views.home import HomeView
from test_security_and_ui import PASSWORD, Page, button, walk


@pytest.fixture
def ui(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(ft.Control, "update", lambda self: None)
    return Page()


def seed(root):
    user = AuthStore(root).register("layout_user", PASSWORD)
    conn = open_database(user.directory(root) / "senso.db")
    beans, brews = BeanRepository(conn), BrewRepository(conn)
    coffee = beans.create(validate_bean(BeanKind.COFFEE, "Coffee"))
    tea = beans.create(validate_bean(BeanKind.TEA, "Tea"))
    for n in range(45):
        bean = tea if n < 24 else coffee
        draft = validate_brew(bean=bean, bean_id=bean.id, dose_g="15", water_g="250")
        brews.create(draft, datetime(2026, 11, 14, 9, n))
    return user, conn


def test_filter_before_limit_and_more(ui, tmp_path):
    user, conn = seed(tmp_path)
    repo = BrewRepository(conn)
    assert len(repo.list(limit=21, kind=BeanKind.TEA)) == 21
    assert all(b.kind is BeanKind.TEA for b in repo.list(limit=21, kind=BeanKind.TEA))
    app.authenticated_main(ui, user)
    button(ui.controls[0], "차").on_click(None)

    def texts():
        return [c.value for c in walk(ui.controls[0]) if isinstance(c, ft.Text)]

    assert "최근 기록 20개" in texts()
    button(ui.controls[0], "더 보기").on_click(None)
    assert "최근 기록 24개" in texts()
    button(ui.controls[0], "커피").on_click(None)
    assert "최근 기록 20개" in texts()
    assert "Tea" not in texts()
    ui.on_close(None)
    conn.close()


def test_repeat_clears_tasting_and_recommendation(tmp_path):
    _, conn = seed(tmp_path)
    brew = BrewRepository(conn).list(limit=1)[0]
    brew = replace(
        brew,
        tasting=Tasting(satisfaction=5, notes="old tasting"),
        based_on_rec_id=7,
        notes="old note",
    )
    draft = draft_from_brew(brew)
    assert draft.recipe == brew.recipe and draft.bean == brew.bean
    assert draft.based_on_brew_id == brew.id
    assert draft.based_on_rec_id is None
    assert draft.tasting.is_empty and draft.notes is None
    conn.close()


def test_taste_count_excludes_samples_and_unrated(tmp_path):
    _, conn = seed(tmp_path)
    repo = BrewRepository(conn)
    assert repo.rated_count() == 0
    conn.execute("UPDATE brews SET satisfaction = 4 WHERE id IN (1,2)")
    conn.execute("UPDATE brews SET is_sample = 1 WHERE id = 2")
    conn.commit()
    assert repo.rated_count() == 1
    conn.close()


def test_landing_signup_and_read_only_example(ui, tmp_path):
    app.main(ui)
    button(ui.controls[0], "예시 기록 둘러보기").on_click(None)
    assert "예시" in ui.dialog.title.value
    assert not (tmp_path / "users").exists()
    button(ui.dialog, "닫기").on_click(None)
    button(ui.controls[0], "무료로 시작하기").on_click(None)
    fields = [c for c in walk(ui.dialog) if isinstance(c, ft.TextField)]
    assert fields[2].visible and ui.dialog.title.value == "회원가입"
    assert not (tmp_path / "users").exists()
    button(ui.dialog, "취소").on_click(None)
    button(ui.appbar, "로그인").on_click(None)
    assert ui.dialog.title.value == "로그인"
    assert not fields[2].visible


def test_mobile_actions_repeat_and_form_width(ui, tmp_path):
    user, conn = seed(tmp_path)
    ui.width = 390
    app.authenticated_main(ui, user)
    home = next(c for c in walk(ui.controls[0]) if isinstance(c, HomeView))
    assert home.mobile_actions.visible and not home.desktop_actions.visible
    ui.width = 1360
    ui.on_resize(None)
    assert not home.mobile_actions.visible and home.desktop_actions.visible
    button(home.desktop_actions, "최근 레시피로 다시 추출").on_click(None)
    assert not any(isinstance(c, HomeView) for c in walk(ui.controls[0]))
    assert any(isinstance(c, ft.Container) and c.width == 640 for c in walk(ui.controls[0]))
    ui.navigation_bar.on_change(SimpleNamespace(control=SimpleNamespace(selected_index=0)))
    assert any(isinstance(c, HomeView) for c in walk(ui.controls[0]))
    ui.on_close(None)
    conn.close()
