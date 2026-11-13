"""앱 조립: DB 열기, 테마 적용, 하단 탭(기록·커피·차·나)과 화면 전환."""

from collections.abc import Callable

import flet as ft

from senso import config
from senso.db.bean_repo import BeanRepository
from senso.db.brew_repo import BrewRepository
from senso.db.database import open_database, schema_version
from senso.domain.bean import Bean, BeanKind
from senso.domain.brew import Brew, BrewDraft
from senso.photos import load_photo
from senso.recommend.engine import recommend
from senso.samples import add_samples, remove_samples
from senso.ui import theme
from senso.ui.views.bean_form import FormDeps, bean_form_view
from senso.ui.views.bean_list import bean_list_view
from senso.ui.views.brew_detail import DetailDeps, brew_detail_view
from senso.ui.views.brew_form import BrewFormDeps, brew_form_view
from senso.ui.views.home import home_view
from senso.ui.views.me import me_view
from senso.ui.views.recommend_view import RecommendDeps, recommend_view

TABS = [
    (ft.Icons.HOME_OUTLINED, ft.Icons.HOME, "기록"),
    (ft.Icons.COFFEE_OUTLINED, ft.Icons.COFFEE, "커피"),
    (ft.Icons.EMOJI_FOOD_BEVERAGE_OUTLINED, ft.Icons.EMOJI_FOOD_BEVERAGE, "차"),
    (ft.Icons.PERSON_OUTLINE, ft.Icons.PERSON, "나"),
]
TAB_HOME, TAB_COFFEE, TAB_TEA, TAB_ME = range(4)
TAB_KINDS = {TAB_COFFEE: BeanKind.COFFEE, TAB_TEA: BeanKind.TEA}

CONTENT_MAX_WIDTH = 640  # 넓은 화면에서도 폰처럼 가운데 한 줄로


