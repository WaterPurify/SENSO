"""추출 기록 저장소."""

# 메서드 이름 list가 내장 list를 가리므로 타입 표기를 문자열로 미룬다
from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from senso.domain.brew import BeanSnapshot, Brew, BrewDraft, Recipe, Tasting

_COLUMNS = (
    "id, bean_id, bean_snapshot, brewed_at, desired_flavors, hot_or_iced, equipment, "
    "dose_g, water_g, temp_c, grind, time_s, ice_g, notes, "
    "acidity, bitterness, sweetness, body, satisfaction, tasting_notes, next_wish, next_memo, "
    "based_on_brew_id, based_on_rec_id, is_sample"
)


def _json_list(text: str | None) -> tuple[str, ...]:
    if not text:
        return ()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return ()
    return tuple(str(v) for v in value) if isinstance(value, list) else ()


def _to_brew(row: sqlite3.Row) -> Brew:
    equipment = json.loads(row["equipment"]) if row["equipment"] else {}
    return Brew(
        id=row["id"],
        bean_id=row["bean_id"],
        bean=BeanSnapshot.from_dict(json.loads(row["bean_snapshot"])),
        brewed_at=datetime.fromisoformat(row["brewed_at"]),
        recipe=Recipe(
            dose_g=row["dose_g"],
            water_g=row["water_g"],
            temp_c=row["temp_c"],
            grind=row["grind"],
            time_s=row["time_s"],
            ice_g=row["ice_g"],
        ),
        desired_flavors=_json_list(row["desired_flavors"]),
        iced=row["hot_or_iced"] == "iced",
        dripper=equipment.get("dripper"),
        grinder=equipment.get("grinder"),
        notes=row["notes"],
        tasting=Tasting(
            acidity=row["acidity"],
            bitterness=row["bitterness"],
            sweetness=row["sweetness"],
            body=row["body"],
            satisfaction=row["satisfaction"],
            notes=row["tasting_notes"],
            next_wish=_json_list(row["next_wish"]),
            next_memo=row["next_memo"],
        ),
        based_on_brew_id=row["based_on_brew_id"],
        based_on_rec_id=row["based_on_rec_id"],
        is_sample=bool(row["is_sample"]),
    )


def _fields(draft: BrewDraft) -> dict:
    r, t = draft.recipe, draft.tasting
    equipment = {k: v for k, v in (("dripper", draft.dripper), ("grinder", draft.grinder)) if v}
    return {
        "bean_id": draft.bean_id,
        "bean_snapshot": json.dumps(draft.bean.to_dict(), ensure_ascii=False),
        "desired_flavors": json.dumps(list(draft.desired_flavors), ensure_ascii=False),
        "hot_or_iced": "iced" if draft.iced else "hot",
        "equipment": json.dumps(equipment, ensure_ascii=False),
        "dose_g": r.dose_g,
        "water_g": r.water_g,
        "temp_c": r.temp_c,
        "grind": r.grind,
        "time_s": r.time_s,
        "ice_g": r.ice_g,
        "notes": draft.notes,
        "acidity": t.acidity,
        "bitterness": t.bitterness,
        "sweetness": t.sweetness,
        "body": t.body,
        "satisfaction": t.satisfaction,
        "tasting_notes": t.notes,
        "next_wish": json.dumps(list(t.next_wish)),
        "next_memo": t.next_memo,
        "based_on_brew_id": draft.based_on_brew_id,
        "based_on_rec_id": draft.based_on_rec_id,
    }


class BrewRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list(self, limit: int | None = None) -> list[Brew]:
        """최신순."""
        sql = f"SELECT {_COLUMNS} FROM brews ORDER BY brewed_at DESC, id DESC"
        params: tuple = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)
        return [_to_brew(r) for r in self.conn.execute(sql, params).fetchall()]

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM brews").fetchone()[0]

    def get(self, brew_id: int) -> Brew | None:
        row = self.conn.execute(f"SELECT {_COLUMNS} FROM brews WHERE id = ?", (brew_id,)).fetchone()
        return _to_brew(row) if row else None

    def create(self, draft: BrewDraft, brewed_at: datetime, is_sample: bool = False) -> Brew:
        values = _fields(draft) | {
            "brewed_at": brewed_at.isoformat(timespec="minutes"),
            "is_sample": int(is_sample),
        }
        cols = ", ".join(values)
        marks = ", ".join("?" for _ in values)
        with self.conn:
            cur = self.conn.execute(
                f"INSERT INTO brews ({cols}) VALUES ({marks})", tuple(values.values())
            )
        brew = self.get(cur.lastrowid)
        assert brew is not None
        return brew

    def update(self, brew_id: int, draft: BrewDraft) -> Brew:
        """추출 조건과 평가를 함께 고친다. 연결 정보(어떤 기록에서 왔는지)는 바꾸지 않는다."""
        values = _fields(draft)
        values.pop("based_on_brew_id")
        values.pop("based_on_rec_id")
        assignments = ", ".join(f"{k} = ?" for k in values)
        with self.conn:
            cur = self.conn.execute(
                f"UPDATE brews SET {assignments}, updated_at = datetime('now') WHERE id = ?",
                (*values.values(), brew_id),
            )
        if cur.rowcount == 0:
            raise LookupError(f"기록을 찾을 수 없어요 (id={brew_id})")
        brew = self.get(brew_id)
        assert brew is not None
        return brew

    def delete(self, brew_id: int) -> None:
        """기록을 지운다. 이 기록을 바탕으로 만든 기록은 남고 연결만 끊긴다."""
        with self.conn:
            self.conn.execute("DELETE FROM brews WHERE id = ?", (brew_id,))

    def has_samples(self) -> bool:
        return (
            self.conn.execute("SELECT 1 FROM brews WHERE is_sample = 1 LIMIT 1").fetchone()
            is not None
        )

    def delete_samples(self) -> int:
        """예시 기록을 모두 지우고 지운 개수를 돌려준다. 실제 기록은 건드리지 않는다."""
        with self.conn:
            cur = self.conn.execute("DELETE FROM brews WHERE is_sample = 1")
        return cur.rowcount

    def derived_from(self, brew_id: int) -> list[Brew]:
        """이 기록을 바탕으로 만든 기록들 (최신순)."""
        rows = self.conn.execute(
            f"SELECT {_COLUMNS} FROM brews WHERE based_on_brew_id = ? "
            "ORDER BY brewed_at DESC, id DESC",
            (brew_id,),
        ).fetchall()
        return [_to_brew(r) for r in rows]
