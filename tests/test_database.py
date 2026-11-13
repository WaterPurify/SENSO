import sqlite3

import pytest

from senso.db.database import available_migrations, migrate, open_database, schema_version


@pytest.fixture
def conn(tmp_path):
    c = open_database(tmp_path / "test.db")
    yield c
    c.close()


def table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {r[0] for r in rows}


def test_migration_creates_schema_v1(conn):
    assert schema_version(conn) == len(available_migrations())
    assert {"beans", "brews", "recommendations", "quiz_results"} <= table_names(conn)


def test_migrate_twice_is_harmless(conn):
    before = schema_version(conn)
    assert migrate(conn) == before


def test_data_survives_reopen(tmp_path):
    path = tmp_path / "reopen.db"
    c = open_database(path)
    c.execute("INSERT INTO beans (kind, name) VALUES ('coffee', '에티오피아 예가체프')")
    c.commit()
    c.close()

    c = open_database(path)
    assert c.execute("SELECT name FROM beans").fetchone()["name"] == "에티오피아 예가체프"
    c.close()


def test_bean_name_is_required(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO beans (kind, name) VALUES ('coffee', '   ')")


def insert_brew(conn, **overrides):
    values = {"bean_snapshot": "{}", "dose_g": 15, "water_g": 250} | overrides
    cols = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    conn.execute(f"INSERT INTO brews ({cols}) VALUES ({marks})", tuple(values.values()))


def test_unrated_brew_keeps_scores_empty(conn):
    insert_brew(conn)
    row = conn.execute("SELECT acidity, satisfaction FROM brews").fetchone()
    assert row["acidity"] is None
    assert row["satisfaction"] is None


@pytest.mark.parametrize(
    ("field", "value"), [("acidity", 0), ("satisfaction", 6), ("dose_g", 0), ("temp_c", 120)]
)
def test_out_of_range_values_rejected(conn, field, value):
    with pytest.raises(sqlite3.IntegrityError):
        insert_brew(conn, **{field: value})


def test_failed_migration_rolls_back(tmp_path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_ok.sql").write_text("CREATE TABLE a (id INTEGER);", encoding="utf-8")
    (migrations / "002_bad.sql").write_text(
        "CREATE TABLE b (id INTEGER);\nSELECT * FROM missing_table;", encoding="utf-8"
    )
    c = sqlite3.connect(tmp_path / "x.db")
    with pytest.raises(sqlite3.Error):
        migrate(c, migrations)
    assert schema_version(c) == 1
    assert table_names(c) == {"a"}
    c.close()
