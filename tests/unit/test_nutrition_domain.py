from __future__ import annotations

from sophie.domain.nutrition import build_shopping_list, suggest_meals_for_week
from sophie.domain.training_block import SessionType


def test_gluten_free_filter_applied():
    meals = suggest_meals_for_week([SessionType.EASY], gluten_free=True, paleo_inspired=True)
    assert all("gluten_free" in m.tags for m in meals)


def test_fueling_meals_prioritized_around_long_run():
    meals = suggest_meals_for_week(
        [SessionType.LONG], gluten_free=True, paleo_inspired=True, count=3
    )
    assert any("fueling" in m.tags for m in meals)


def test_shopping_list_is_deduplicated_and_sorted():
    meals = suggest_meals_for_week(
        [SessionType.EASY], gluten_free=True, paleo_inspired=True, count=10
    )
    shopping = build_shopping_list(meals)
    assert shopping == sorted(set(shopping))
