"""앱 조립: DB 열기, 테마 적용, 하단 탭(기록·커피·차·나)과 화면 전환."""

import asyncio
import time
from collections.abc import Callable

import flet as ft

from senso import config
from senso.auth import AuthError, AuthStore, User
from senso.characters.lines import (
    beans_greeting,
    brew_again_line,
    home_greeting,
    recommendation_line,
)
from senso.db.bean_repo import BeanRepository
from senso.db.brew_repo import BrewRepository
from senso.db.database import schema_version
from senso.db.quiz_repo import QuizRepository
from senso.db.recommendation_repo import RecommendationRepository
from senso.db.settings_repo import WORD_ENABLED, SettingsRepository
from senso.db.word_repo import WordCard, WordRepository
from senso.domain.bean import Bean, BeanKind
from senso.domain.brew import Brew, BrewDraft
from senso.export import ExportError, export_account
from senso.photos import MAX_INPUT_BYTES, PhotoError, load_photo
from senso.recommend.apply import draft_from_brew, draft_from_recommendation
from senso.recommend.engine import Recommendation, recommend
from senso.samples import add_samples, remove_samples
from senso.sessions import DataSession
from senso.taste.dna import compute as compute_dna
from senso.taste.quiz import QuizResult
from senso.ui import theme
from senso.ui.components.character import speech_bubble
from senso.ui.components.compare import compare_table, recipe_values
from senso.ui.components.inputs import section
from senso.ui.views.account import account_section, delete_dialog, password_dialog
from senso.ui.views.bean_form import FormDeps, bean_form_view
from senso.ui.views.bean_list import bean_list_view
from senso.ui.views.brew_detail import DetailDeps, brew_detail_view
from senso.ui.views.brew_form import BrewFormDeps, brew_form_view
from senso.ui.views.compare_view import compare_view
from senso.ui.views.home import HomeView, home_view
from senso.ui.views.landing import DESKTOP_WIDTH
from senso.ui.views.login import login_view
from senso.ui.views.me import me_view
from senso.ui.views.quiz_view import QuizDeps, quiz_view
from senso.ui.views.recommend_view import RecommendDeps, recommend_view
from senso.ui.views.word_view import (
    CardDeps,
    PickDeps,
    faith_view,
    word_card_view,
    word_home,
    word_intro,
    word_me_section,
    word_pick_view,
)
from senso.word.moods import MOODS_BY_KEY, find_verse, pick_verse

TABS = [
    (ft.Icons.HOME_OUTLINED, ft.Icons.HOME, "기록"),
    (ft.Icons.COFFEE_OUTLINED, ft.Icons.COFFEE, "커피"),
    (ft.Icons.EMOJI_FOOD_BEVERAGE_OUTLINED, ft.Icons.EMOJI_FOOD_BEVERAGE, "차"),
    (ft.Icons.PERSON_OUTLINE, ft.Icons.PERSON, "나"),
]
TAB_HOME, TAB_COFFEE, TAB_TEA, TAB_ME = range(4)
TAB_KINDS = {TAB_COFFEE: BeanKind.COFFEE, TAB_TEA: BeanKind.TEA}

CONTENT_MAX_WIDTH = 640  # 넓은 화면에서도 폰처럼 가운데 한 줄로
IDLE_MINUTES = 30  # 이 시간 동안 아무것도 하지 않으면 자동 로그아웃
IDLE_CHECK_SECONDS = 30
WRONG_PASSWORD = "아이디 또는 비밀번호를 확인해 주세요."


def main(page: ft.Page, notice: str | None = None) -> None:
    page.title = "SENSO"
    theme.apply(page)

    store = AuthStore(config.data_dir())
    login_view(page, store, lambda user: authenticated_main(page, user, store), notice=notice)


