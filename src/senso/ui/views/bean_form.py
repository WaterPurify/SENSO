"""원두·차 등록과 수정 화면."""

from collections.abc import Awaitable, Callable
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path

import flet as ft

from senso.db.bean_repo import BeanRepository
from senso.domain.bean import (
    LABELS,
    NAME_MAX,
    ORIGIN_MAX,
    PRODUCER_MAX,
    ROAST_LEVELS,
    TEA_TYPES,
    Bean,
    BeanKind,
    BeanValidationError,
    validate_bean,
)
from senso.origin import country_of
from senso.photos import PhotoError, delete_photo, load_photo, prepare_photo, save_prepared_photo
from senso.text import josa, quote
from senso.ui import theme
from senso.ui.components.flag import flag_image
from senso.ui.components.tea_info import tea_info_card

PickImage = Callable[[], Awaitable[bytes | None]]


@dataclass
class FormDeps:
    repo: BeanRepository
    photo_dir: Path
    pick_image: PickImage  # 사진을 고르게 하고 내용을 돌려준다. 취소하면 None
    notify: Callable[[str], None]
    confirm: Callable[[str, str, str, Callable[[], None]], None]
    close: Callable[[], None]  # 목록으로 돌아가기
    access: Callable = nullcontext


class BeanForm(ft.Column):
    """탭 이동·로그아웃·세션 종료 때 미저장 사진을 해제한다."""

    discard: Callable[[], None]

    def dispose(self) -> None:
        self.discard()

    def will_unmount(self) -> None:
        self.dispose()


