from datetime import datetime

import pytest

from senso.db.bean_repo import BeanRepository
from senso.db.brew_repo import BrewRepository
from senso.db.database import open_database
from senso.domain.bean import BeanKind, validate_bean
from senso.domain.brew import validate_brew
from senso.samples import add_samples, remove_samples

NOW = datetime(2026, 11, 13, 9, 0)


@pytest.fixture
def repos(tmp_path):
    conn = open_database(tmp_path / "t.db")
    yield BeanRepository(conn), BrewRepository(conn)
    conn.close()


def test_samples_are_marked_and_linked(repos):
    beans, brews = repos
    assert not brews.has_samples()
    assert add_samples(beans, brews, NOW) == 3

    all_brews = brews.list()
    assert len(all_brews) == 3
    assert all(b.is_sample for b in all_brews)
    assert all(b.brewed_at < NOW for b in all_brews)
    assert any(b.based_on_brew_id for b in all_brews)  # 제안으로 이어진 기록 예시
    assert brews.has_samples()


def test_remove_samples_keeps_real_data(repos):
    beans, brews = repos
    real_bean = beans.create(validate_bean(BeanKind.COFFEE, "내 원두"))
    real = brews.create(
        validate_brew(bean=real_bean, bean_id=real_bean.id, dose_g="15", water_g="240"),
        brewed_at=NOW,
    )
    add_samples(beans, brews, NOW)

    # 사용자가 예시 원두로 실제 기록을 남긴 경우도 지워지지 않아야 한다
    sample_bean = next(b for b in beans.list(BeanKind.COFFEE) if b.name.startswith("[예시]"))
    mine = brews.create(
        validate_brew(bean=sample_bean, bean_id=sample_bean.id, dose_g="15", water_g="240"),
        brewed_at=NOW,
    )

    assert remove_samples(beans, brews) == 3
    assert {b.id for b in brews.list()} == {real.id, mine.id}
    assert [b.name for b in beans.list(BeanKind.COFFEE)] == ["내 원두"]
    assert beans.list(BeanKind.TEA) == []
    assert not brews.has_samples()
