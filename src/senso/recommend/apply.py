"""제안을 새 기록의 초기값으로 바꾼다 ('이 레시피로 새 기록')."""

from senso.domain.brew import Brew, BrewDraft, Tasting
from senso.recommend.engine import Recommendation


def draft_from_recommendation(brew: Brew, rec: Recommendation, rec_id: int) -> BrewDraft:
    """이전 기록은 그대로 두고 새 기록을 만든다.

    - 레시피는 제안을 반영한 값, 원두·도구·원했던 맛은 이전 기록 그대로
    - 시음 평가는 복사하지 않는다 (새로 마셔 보고 남겨야 하므로)
    - 분쇄도처럼 방향만 제안한 경우는 메모에 남겨 추출할 때 보이게 한다
    - 어떤 기록과 제안을 참고했는지 연결 정보를 남긴다
    """
    notes = brew.notes
    if rec.direction_only:
        hint = f"[제안] {rec.field_label} {rec.to_value} (이전: {rec.from_value})"
        notes = f"{hint}\n{notes}" if notes else hint
    return BrewDraft(
        bean_id=brew.bean_id,
        bean=brew.bean,
        recipe=rec.new_recipe,
        desired_flavors=brew.desired_flavors,
        iced=brew.iced,
        dripper=brew.dripper,
        grinder=brew.grinder,
        notes=notes,
        tasting=Tasting(),
        based_on_brew_id=brew.id,
        based_on_rec_id=rec_id,
    )


def draft_from_brew(brew: Brew) -> BrewDraft:
    """레시피만 새 기록에 복사한다. 과거 평가와 추천 ID는 이어받지 않는다."""
    return BrewDraft(
        bean_id=brew.bean_id,
        bean=brew.bean,
        recipe=brew.recipe,
        desired_flavors=brew.desired_flavors,
        iced=brew.iced,
        dripper=brew.dripper,
        grinder=brew.grinder,
        based_on_brew_id=brew.id,
    )
