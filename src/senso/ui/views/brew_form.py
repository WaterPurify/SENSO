"""③ 추출·시음 기록 입력 (새 기록 / 수정 / 추천으로 새 기록)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import flet as ft

from senso.db.bean_repo import BeanRepository
from senso.db.brew_repo import BrewRepository
from senso.domain.bean import LABELS, Bean, BeanKind
from senso.domain.brew import (
    DESIRED_FLAVORS,
    NEXT_WISHES,
    SCORE_FIELDS,
    WISHES_BY_KIND,
    BeanSnapshot,
    Brew,
    BrewDraft,
    BrewValidationError,
    format_number,
    format_time,
    validate_brew,
)
from senso.ui import theme
from senso.ui.components.aroma import AromaPicker
from senso.ui.components.inputs import ChipGroup, ScoreInput, section


@dataclass
class BrewFormDeps:
    beans: BeanRepository
    brews: BrewRepository
    now: Callable[[], datetime]
    notify: Callable[[str], None]
    on_saved: Callable[[Brew], None]
    on_cancel: Callable[[], None]
    on_add_bean: Callable[[], None]


def _num(value: float | None) -> str:
    return "" if value is None else format_number(value)


def brew_form_view(
    deps: BrewFormDeps,
    *,
    editing: Brew | None = None,
    prefill: BrewDraft | None = None,
    banner: ft.Control | None = None,
) -> ft.Control:
    """editing: 고칠 기록. prefill: 새 기록의 초기값(추천으로 새 기록). banner: 맨 위 안내."""
    source: BrewDraft | None = editing or prefill
    beans: list[Bean] = deps.beans.list_all()
    beans_by_id = {b.id: b for b in beans}

    # 기록에 쓰인 원두가 지워졌어도 수정·재추출할 수 있게 선택지에 남긴다
    snapshot_only: BeanSnapshot | None = None
    if source and (source.bean_id is None or source.bean_id not in beans_by_id):
        deleted = deps.beans.get(source.bean_id, include_deleted=True) if source.bean_id else None
        if deleted:
            beans_by_id[deleted.id] = deleted
        else:
            snapshot_only = source.bean

    if not beans_by_id and snapshot_only is None:
        return _no_beans_view(deps)

    SNAPSHOT_KEY = "snapshot"
    options = [
        ft.DropdownOption(
            key=str(b.id),
            text=f"{b.name} · {LABELS[b.kind].title}" + (" (지운 항목)" if b not in beans else ""),
        )
        for b in beans_by_id.values()
    ]
    if snapshot_only:
        options.append(
            ft.DropdownOption(key=SNAPSHOT_KEY, text=f"{snapshot_only.name} (지운 항목)")
        )

    if source:
        initial_key = str(source.bean_id) if source.bean_id in beans_by_id else SNAPSHOT_KEY
    else:
        initial_key = str(beans[0].id) if beans else options[0].key

    def selected_bean() -> tuple[int | None, Bean | BeanSnapshot | None]:
        key = bean_dd.value
        if key == SNAPSHOT_KEY:
            return None, snapshot_only
        if key and key.isdigit() and int(key) in beans_by_id:
            return int(key), beans_by_id[int(key)]
        return None, None

    def current_kind() -> BeanKind:
        _, bean = selected_bean()
        return bean.kind if bean else BeanKind.COFFEE

    bean_dd = ft.Dropdown(label="원두·차 *", value=initial_key, options=options, expand=True)

    # ---- 추출 전 ----------------------------------------------------------
    recipe = source.recipe if source else None
    iced_btn = ft.SegmentedButton(
        selected=["iced" if source and source.iced else "hot"],
        segments=[
            ft.Segment(value="hot", label=ft.Text("따뜻하게"), icon=ft.Icon(ft.Icons.WHATSHOT)),
            ft.Segment(value="iced", label=ft.Text("아이스"), icon=ft.Icon(ft.Icons.AC_UNIT)),
        ],
    )
    dose = ft.TextField(suffix="g", value=_num(recipe.dose_g if recipe else None), expand=True)
    water = ft.TextField(
        label="물양 *", suffix="g", value=_num(recipe.water_g if recipe else None), expand=True
    )
    ratio_text = ft.Text(size=theme.CAPTION_SIZE, color=theme.TEXT_MUTED)
    dripper = ft.TextField(label="추출 도구", value=(source.dripper or "") if source else "")
    grinder = ft.TextField(
        label="그라인더", hint_text="예) 코만단테", value=(source.grinder or "") if source else ""
    )
    temp = ft.TextField(label="수온", suffix="°C", value=_num(recipe.temp_c if recipe else None))
    grind = ft.TextField(
        label="분쇄도",
        hint_text="예) 24클릭, 중간",
        value=(recipe.grind or "") if recipe else "",
        helper="그라인더마다 표기가 달라 자유롭게 적어요",
    )
    time = ft.TextField(
        label="추출 시간",
        hint_text="3:00",
        suffix="분:초",
        value=format_time(recipe.time_s) if recipe and recipe.time_s is not None else "",
    )
    ice = ft.TextField(label="얼음량", suffix="g", value=_num(recipe.ice_g if recipe else None))
    notes = ft.TextField(
        label="붓는 순서·추출 메모",
        multiline=True,
        min_lines=2,
        max_lines=5,
        value=(source.notes or "") if source else "",
    )
    has_details = bool(
        source
        and (
            source.dripper
            or source.grinder
            or source.notes
            or recipe.temp_c
            or recipe.grind
            or recipe.time_s is not None
            or recipe.ice_g
        )
    )
    details = ft.ExpansionTile(
        title=ft.Text("도구·수온·분쇄도·시간 (선택)"),
        expanded=has_details,
        tile_padding=0,
        controls=[
            ft.Column(
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[dripper, grinder, temp, grind, time, ice, notes],
            )
        ],
    )
    flavor_box = ft.Column(spacing=6)
    flavors: ChipGroup | None = None

    # ---- 시음 후 ----------------------------------------------------------
    tasting = (
        source.tasting if editing else None
    )  # 추천으로 만든 새 기록에는 평가를 복사하지 않는다
    scores = {k: ScoreInput(k, getattr(tasting, k) if tasting else None) for k in SCORE_FIELDS}
    tasting_notes = ft.TextField(
        label="느낀 점",
        multiline=True,
        min_lines=2,
        max_lines=5,
        value=(tasting.notes or "") if tasting else "",
    )
    wish_box = ft.Column(spacing=6)
    wishes: ChipGroup | None = None
    aroma_box = ft.Column()
    aroma: AromaPicker | None = None
    next_memo = ft.TextField(
        label="다음에 원하는 맛 (메모)",
        hint_text="예) 오늘보다 덜 시고 단맛이 더 났으면",
        value=(tasting.next_memo or "") if tasting else "",
    )

    # ---- 종류(커피/차)에 따라 바뀌는 부분 -----------------------------------------
    def apply_kind(first: bool = False) -> None:
        nonlocal flavors, wishes, aroma
        kind = current_kind()
        is_coffee = kind is BeanKind.COFFEE
        dose.label = "원두량 *" if is_coffee else "찻잎 양 *"
        dripper.hint_text = "예) V60, 칼리타" if is_coffee else "예) 다관, 개완, 티팟"
        grinder.visible = is_coffee
        grind.visible = is_coffee

        old_flavors = flavors.value if flavors else list(source.desired_flavors if source else [])
        flavors = ChipGroup(
            [(f, f) for f in DESIRED_FLAVORS[kind]],
            selected=[f for f in old_flavors if f in DESIRED_FLAVORS[kind]],
        )
        flavor_box.controls = [
            ft.Text("오늘 원하는 맛", color=theme.TEXT_MUTED, size=theme.CAPTION_SIZE),
            flavors.control,
        ]
        old_wishes = wishes.value if wishes else list(tasting.next_wish if tasting else [])
        wishes = ChipGroup(
            [(w, NEXT_WISHES[w]) for w in WISHES_BY_KIND[kind]],
            selected=[w for w in old_wishes if w in WISHES_BY_KIND[kind]],
            exclusive=["keep"],
        )
        wish_box.controls = [
            ft.Text("다음에 원하는 변화", color=theme.TEXT_MUTED, size=theme.CAPTION_SIZE),
            wishes.control,
        ]
        # 향: 커피와 차는 향 목록이 달라 종류가 바뀌면 다시 만든다 (같은 키는 유지)
        if aroma is not None:
            old = (aroma.groups, aroma.notes, aroma.intensity.value)
        elif tasting is not None:
            old = (list(tasting.aromas), list(tasting.aroma_notes), tasting.aroma_intensity)
        else:
            old = ([], [], None)
        aroma = AromaPicker(kind, old[0], old[1], old[2])
        aroma_box.controls = [aroma.control]
        if not first:
            form.update()

    def update_ratio(_: ft.Event | None = None) -> None:
        try:
            d = float((dose.value or "").replace(",", "."))
            w = float((water.value or "").replace(",", "."))
            ratio_text.value = f"비율 1 : {w / d:.1f}" if d > 0 and w > 0 else ""
        except ValueError:
            ratio_text.value = ""
        if _ is not None:
            ratio_text.update()

    def update_iced(_: ft.Event | None = None) -> None:
        ice.visible = "iced" in (iced_btn.selected or [])
        if _ is not None:
            ice.update()

    def clear_error(e: ft.Event) -> None:
        if getattr(e.control, "error", None):
            e.control.error = None
            e.control.update()

    bean_dd.on_select = lambda _: apply_kind()
    iced_btn.on_change = update_iced
    for f in (dose, water):
        f.on_change = lambda e: (clear_error(e), update_ratio(e))
    for f in (temp, time, ice):
        f.on_change = clear_error

    # ---- 저장 -------------------------------------------------------------
    error_fields = {"dose_g": dose, "water_g": water, "temp_c": temp, "time_s": time, "ice_g": ice}

    def on_save(_: ft.Event) -> None:
        bean_id, bean = selected_bean()
        try:
            draft = validate_brew(
                bean=bean,
                bean_id=bean_id,
                dose_g=dose.value,
                water_g=water.value,
                temp_c=temp.value,
                grind=grind.value,
                time=time.value,
                ice_g=ice.value,
                iced="iced" in (iced_btn.selected or []),
                desired_flavors=flavors.value if flavors else [],
                dripper=dripper.value,
                grinder=grinder.value,
                notes=notes.value,
                scores={k: s.value for k, s in scores.items()},
                tasting_notes=tasting_notes.value,
                next_wish=wishes.value if wishes else [],
                next_memo=next_memo.value,
                aroma_intensity=aroma.intensity.value if aroma else None,
                aromas=aroma.groups if aroma else [],
                aroma_notes=aroma.notes if aroma else [],
                based_on_brew_id=prefill.based_on_brew_id if prefill and not editing else None,
                based_on_rec_id=prefill.based_on_rec_id if prefill and not editing else None,
            )
        except BrewValidationError as e:
            for key, field in error_fields.items():
                field.error = e.errors.get(key)
            bean_dd.error_text = e.errors.get("bean")
            if any(k in e.errors for k in ("temp_c", "time_s", "ice_g")):
                details.expanded = True
            form.update()
            deps.notify("입력을 확인해 주세요.")
            return
        if editing:
            brew = deps.brews.update(editing.id, draft)
            deps.notify("기록을 고쳤어요.")
        else:
            brew = deps.brews.create(draft, brewed_at=deps.now())
            deps.notify(
                "기록을 저장했어요." if draft.tasting.is_empty else "기록과 평가를 저장했어요."
            )
        deps.on_saved(brew)

    title = "기록 고치기" if editing else "새 기록"
    form = ft.Column(
        spacing=theme.SPACING,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            ft.Row(
                controls=[
                    ft.IconButton(
                        ft.Icons.ARROW_BACK, tooltip="뒤로", on_click=lambda _: deps.on_cancel()
                    ),
                    ft.Text(
                        title, size=theme.HEADING_SIZE, weight=ft.FontWeight.BOLD, color=theme.BROWN
                    ),
                ]
            ),
            *([banner] if banner else []),
            section(
                "추출 전",
                "* 표시만 필수예요. 모르는 값은 비워 두세요.",
                [
                    ft.Row([bean_dd]),
                    flavor_box,
                    iced_btn,
                    ft.Row(spacing=12, controls=[dose, water]),
                    ratio_text,
                    details,
                ],
            ),
            section(
                "시음 후",
                "마셔 본 뒤에 입력해도 돼요. 비워 두고 저장한 뒤 나중에 추가할 수 있어요.",
                [
                    *[s.control for s in scores.values()],
                    ft.Divider(color="#EFE6D8"),
                    aroma_box,
                    ft.Divider(color="#EFE6D8"),
                    tasting_notes,
                    wish_box,
                    next_memo,
                ],
            ),
            ft.FilledButton("저장", icon=ft.Icons.CHECK, height=48, on_click=on_save),
        ],
    )
    apply_kind(first=True)
    update_ratio()
    update_iced()
    return form


def _no_beans_view(deps: BrewFormDeps) -> ft.Control:
    return ft.Column(
        spacing=theme.SPACING,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            ft.Row(
                controls=[
                    ft.IconButton(
                        ft.Icons.ARROW_BACK, tooltip="뒤로", on_click=lambda _: deps.on_cancel()
                    ),
                    ft.Text(
                        "새 기록",
                        size=theme.HEADING_SIZE,
                        weight=ft.FontWeight.BOLD,
                        color=theme.BROWN,
                    ),
                ]
            ),
            ft.Text(
                "기록하려면 먼저 원두나 차를 등록해 주세요.",
                size=theme.BODY_SIZE,
                color=theme.TEXT_MUTED,
            ),
            ft.FilledButton(
                "원두 등록하러 가기",
                icon=ft.Icons.COFFEE,
                height=48,
                on_click=lambda _: deps.on_add_bean(),
            ),
        ],
    )
