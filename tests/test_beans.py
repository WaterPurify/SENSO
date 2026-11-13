import io
import json
from datetime import date

import pytest
from PIL import Image

from senso.db.bean_repo import BeanRepository
from senso.db.database import open_database
from senso.domain.bean import BeanKind, BeanValidationError, parse_date, validate_bean
from senso.photos import PhotoError, delete_photo, load_photo, save_photo

TODAY = date(2026, 11, 13)


@pytest.fixture
def conn(tmp_path):
    c = open_database(tmp_path / "test.db")
    yield c
    c.close()


@pytest.fixture
def repo(conn):
    return BeanRepository(conn)


# ---- 검증 -----------------------------------------------------------------


def test_name_only_is_enough():
    draft = validate_bean(BeanKind.COFFEE, "  예가체프  ", today=TODAY)
    assert draft.name == "예가체프"
    assert draft.producer is None and draft.produced_on is None


@pytest.mark.parametrize("name", [None, "", "   "])
def test_name_required(name):
    with pytest.raises(BeanValidationError) as e:
        validate_bean(BeanKind.TEA, name, today=TODAY)
    assert "name" in e.value.errors
    assert "차 이름" in e.value.errors["name"]


@pytest.mark.parametrize("text", ["2026-11-01", "2026.11.01", "20261101", "2026/11/1"])
def test_date_formats(text):
    assert parse_date(text) == date(2026, 11, 1)


@pytest.mark.parametrize(
    ("text", "message"),
    [("어제", "2026-11-01처럼"), ("2026-02-30", "없는 날짜"), ("2026-12-01", "미래")],
)
def test_bad_dates(text, message):
    with pytest.raises(BeanValidationError) as e:
        validate_bean(BeanKind.COFFEE, "원두", produced_on=text, today=TODAY)
    assert message in e.value.errors["produced_on"]


def test_coffee_ignores_tea_type_and_tea_ignores_roast_level():
    coffee = validate_bean(BeanKind.COFFEE, "a", roast_level="dark", tea_type="green", today=TODAY)
    tea = validate_bean(BeanKind.TEA, "b", roast_level="dark", tea_type="green", today=TODAY)
    assert (coffee.roast_level, coffee.tea_type) == ("dark", None)
    assert (tea.roast_level, tea.tea_type) == (None, "green")


def test_unknown_choice_rejected():
    with pytest.raises(BeanValidationError) as e:
        validate_bean(BeanKind.COFFEE, "a", roast_level="burnt", today=TODAY)
    assert "roast_level" in e.value.errors


def test_all_errors_reported_together():
    with pytest.raises(BeanValidationError) as e:
        validate_bean(BeanKind.COFFEE, "", produced_on="nope", today=TODAY)
    assert set(e.value.errors) == {"name", "produced_on"}


# ---- 저장소 ----------------------------------------------------------------


def test_create_and_list_by_kind(repo):
    repo.create(validate_bean(BeanKind.COFFEE, "예가체프", "프릳츠", "2026-11-01", "light"))
    repo.create(validate_bean(BeanKind.TEA, "제주 세작", tea_type="green"))

    coffees = repo.list(BeanKind.COFFEE)
    teas = repo.list(BeanKind.TEA)
    assert [b.name for b in coffees] == ["예가체프"]
    assert [b.name for b in teas] == ["제주 세작"]
    assert coffees[0].produced_on == date(2026, 11, 1)
    assert coffees[0].producer == "프릳츠"


def test_update(repo):
    bean = repo.create(validate_bean(BeanKind.COFFEE, "이전 이름"))
    updated = repo.update(bean.id, validate_bean(BeanKind.COFFEE, "새 이름"), photo_path="p.jpg")
    assert updated.name == "새 이름"
    assert updated.photo_path == "p.jpg"


def test_update_missing_bean(repo):
    with pytest.raises(LookupError):
        repo.update(999, validate_bean(BeanKind.COFFEE, "x"), None)


def test_soft_delete_hides_but_keeps_row_and_brews(repo, conn):
    bean = repo.create(validate_bean(BeanKind.COFFEE, "지울 원두"))
    conn.execute(
        "INSERT INTO brews (bean_id, bean_snapshot, dose_g, water_g) VALUES (?, ?, 15, 250)",
        (bean.id, json.dumps({"name": bean.name})),
    )
    conn.commit()

    repo.soft_delete(bean.id)

    assert repo.list(BeanKind.COFFEE) == []
    assert repo.get(bean.id) is None
    assert repo.get(bean.id, include_deleted=True).name == "지울 원두"
    assert conn.execute("SELECT COUNT(*) FROM brews").fetchone()[0] == 1


def test_beans_survive_reopen(tmp_path):
    path = tmp_path / "db.sqlite"
    c = open_database(path)
    BeanRepository(c).create(validate_bean(BeanKind.TEA, "보성 녹차"))
    c.close()
    c = open_database(path)
    assert [b.name for b in BeanRepository(c).list(BeanKind.TEA)] == ["보성 녹차"]
    c.close()


# ---- 사진 ------------------------------------------------------------------


def _png(size=(2000, 1000)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", size, (120, 80, 40, 255)).save(buf, "PNG")
    return buf.getvalue()


def test_photo_saved_resized_as_jpeg(tmp_path):
    name = save_photo(_png(), tmp_path)
    assert name.endswith(".jpg")
    with Image.open(tmp_path / name) as img:
        assert img.format == "JPEG"
        assert max(img.size) == 1280
    assert load_photo(name, tmp_path)


def test_not_an_image_rejected(tmp_path):
    with pytest.raises(PhotoError):
        save_photo(b"this is not an image", tmp_path)


def test_missing_photo_loads_as_none(tmp_path):
    assert load_photo("nope.jpg", tmp_path) is None


def test_photo_paths_cannot_escape_folder(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("x")
    photos = tmp_path / "photos"
    photos.mkdir()
    assert load_photo("../secret.txt", photos) is None
    delete_photo("../secret.txt", photos)
    assert secret.exists()