def main(page: ft.Page) -> None:
    page.title = "SENSO"
    theme.apply(page)

    # 웹 모드에서는 브라우저 탭마다 main()이 따로 실행되므로 연결도 탭마다 연다.
    conn = open_database(config.db_path())
    # on_disconnect는 새로고침 등으로 잠깐 끊겨도 불리고 세션은 다시 이어지므로,
    # 세션이 완전히 끝날 때(on_close)만 연결을 닫는다.
    page.on_close = lambda _: conn.close()
    version = schema_version(conn)
    beans = BeanRepository(conn)
    brews = BrewRepository(conn)
    photo_dir = config.photos_dir()

    picker = ft.FilePicker()  # 페이지에 서비스로 등록된다

    async def pick_image() -> bytes | None:
        files = await picker.pick_files(
            dialog_title="사진 고르기",
            file_type=ft.FilePickerFileType.IMAGE,
            with_data=True,  # 웹·폰에서는 파일 경로 대신 내용을 받는다
        )
        if not files:
            return None
        f = files[0]
        if f.bytes:
            return f.bytes
        if f.path:  # 데스크톱 실행
            with open(f.path, "rb") as fh:
                return fh.read()
        return None

    def notify(message: str) -> None:
        page.show_dialog(ft.SnackBar(message))

    def confirm(title: str, message: str, ok_label: str, on_ok) -> None:
        def ok(_):
            page.pop_dialog()
            on_ok()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(title),
                content=ft.Text(message),
                actions=[
                    ft.TextButton("취소", on_click=lambda _: page.pop_dialog()),
                    ft.FilledButton(
                        ok_label,
                        style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700),
                        on_click=ok,
                    ),
                ],
            )
        )

    content = ft.Container(padding=ft.Padding.symmetric(horizontal=20, vertical=16))

    def show(control: ft.Control) -> None:
        content.content = control
        page.update()

    # ---- 화면 만들기 ------------------------------------------------------
    def open_tab(index: int) -> None:
        nav.selected_index = index
        show(build_tab(index))

    def open_bean_form(kind: BeanKind, bean: Bean | None = None) -> None:
        tab = TAB_COFFEE if kind is BeanKind.COFFEE else TAB_TEA
        deps = FormDeps(
            repo=beans,
            photo_dir=photo_dir,
            pick_image=pick_image,
            notify=notify,
            confirm=confirm,
            close=lambda: open_tab(tab),
        )
        nav.selected_index = tab
        show(bean_form_view(kind, bean, deps))

    def brew_deps(back: Callable[[], None]) -> BrewFormDeps:
        return BrewFormDeps(
            beans=beans,
            brews=brews,
            now=config.now,
            notify=notify,
            on_saved=lambda brew: open_brew_detail(brew.id),
            on_cancel=back,
            on_add_bean=lambda: open_bean_form(BeanKind.COFFEE),
        )

    def open_brew_form(
        editing: Brew | None = None,
        prefill: BrewDraft | None = None,
        banner: ft.Control | None = None,
        back: Callable[[], None] | None = None,
    ) -> None:
        if back is None:
            back = (
                (lambda: open_brew_detail(editing.id)) if editing else (lambda: open_tab(TAB_HOME))
            )
        nav.selected_index = TAB_HOME
        show(brew_form_view(brew_deps(back), editing=editing, prefill=prefill, banner=banner))

    def open_brew_detail(brew_id: int) -> None:
        brew = brews.get(brew_id)
        if brew is None:
            notify("기록을 찾을 수 없어요.")
            open_tab(TAB_HOME)
            return
        nav.selected_index = TAB_HOME
        show(
            brew_detail_view(
                brew,
                DetailDeps(
                    brews=brews,
                    notify=notify,
                    confirm=confirm,
                    on_back=lambda: open_tab(TAB_HOME),
                    on_edit=lambda b: open_brew_form(editing=b),
                    on_open=open_brew_detail,
                    on_deleted=lambda: open_tab(TAB_HOME),
                    on_recommend=lambda b: open_recommendation(b.id),
                ),
            )
        )

    def open_recommendation(brew_id: int) -> None:
        brew = brews.get(brew_id)
        if brew is None:
            open_tab(TAB_HOME)
            return
        nav.selected_index = TAB_HOME
        show(
            recommend_view(
                brew,
                recommend(brew),
                RecommendDeps(
                    on_back=lambda: open_brew_detail(brew_id),
                    on_edit=lambda b: open_brew_form(
                        editing=b, back=lambda: open_recommendation(brew_id)
                    ),
                ),
            )
        )

    def on_add_samples() -> None:
        count = add_samples(beans, brews, config.now())
        notify(f"예시 기록 {count}개를 넣었어요. 카드에 '예시' 표시가 붙어 있어요.")
        open_tab(TAB_HOME)

    def on_remove_samples() -> None:
        def really() -> None:
            count = remove_samples(beans, brews)
            notify(f"예시 기록 {count}개를 지웠어요. 직접 남긴 기록은 그대로예요.")
            open_tab(TAB_HOME)

        confirm(
            "예시 데이터를 지울까요?",
            "'예시' 표시가 붙은 기록과 원두·차만 지워요.\n직접 남긴 기록은 그대로 남아요.",
            "지우기",
            really,
        )

    def build_tab(index: int) -> ft.Control:
        if index == TAB_HOME:
            all_brews = brews.list()
            top: list[ft.Control] = []
            bottom: list[ft.Control] = []
            if not all_brews:
                bottom.append(
                    ft.TextButton(
                        "예시 기록으로 둘러보기",
                        icon=ft.Icons.TOUR_OUTLINED,
                        on_click=lambda _: on_add_samples(),
                    )
                )
            elif brews.has_samples():
                bottom.append(
                    ft.TextButton(
                        "예시 데이터 지우기",
                        icon=ft.Icons.CLEANING_SERVICES_OUTLINED,
                        on_click=lambda _: on_remove_samples(),
                    )
                )
            return home_view(
                all_brews,
                on_new=open_brew_form,
                on_add_coffee=lambda: open_bean_form(BeanKind.COFFEE),
                on_open=lambda b: open_brew_detail(b.id),
                top=top,
                bottom=bottom,
            )
        if index in TAB_KINDS:
            kind = TAB_KINDS[index]
            return bean_list_view(
                kind,
                beans.list(kind),
                load_photo=lambda name: load_photo(name, photo_dir),
                on_add=lambda: open_bean_form(kind),
                on_open=lambda b: open_bean_form(kind, b),
            )
        return me_view(version)

    nav = ft.NavigationBar(
        bgcolor=theme.CREAM,
        indicator_color=theme.IVORY,
        destinations=[
            ft.NavigationBarDestination(icon=icon, selected_icon=selected, label=label)
            for icon, selected, label in TABS
        ],
        on_change=lambda e: open_tab(e.control.selected_index),
    )
    page.navigation_bar = nav
    page.add(
        ft.SafeArea(
            expand=True,
            content=ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[ft.Container(content=content, max_width=CONTENT_MAX_WIDTH)],
            ),
        )
    )
    open_tab(TAB_HOME)