def authenticated_main(page: ft.Page, user: User, store: AuthStore | None = None) -> None:
    store = store or AuthStore(config.data_dir())
    client = getattr(page, "client_ip", None)
    conn = DataSession(store, user)
    directory = store.root / "users" / user.id

    # on_disconnect는 새로고침 등으로 잠깐 끊겨도 불리고 세션은 다시 이어지므로,
    # 세션이 완전히 끝날 때(on_close)만 연결을 닫는다.
    session = {"alive": True, "active_at": time.monotonic(), "changing_password": False}

    def close_session(_) -> None:
        if not session["alive"]:
            return
        session["alive"] = False
        dispose_view()
        conn.close()

    def logout(_=None, notice: str | None = None) -> None:
        close_session(None)
        page.on_keyboard_event = None
        main(page, notice)

    conn.on_revoke = lambda: logout(notice="계정 상태가 변경됐어요. 다시 로그인해 주세요.")

    # ---- 자동 로그아웃 ------------------------------------------------------
    def touch(_=None) -> None:
        with conn.access():
            session["active_at"] = time.monotonic()

    async def watch_idle() -> None:
        while session["alive"]:
            await asyncio.sleep(IDLE_CHECK_SECONDS)
            if not session["alive"]:
                break
            if session["changing_password"]:
                continue
            try:
                store.require_session(conn.user)
            except AuthError:
                conn.on_revoke()
                page.update()
                break
            idle = time.monotonic() - session["active_at"]
            if session["alive"] and idle >= IDLE_MINUTES * 60:
                logout(notice=f"{IDLE_MINUTES}분 동안 사용하지 않아 안전을 위해 로그아웃했어요.")
                page.update()

    page.on_keyboard_event = touch

    page.on_close = close_session
    page.clean()
    page.appbar = ft.AppBar(
        title=ft.Text("SENSO"),
        bgcolor=theme.CREAM,
        actions=[ft.Text(user.username), ft.TextButton("로그아웃", on_click=logout)],
    )
    version = schema_version(conn)
    beans = BeanRepository(conn)
    brews = BrewRepository(conn)
    recommendations = RecommendationRepository(conn)
    quizzes = QuizRepository(conn)
    settings = SettingsRepository(conn)
    words = WordRepository(conn)
    photo_dir = directory / "photos"
    photo_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

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
        if f.size > MAX_INPUT_BYTES:
            raise PhotoError("사진이 너무 커요 (20MB 이하)")
        if f.bytes:
            return f.bytes
        if f.path and not page.web:  # 웹 클라이언트의 경로로 서버 파일을 읽지 않는다
            with open(f.path, "rb") as fh:
                return fh.read(MAX_INPUT_BYTES + 1)
        return None

    async def save_bytes(data: bytes, file_name: str, extension: str, what: str) -> None:
        """웹·폰에서는 내용을 넘겨 내려받게 하고, PC 창에서는 고른 위치에 직접 쓴다."""
        try:
            store.require_session(conn.user)
            if not session["alive"]:
                return
            path = await picker.save_file(
                dialog_title=f"{what} 저장",
                file_name=file_name,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=[extension],
                src_bytes=data,
            )
        except Exception:
            notify(f"{what}를 저장하지 못했어요.")
            return
        if path and not page.web:
            with open(path, "wb") as fh:
                fh.write(data)
        if path or page.web:
            notify(f"{what}를 저장했어요.")

    async def save_png(data: bytes, file_name: str) -> None:
        await save_bytes(data, file_name, "png", "카드 이미지")

    # ---- 계정 관리 ----------------------------------------------------------
    def close_dialog() -> None:
        page.pop_dialog()

    async def change_password(current: str, new: str) -> str | None:
        session["changing_password"] = True
        try:
            renewed = await asyncio.to_thread(
                store.change_password, conn.user, current, new, client
            )
            conn.user = renewed
            conn.revoke_others()
        except AuthError as e:
            return "지금 비밀번호가 맞지 않아요." if str(e) == WRONG_PASSWORD else str(e)
        finally:
            session["changing_password"] = False
        if not session["alive"]:
            return None
        page.pop_dialog()
        notify("비밀번호를 바꿨어요. 다른 기기에서는 다시 로그인해야 해요.")
        return None

    async def export_data() -> None:
        try:
            data = await asyncio.to_thread(export_account, store, conn.user, config.now())
            store.require_session(conn.user)
            if session["alive"]:
                stamp = config.now().strftime("%Y%m%d")
                await save_bytes(data, f"SENSO_내데이터_{stamp}.zip", "zip", "내 데이터")
        except (ExportError, AuthError) as exc:
            notify(str(exc))
        except Exception:
            notify("내보내지 못했어요. 잠시 뒤 다시 시도해 주세요.")

    async def delete_account(password: str) -> str | None:
        try:
            await asyncio.to_thread(store.begin_delete, conn.user, password, client)
        except AuthError as e:
            return "비밀번호가 맞지 않아요." if str(e) == WRONG_PASSWORD else str(e)
        page.pop_dialog()
        conn.revoke_others()
        close_session(None)
        try:
            await asyncio.to_thread(store.finish_delete, user.id)
        except Exception:
            logout(
                notice="계정 접근을 차단했지만 일부 파일을 지우지 못했어요. "
                "관리자에게 삭제 재시도를 요청해 주세요."
            )
            page.update()
            return None
        logout(notice="계정과 모든 기록을 지웠어요. 그동안 함께해 줘서 고마워요.")
        page.update()
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
    frame = ft.Container(content=content, width=CONTENT_MAX_WIDTH)
    scroller = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[frame],
    )

    attached = {"scroller": False}

    def dispose_view() -> None:
        if hasattr(content.content, "dispose"):
            content.content.dispose()

    def show(control: ft.Control, *, scroll_to_top: bool = True) -> None:
        """화면을 바꾸고, 새 화면은 맨 위에서 시작한다."""
        touch()
        dispose_view()
        frame.width = DESKTOP_WIDTH if isinstance(control, HomeView) else CONTENT_MAX_WIDTH
        content.content = control
        if isinstance(control, HomeView):
            control.adapt(getattr(page, "width", None) or DESKTOP_WIDTH)
        page.update()
        # scroller는 page.add() 이후에만 화면에 붙어 있다 (그 전에는 .page 접근이 오류)
        if attached["scroller"] and scroll_to_top:
            page.run_task(scroller.scroll_to, offset=0, duration=0)

    def resize_home(_) -> None:
        if isinstance(content.content, HomeView):
            content.content.adapt(getattr(page, "width", None) or DESKTOP_WIDTH)
            page.update()

    page.on_resize = resize_home

    # ---- 화면 만들기 ------------------------------------------------------
    home_limit = 20
    home_kind: BeanKind | None = None

    def filter_home(kind: BeanKind | None) -> None:
        nonlocal home_kind, home_limit
        home_kind, home_limit = kind, 20
        show(build_tab(TAB_HOME))

    def repeat_brew(brew: Brew) -> None:
        open_brew_form(
            prefill=draft_from_brew(brew),
            banner=ft.Text("최근 레시피를 불러왔어요. 맛 평가는 새로 남겨주세요."),
        )

    def more_home() -> None:
        nonlocal home_limit
        home_limit += 20
        show(build_tab(TAB_HOME), scroll_to_top=False)

    def open_tab(index: int) -> None:
        nonlocal home_limit, home_kind
        home_limit, home_kind = 20, None
        nav.selected_index = index
        show(build_tab(index))

    def open_bean_form(kind: BeanKind, bean: Bean | None = None) -> None:
        tab = TAB_COFFEE if kind is BeanKind.COFFEE else TAB_TEA
        deps = FormDeps(
            repo=beans,
            access=conn.access,
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

    # ---- 오늘의 말씀 한 잔 ------------------------------------------------
    def set_word_enabled(on: bool, back_tab: int) -> None:
        settings.set_flag(WORD_ENABLED, on)
        if on:
            notify("오늘의 말씀 한 잔을 켰어요.")
        else:
            notify("말씀 한 잔은 꺼 둘게요. '나' 탭에서 언제든 켤 수 있어요.")
        open_tab(back_tab)

    def word_top() -> list[ft.Control]:
        enabled = settings.get_flag(WORD_ENABLED)
        if enabled is None:
            return [
                word_intro(
                    on_enable=lambda: set_word_enabled(True, TAB_HOME),
                    on_decline=lambda: set_word_enabled(False, TAB_HOME),
                )
            ]
        if not enabled:
            return []
        today = words.for_day(config.now().date())
        return [word_home(today, on_pick=open_word_pick, on_open=lambda c: open_word_card(c))]

    def open_word_pick(back: Callable[[], None] | None = None) -> None:
        """기분 고르기. 오늘 이미 받았어도 다시 고를 수 있다 (새 카드가 그날의 카드가 됨)."""
        back = back or (lambda: open_tab(TAB_HOME))

        def picked(mood_key: str, note: str | None) -> None:
            # 적은 한 줄은 마음 건강과 관련된 민감한 내용일 수 있어 저장하지 않는다.
            # 위기 신호 확인(화면 안)에만 쓰고 버린다.
            del note
            now = config.now()
            mood = MOODS_BY_KEY[mood_key]
            verse = pick_verse(mood, now.date())
            open_word_card(words.create(now.date(), mood_key, verse.ref, None, now))

        nav.selected_index = TAB_HOME
        show(word_pick_view(PickDeps(on_back=back, on_pick=picked)))

    def open_word_card(card: WordCard, back_tab: int = TAB_HOME) -> None:
        found = find_verse(card.mood, card.verse_ref)
        if found is None:
            notify("이 말씀 카드를 열 수 없어요.")
            open_tab(back_tab)
            return
        mood, verse = found
        nav.selected_index = back_tab
        show(
            word_card_view(
                card,
                mood,
                verse,
                CardDeps(
                    on_back=lambda: open_tab(back_tab),
                    set_saved=words.set_saved,
                    save_png=save_png,
                    on_faith=lambda: open_faith(lambda: open_word_card(card, back_tab)),
                    notify=notify,
                    on_repick=lambda: open_word_pick(back=lambda: open_word_card(card, back_tab)),
                ),
            )
        )

    def open_faith(back: Callable[[], None]) -> None:
        show(faith_view(back))

    def build_tab(index: int) -> ft.Control:
        if index == TAB_HOME:
            all_brews = brews.list(limit=home_limit + 1, kind=home_kind)
            has_more = len(all_brews) > home_limit
            all_brews = all_brews[:home_limit]
            top: list[ft.Control] = [speech_bubble(home_greeting(config.now(), brews.count()))]
            top += word_top()
            bottom: list[ft.Control] = []
            if brews.count() == 0:
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
            latest = brews.list(limit=1)
            return home_view(
                all_brews,
                on_new=open_brew_form,
                on_add_coffee=lambda: open_bean_form(BeanKind.COFFEE),
                on_open=lambda b: open_brew_detail(b.id),
                top=top,
                bottom=bottom,
                on_more=more_home if has_more else None,
                kind=home_kind,
                on_filter=filter_home,
                latest=latest[0] if latest else None,
                on_repeat=repeat_brew,
                rated_count=brews.rated_count(),
                on_taste=lambda: open_tab(TAB_ME),
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
            word_section=word_me_section(
                enabled=bool(settings.get_flag(WORD_ENABLED)),
                notes=words.saved(),
                on_toggle=lambda on: set_word_enabled(on, TAB_ME),
                on_open=lambda c: open_word_card(c, TAB_ME),
                on_faith=lambda: open_faith(lambda: open_tab(TAB_ME)),
            ),
            account_section=account_section(
                user.username,
                IDLE_MINUTES,
                on_password=lambda: page.show_dialog(
                    password_dialog(change_password, close_dialog)
                ),
                on_export=export_data,
                on_delete=lambda: page.show_dialog(
                    delete_dialog(user.username, delete_account, close_dialog)
                ),
            ),
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
    page.run_task(watch_idle)
