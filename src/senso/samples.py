"""예시 데이터. 처음 쓰는 사람이 앱을 둘러볼 수 있게 한다.

예시는 is_sample=1로 저장해 실제 기록과 구분하고, 한 번에 지울 수 있다.
"""

from datetime import datetime, timedelta

from senso.db.bean_repo import BeanRepository
from senso.db.brew_repo import BrewRepository
from senso.domain.bean import BeanKind, validate_bean
from senso.domain.brew import validate_brew


def add_samples(beans: BeanRepository, brews: BrewRepository, now: datetime) -> int:
    """예시 원두 1개·차 1개와 기록 3개를 넣고, 넣은 기록 수를 돌려준다."""
    coffee = beans.create(
        validate_bean(
            BeanKind.COFFEE,
            "[예시] 에티오피아 예가체프",
            "예시 로스터리",
            roast_level="light",
            today=now.date(),
        ),
        is_sample=True,
    )
    tea = beans.create(
        validate_bean(BeanKind.TEA, "[예시] 제주 세작", "예시 다원", tea_type="green"),
        is_sample=True,
    )

    first = brews.create(
        validate_brew(
            bean=coffee,
            bean_id=coffee.id,
            dose_g="15",
            water_g="250",
            temp_c="93",
            grind="중간",
            time="2:40",
            dripper="V60",
            grinder="핸드밀",
            desired_flavors=["과일", "산뜻함"],
            scores={"acidity": 5, "bitterness": 2, "sweetness": 2, "body": 2, "satisfaction": 3},
            tasting_notes="과일 향은 좋은데 신맛이 너무 튀었다",
            next_wish=["less_acid"],
        ),
        brewed_at=now - timedelta(days=2, hours=1),
        is_sample=True,
    )
    brews.create(
        validate_brew(
            bean=coffee,
            bean_id=coffee.id,
            dose_g="15",
            water_g="250",
            temp_c="93",
            grind="중간보다 조금 곱게",
            time="2:55",
            dripper="V60",
            grinder="핸드밀",
            desired_flavors=["과일", "단맛"],
            scores={"acidity": 3, "bitterness": 2, "sweetness": 4, "body": 3, "satisfaction": 4},
            tasting_notes="산미가 둥글어지고 단맛이 올라왔다",
            next_wish=["keep"],
            based_on_brew_id=first.id,
        ),
        brewed_at=now - timedelta(days=1, hours=2),
        is_sample=True,
    )
    brews.create(
        validate_brew(
            bean=tea,
            bean_id=tea.id,
            dose_g="3",
            water_g="150",
            temp_c="80",
            time="2:00",
            dripper="다관",
            desired_flavors=["구수함"],
        ),
        brewed_at=now - timedelta(hours=3),
        is_sample=True,
    )
    return 3


def remove_samples(beans: BeanRepository, brews: BrewRepository) -> int:
    count = brews.delete_samples()
    beans.soft_delete_samples()
    return count