def bean_form_view(kind: BeanKind, bean: Bean | None, deps: FormDeps) -> ft.Control:
    labels = LABELS[kind]
    editing = bean is not None

    # 미저장 사진은 축소한 바이트만 보관한다. DB 저장 전 파일은 만들지 않는다.
    original_photo = bean.photo_path if bean else None
    state = {"current": original_photo, "pending": None, "closed": False}

    def discard_unsaved_photo() -> None:
        state["pending"] = None

    def dispose() -> None:
        state["closed"] = True
        discard_unsaved_photo()
        photo_box.content = None

    photo_box = ft.Container(
        width=120, height=120, border_radius=16, bgcolor=theme.CREAM, alignment=ft.Alignment.CENTER
    )
    remove_photo_btn = ft.TextButton("사진 빼기", icon=ft.Icons.DELETE_OUTLINE)
    pick_photo_btn = ft.OutlinedButton("사진 고르기", icon=ft.Icons.ADD_A_PHOTO_OUTLINED)

    def render_photo() -> None:
        data = state["pending"] or (
            load_photo(state["current"], deps.photo_dir) if state["current"] else None
        )
        if data:
            photo_box.content = ft.Image(
                src=data, width=120, height=120, fit=ft.BoxFit.COVER, border_radius=16
            )
        else:
            photo_box.content = ft.Icon(ft.Icons.IMAGE_OUTLINED, size=40, color=theme.BROWN_LIGHT)
        remove_photo_btn.visible = data is not None
        pick_photo_btn.content = "사진 바꾸기" if data else "사진 고르기"

    async def on_pick_photo(_: ft.Event) -> None:
        try:
            data = await deps.pick_image()
        except PhotoError as e:
            if not state["closed"]:
                deps.notify(str(e))
            return
        except Exception:
            # 권한 거부 등: 사진 없이도 등록할 수 있게 안내만 한다
            if not state["closed"]:
                deps.notify("사진을 가져오지 못했어요. 사진 없이도 등록할 수 있어요.")
            return
        if data is None or state["closed"]:
            return
        try:
            prepared = prepare_photo(data)
        except PhotoError as e:
            deps.notify(str(e))
            return
        discard_unsaved_photo()
        state["current"] = None
        state["pending"] = prepared
        render_photo()
        photo_box.update()
        pick_photo_btn.update()
        remove_photo_btn.update()

    def on_remove_photo(_: ft.Event) -> None:
        discard_unsaved_photo()
        state["current"] = None
        render_photo()
        photo_box.update()
        pick_photo_btn.update()
        remove_photo_btn.update()

    pick_photo_btn.on_click = on_pick_photo
    remove_photo_btn.on_click = on_remove_photo
    render_photo()

    # ---- 입력 항목 ------------------------------------------------------
    name = ft.TextField(
        label=f"{labels.item} 이름 *",
        hint_text="예) 에티오피아 예가체프" if kind is BeanKind.COFFEE else "예) 제주 세작",
        value=bean.name if bean else "",
        max_length=NAME_MAX,
        autofocus=not editing,
    )
    origin = ft.TextField(
        label="산지 (나라·지역)",
        hint_text="예) 에티오피아, 콜롬비아" if kind is BeanKind.COFFEE else "예) 제주, 다즐링",
        value=(bean.origin or "") if bean else "",
        max_length=ORIGIN_MAX,
    )
    flag_text = ft.Text(size=theme.CAPTION_SIZE, color=theme.TEXT_MUTED)
    flag_hint = ft.Row(spacing=8, controls=[flag_text])

    def render_flag() -> None:
        country = country_of(origin.value, name.value)
        image = flag_image(country, height=16) if country else None
        if country:
            flag_text.value = f"{country.name} 국기가 함께 표시돼요"
        else:
            flag_text.value = "산지를 적으면 그 나라 국기가 함께 표시돼요"
        flag_hint.controls = [image, flag_text] if image else [flag_text]

    render_flag()
    producer = ft.TextField(
        label=labels.producer,
        value=(bean.producer or "") if bean else "",
        max_length=PRODUCER_MAX,
    )
    produced_on = ft.TextField(
        label=labels.produced_on,
        hint_text="2026-11-01",
        value=bean.produced_on.isoformat() if bean and bean.produced_on else "",
        keyboard_type=ft.KeyboardType.DATETIME,
    )
    if kind is BeanKind.COFFEE:
        choice = ft.Dropdown(
            label="로스팅 정도",
            value=(bean.roast_level if bean else None) or "unknown",
            options=[ft.DropdownOption(key=k, text=v) for k, v in ROAST_LEVELS.items()],
            expand=True,
        )
        choice_field = "roast_level"
    else:
        choice = ft.Dropdown(
            label="차 종류",
            value=bean.tea_type if bean else None,
            options=[ft.DropdownOption(key=k, text=v) for k, v in TEA_TYPES.items()],
            expand=True,
        )
        choice_field = "tea_type"

    tea_box = ft.Column(visible=kind is BeanKind.TEA)

    def render_tea_info() -> None:
        card = tea_info_card(choice.value) if kind is BeanKind.TEA else None
        tea_box.controls = [card] if card else []

    def on_tea_type(_: ft.Event) -> None:
        render_tea_info()
        tea_box.update()

    if kind is BeanKind.TEA:
        choice.on_select = on_tea_type
    render_tea_info()

    fields = {"name": name, "origin": origin, "producer": producer, "produced_on": produced_on}

    def clear_error(e: ft.Event) -> None:
        """고치기 시작하면 그 칸의 오류 문구를 지운다."""
        if getattr(e.control, "error", None):
            e.control.error = None
            e.control.update()

    for field in fields.values():
        field.on_change = clear_error

    def on_place_change(e: ft.Event) -> None:
        clear_error(e)
        render_flag()
        flag_hint.update()

    name.on_change = on_place_change
    origin.on_change = on_place_change

    def show_errors(errors: dict[str, str]) -> None:
        for key, field in fields.items():
            field.error = errors.get(key)
        choice.error_text = errors.get(choice_field)

    # ---- 저장·삭제·취소 ---------------------------------------------------
    def save(_: ft.Event) -> None:
        try:
            draft = validate_bean(
                kind,
                name.value,
                producer.value,
                produced_on.value,
                roast_level=choice.value if kind is BeanKind.COFFEE else None,
                tea_type=choice.value if kind is BeanKind.TEA else None,
                origin=origin.value,
            )
        except BeanValidationError as e:
            show_errors(e.errors)
            form.update()
            deps.notify("입력을 확인해 주세요.")
            return
        if state["closed"]:
            return
        new_photo = None
        try:
            if state["pending"]:
                new_photo = save_prepared_photo(state["pending"], deps.photo_dir)
            photo = new_photo or state["current"]
            if bean is None:
                deps.repo.create(draft, photo_path=photo)
            else:
                deps.repo.update(bean.id, draft, photo_path=photo)
        except Exception:
            if new_photo:
                delete_photo(new_photo, deps.photo_dir)
            deps.notify("저장하지 못했어요. 다시 시도해 주세요.")
            return
        # DB 저장에 성공한 뒤에만 기존 사진을 지운다.
        if original_photo and original_photo != photo:
            delete_photo(original_photo, deps.photo_dir)
        discard_unsaved_photo()
        deps.notify(f"{josa(quote(draft.name), '을')} 저장했어요.")
        deps.close()

    def on_save(event: ft.Event) -> None:
        with deps.access():
            save(event)

    def on_cancel(_: ft.Event) -> None:
        discard_unsaved_photo()
        deps.close()

    def on_delete(_: ft.Event) -> None:
        assert bean is not None

        def really_delete() -> None:
            discard_unsaved_photo()
            deps.repo.soft_delete(bean.id)
            deps.notify(f"{josa(quote(bean.name), '을')} 목록에서 지웠어요.")
            deps.close()

        deps.confirm(
            f"{josa(labels.item, '을')} 지울까요?",
            f"{josa(quote(bean.name), '이')} 목록에서 사라져요.\n"
            f"이 {josa(labels.item, '으로')} 남긴 기록은 그대로 남아요.",
            "지우기",
            really_delete,
        )

    title = f"{labels.item} 수정" if editing else f"{labels.item} 등록"
    actions: list[ft.Control] = [
        ft.FilledButton("저장", icon=ft.Icons.CHECK, height=48, expand=True, on_click=on_save),
    ]
    form = BeanForm(
        spacing=theme.SPACING,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,  # 입력 칸을 가로로 꽉 채움
        controls=[
            ft.Row(
                controls=[
                    ft.IconButton(ft.Icons.ARROW_BACK, tooltip="뒤로", on_click=on_cancel),
                    ft.Text(
                        title, size=theme.HEADING_SIZE, weight=ft.FontWeight.BOLD, color=theme.BROWN
                    ),
                ]
            ),
            ft.Row(
                spacing=16,
                controls=[
                    photo_box,
                    ft.Column(spacing=4, controls=[pick_photo_btn, remove_photo_btn]),
                ],
            ),
            name,
            ft.Text("상세 정보 (선택)", size=theme.CAPTION_SIZE, color=theme.TEXT_MUTED),
            origin,
            flag_hint,
            producer,
            produced_on,
            ft.Row([choice]),
            tea_box,
            ft.Row(actions),
        ],
    )
    if editing:
        form.controls.append(
            ft.TextButton(
                f"이 {labels.item} 지우기",
                icon=ft.Icons.DELETE_OUTLINE,
                style=ft.ButtonStyle(color=ft.Colors.RED_700),
                on_click=on_delete,
            )
        )
    form.discard = dispose
    return form
