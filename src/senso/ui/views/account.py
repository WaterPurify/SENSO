"""'나' 탭의 계정 관리: 비밀번호 바꾸기, 내 데이터 내보내기, 계정 삭제."""

from collections.abc import Awaitable, Callable

import flet as ft

from senso.ui import theme
from senso.ui.components.inputs import section

# 제출 함수는 오류 문구를 돌려준다. 성공하면 None (창 닫기는 앱이 한다)
Submit = Callable[..., Awaitable[str | None]]


def account_section(
    username: str,
    idle_minutes: int,
    on_password: Callable[[], None],
    on_export: Callable[[], Awaitable[None]],
    on_delete: Callable[[], None],
) -> ft.Control:
    async def export(_: ft.Event) -> None:
        if export_button.disabled:
            return
        export_button.disabled = True
        export_button.content = "내보내는 중…"
        export_button.update()
        try:
            await on_export()
        finally:
            export_button.disabled = False
            export_button.content = "내 데이터 내보내기 (ZIP)"
            try:
                export_button.update()
            except RuntimeError:
                pass  # The user may have navigated away while the worker ran.

    export_button = ft.OutlinedButton(
        "내 데이터 내보내기 (ZIP)", icon=ft.Icons.DOWNLOAD, on_click=export
    )

    return section(
        "계정",
        f"{username} · {idle_minutes}분 동안 쓰지 않으면 자동으로 로그아웃돼요",
        [
            ft.OutlinedButton(
                "비밀번호 바꾸기", icon=ft.Icons.LOCK_RESET, on_click=lambda _: on_password()
            ),
            export_button,
            ft.Text(
                "기록·말씀 카드·설정(JSON)과 사진을 한 파일로 받아요.",
                size=12,
                color=theme.TEXT_MUTED,
            ),
            ft.TextButton(
                "계정 삭제",
                icon=ft.Icons.DELETE_FOREVER_OUTLINED,
                style=ft.ButtonStyle(color=ft.Colors.RED_700),
                on_click=lambda _: on_delete(),
            ),
        ],
    )


def _password_field(label: str) -> ft.TextField:
    return ft.TextField(label=label, password=True, can_reveal_password=True, max_length=128)


def _dialog(
    title: str,
    fields: list[ft.Control],
    ok_label: str,
    run: Callable[[], Awaitable[str | None]],
    on_close: Callable[[], None],
    danger: bool = False,
) -> ft.AlertDialog:
    message = ft.Text(color=ft.Colors.RED_700)
    state = {"busy": False}

    async def submit(_: ft.Event) -> None:
        if state["busy"]:
            return
        state["busy"] = True
        ok.disabled = True
        cancel.disabled = True
        message.value = "확인 중이에요."
        dialog.update()
        try:
            error = await run()
        except Exception:
            error = "처리하지 못했어요. 잠시 뒤 다시 시도해 주세요."
        finally:
            state["busy"] = False
        if error:
            message.value = error
            ok.disabled = False
            cancel.disabled = False
            dialog.update()

    ok = ft.FilledButton(
        ok_label,
        style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700) if danger else None,
        on_click=submit,
    )
    cancel = ft.TextButton("취소", on_click=lambda _: on_close())
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Column(tight=True, width=340, controls=[*fields, message]),
        actions=[cancel, ok],
    )
    return dialog


def password_dialog(
    on_submit: Callable[[str, str], Awaitable[str | None]], on_close: Callable[[], None]
) -> ft.AlertDialog:
    current = _password_field("지금 비밀번호")
    new = _password_field("새 비밀번호 (12~128자)")
    repeat = _password_field("새 비밀번호 확인")

    async def run() -> str | None:
        if (new.value or "") != (repeat.value or ""):
            return "새 비밀번호 확인이 일치하지 않아요."
        try:
            return await on_submit(current.value or "", new.value or "")
        finally:
            current.value = new.value = repeat.value = ""

    hint = ft.Text(
        "흔한 낱말이나 1234 같은 이어진 글자 대신, 여러 낱말을 섞은 문장처럼 만들어 주세요.",
        size=12,
        color=theme.TEXT_MUTED,
    )
    return _dialog("비밀번호 바꾸기", [current, new, repeat, hint], "바꾸기", run, on_close)


def delete_dialog(
    username: str,
    on_submit: Callable[[str], Awaitable[str | None]],
    on_close: Callable[[], None],
) -> ft.AlertDialog:
    confirm = ft.TextField(label=f"아이디 입력 ({username})")
    password = _password_field("비밀번호")

    async def run() -> str | None:
        if (confirm.value or "").strip().lower() != username:
            return "아이디가 일치하지 않아요."
        try:
            return await on_submit(password.value or "")
        finally:
            password.value = ""

    warning = ft.Text(
        "원두·차, 추출 기록, 취향 테스트, 말씀 카드, 사진이 모두 지워지고 되돌릴 수 없어요. "
        "필요하면 먼저 '내 데이터 내보내기'로 받아 두세요.",
        color=theme.BROWN,
    )
    return _dialog(
        "계정을 삭제할까요?", [warning, confirm, password], "영구 삭제", run, on_close, danger=True
    )
