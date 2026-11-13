"""앱 조립: DB 열기, 테마 적용, 하단 탭(기록·커피·차·나)과 화면 전환."""

from collections.abc import Callable

import flet as ft

from senso import config
from senso.characters.lines import (
    beans_greeting,
    brew_again_line,
    home_greeting,
    recommendation_line,
)
from senso.db.bean_repo import BeanRepository
from senso.db.brew_repo import BrewRepository
from senso.db.database import open_database, schema_version
from senso.db.quiz_repo import QuizRepository
from senso.db.recommendation_repo import RecommendationRepository
from senso.domain.bean import Bean, BeanKind
from senso.domain.brew import Brew, BrewDraft
from senso.photos import load_photo
from senso.recommend.apply import draft_from_recommendation
from senso.recommend.engine import Recommendation, recommend
from senso.samples import add_samples, remove_samples
from senso.taste.dna import compute as compute_dna
from senso.taste.quiz import QuizResult
from senso.ui import theme
from senso.ui.components.character import speech_bubble
from senso.ui.components.compare import compare_table, recipe_values
from senso.ui.components.inputs import section
from senso.ui.views.bean_form import FormDeps, bean_form_view
from senso.ui.views.bean_list import bean_list_view
from senso.ui.views.brew_detail import DetailDeps, brew_detail_view
from senso.ui.views.brew_form import BrewFormDeps, brew_form_view
from senso.ui.views.compare_view import compare_view
from senso.ui.views.home import home_view
from senso.ui.views.me import me_view
from senso.ui.views.quiz_view import QuizDeps, quiz_view
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
    recommendations = RecommendationRepository(conn)
    quizzes = QuizRepository(conn)
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

    async def save_png(data: bytes, file_name: str) -> None:
        """웹·폰에서는 내용을 넘겨 내려받게 하고, PC 창에서는 고른 위치에 직접 쓴다."""
        try:
            path = await picker.save_file(
                dialog_title="카드 이미지 저장",
                file_name=file_name,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["png"],
                src_bytes=data,
            )
        except Exception:
            notify("이미지를 저장하지 못했어요.")
            return
        if path and not page.web:
            with open(path, "wb") as fh:
                fh.write(data)
        if path or page.web:
            notify("카드 이미지를 저장했어요.")

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
    scroller = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[ft.Container(content=content, max_width=CONTENT_MAX_WIDTH)],
    )

    attached = {"scroller": False}

    def show(control: ft.Control) -> None:
        """화면을 바꾸고, 새 화면은 맨 위에서 시작한다."""
        content.content = control
        page.update()
        # scroller는 page.add() 이후에만 화면에 붙어 있다 (그 전에는 .page 접근이 오류)
        if attached["scroller"]:
            page.run_task(scroller.scroll_to, offset=0, duration=0)

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
                    on_compare=open_compare,
                ),
            )
        )

    def open_recommendation(brew_id: int) -> None:
        brew = brews.get(brew_id)
        if brew is None:
            open_tab(TAB_HOME)
            return
        nav.selected_index = TAB_HOME

        def bubble(b: Brew, result) -> list[ft.Control]:
            return [speech_bubble(recommendation_line(b.kind, result))]

        def recipe_compare(b: Brew, result) -> list[ft.Control]:
            if not isinstance(result, Recommendation):
                return []
            overrides = {}
            if result.direction_only:
                overrides[result.field_label] = f"{result.to_value}"
            return [
                section(
                    "지금 레시피와 비교",
                    "노란 칸만 바꿔요",
                    [
                        compare_table(
                            "지금",
                            "제안",
                            recipe_values(b.recipe, b.kind, b.iced),
                            recipe_values(result.new_recipe, b.kind, b.iced),
                            overrides=overrides,
                        )
                    ],
                )
            ]

        show(
            recommend_view(
                brew,
                recommend(brew),
                RecommendDeps(
                    on_back=lambda: open_brew_detail(brew_id),
                    on_edit=lambda b: open_brew_form(
                        editing=b, back=lambda: open_recommendation(brew_id)
                    ),
                    on_brew_again=brew_again,
                    extra_top=bubble,
                    extra_bottom=recipe_compare,
                ),
            )
        )

    def brew_again(brew: Brew, rec: Recommendation) -> None:
        saved = recommendations.save(brew.id, rec)
        open_brew_form(
            prefill=draft_from_recommendation(brew, rec, saved.id),
            banner=speech_bubble(brew_again_line(brew.kind, rec)),
            back=lambda: open_recommendation(brew.id),
        )

    def open_compare(before_id: int, after_id: int) -> None:
        before, after = brews.get(before_id), brews.get(after_id)
        if before is None or after is None:
            notify("비교할 기록을 찾을 수 없어요.")
            return
        nav.selected_index = TAB_HOME
        show(compare_view(before, after, on_back=lambda: open_brew_detail(after_id)))

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
            top: list[ft.Control] = [speech_bubble(home_greeting(config.now(), len(all_brews)))]
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
            items = beans.list(kind)
            return bean_list_view(
                kind,
                items,
                load_photo=lambda name: load_photo(name, photo_dir),
                on_add=lambda: open_bean_form(kind),
                on_open=lambda b: open_bean_form(kind, b),
                top=[speech_bubble(beans_greeting(kind, len(items)))],
            )
        return me_view(
            version,
            quizzes.latest(),
            compute_dna(brews.list()),
            on_quiz=open_quiz,
            on_open=lambda b: open_brew_detail(b.id),
        )

    def open_quiz() -> None:
        def done(answers: list[int], result: QuizResult) -> None:
            quizzes.save(answers, result.type.code, config.now())

        nav.selected_index = TAB_ME
        show(
            quiz_view(QuizDeps(on_done=done, on_close=lambda: open_tab(TAB_ME), save_png=save_png))
        )

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
    page.add(ft.SafeArea(expand=True, content=scroller))
    attached["scroller"] = True
    open_tab(TAB_HOME)
