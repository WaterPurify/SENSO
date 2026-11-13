"""앱 조립: DB 열기, 테마 적용, 하단 탭 전환."""

import flet as ft

from senso import config
from senso.db.database import open_database, schema_version
from senso.ui import theme
from senso.ui.views.beans import beans_view
from senso.ui.views.home import home_view
from senso.ui.views.me import me_view

TABS = [
    (ft.Icons.HOME_OUTLINED, ft.Icons.HOME, "기록"),
    (ft.Icons.COFFEE_OUTLINED, ft.Icons.COFFEE, "원두·차"),
    (ft.Icons.PERSON_OUTLINE, ft.Icons.PERSON, "나"),
]


def main(page: ft.Page) -> None:
    page.title = "SENSO"
    theme.apply(page)

    # 웹 모드에서는 브라우저 탭마다 main()이 따로 실행되므로 연결도 탭마다 연다.
    conn = open_database(config.db_path())
    page.on_disconnect = lambda _: conn.close()
    version = schema_version(conn)

    def show_not_ready(feature: str) -> None:
        page.show_dialog(ft.SnackBar(f"'{feature}' 기능은 곧 만들어질 예정이에요."))

    def build_tab(index: int) -> ft.Control:
        if index == 0:
            return home_view(show_not_ready)
        if index == 1:
            return beans_view()
        return me_view(version)

    body = ft.Container(
        content=build_tab(0),
        padding=ft.Padding.symmetric(horizontal=20, vertical=16),
    )

    def on_tab_change(e: ft.Event[ft.NavigationBar]) -> None:
        body.content = build_tab(e.control.selected_index)
        page.update()

    page.navigation_bar = ft.NavigationBar(
        bgcolor=theme.CREAM,
        indicator_color=theme.IVORY,
        destinations=[
            ft.NavigationBarDestination(icon=icon, selected_icon=selected, label=label)
            for icon, selected, label in TABS
        ],
        on_change=on_tab_change,
    )
    page.add(
        ft.SafeArea(
            expand=True,
            content=ft.Column([body], scroll=ft.ScrollMode.AUTO, expand=True),
        )
    )
