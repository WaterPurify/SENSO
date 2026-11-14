"""개인 데이터를 열기 전의 로그인·회원가입 화면."""

import asyncio
from collections.abc import Callable

import flet as ft

from senso.auth import AuthError, AuthStore, User
from senso.ui import theme


def login_view(page: ft.Page, store: AuthStore, on_login: Callable[[User], None]) -> None:
    page.clean()
    page.navigation_bar = None
    state = {"alive": True, "signup": False, "busy": False, "attempts": 0}
    username = ft.TextField(label="아이디", max_length=32, autofocus=True)
    password = ft.TextField(
        label="비밀번호", password=True, can_reveal_password=True, max_length=128
    )
    repeat = ft.TextField(label="비밀번호 확인", password=True, max_length=128, visible=False)
    message = ft.Text(color=ft.Colors.RED_700)
    title = ft.Text("로그인", size=theme.HEADING_SIZE, weight=ft.FontWeight.BOLD)

    def close_session(_) -> None:
        state["alive"] = False
        password.value = repeat.value = ""

    page.on_close = close_session

    def open_dialog(_) -> None:
        if not state["busy"]:
            page.show_dialog(dialog)

    def cancel(_) -> None:
        if not state["busy"]:
            password.value = repeat.value = ""
            page.pop_dialog()

    def toggle(_) -> None:
        if state["busy"]:
            return
        state["signup"] = not state["signup"]
        repeat.visible = state["signup"]
        title.value = submit.content = "회원가입" if state["signup"] else "로그인"
        switch.content = "이미 계정이 있어요" if state["signup"] else "회원가입"
        password.value = repeat.value = ""
        message.value = "비밀번호는 12~128자로 입력해 주세요." if state["signup"] else ""
        page.update()

    async def authenticate(_) -> None:
        if state["busy"] or not state["alive"]:
            return
        if state["signup"] and password.value != repeat.value:
            message.value = "비밀번호 확인이 일치하지 않아요."
            page.update()
            return
        state["busy"] = True
        submit.disabled = switch.disabled = True
        message.value = "확인 중이에요."
        page.update()
        name, secret = username.value or "", password.value or ""
        try:
            # 계정별 제한 외에도 한 세션의 연속 요청을 늦춘다.
            if state["attempts"]:
                await asyncio.sleep(min(state["attempts"], 5))
            action = store.register if state["signup"] else store.login
            user = await asyncio.to_thread(action, name, secret)
        except AuthError as e:
            state["attempts"] += 1
            message.value = str(e)
        except Exception:
            message.value = "로그인할 수 없어요. 잠시 후 다시 시도해 주세요."
        else:
            if state["alive"]:
                state["alive"] = False
                password.value = repeat.value = ""
                page.pop_dialog()
                on_login(user)
                return
        finally:
            secret = ""
            state["busy"] = False
        if state["alive"]:
            password.value = repeat.value = ""
            submit.disabled = switch.disabled = False
            page.update()

    submit = ft.FilledButton("로그인", on_click=authenticate)
    switch = ft.TextButton("회원가입", on_click=toggle)
    password.on_submit = authenticate
    repeat.on_submit = authenticate
    dialog = ft.AlertDialog(
        modal=True,
        title=title,
        content=ft.Column(tight=True, width=340, controls=[username, password, repeat, message]),
        actions=[ft.TextButton("취소", on_click=cancel), switch, submit],
    )
    page.appbar = ft.AppBar(
        title=ft.Text("SENSO"),
        bgcolor=theme.CREAM,
        actions=[ft.TextButton("로그인", icon=ft.Icons.LOGIN, on_click=open_dialog)],
    )
    page.add(
        ft.SafeArea(
            content=ft.Container(
                padding=24,
                content=ft.Column(
                    controls=[
                        ft.Text("나만의 한 잔을 기록해 보세요", size=theme.TITLE_SIZE),
                        ft.Text("로그인하면 내 커피·차 기록과 사진을 볼 수 있어요."),
                        ft.Text("처음이라면 오른쪽 위 로그인에서 회원가입을 해 주세요."),
                    ]
                ),
            )
        )
    )
