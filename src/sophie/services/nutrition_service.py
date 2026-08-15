"""Lightweight nutrition suggestions wired to user preferences and the
current week's plan. See docs/PRODUCT_SPEC.md §41 — supporting feature, not
a calorie-tracking pillar."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from sophie.domain.nutrition import MealIdea, build_shopping_list, suggest_meals_for_week
from sophie.domain.training_block import SessionType
from sophie.repositories import profile_repo


@dataclass
class WeeklyNutritionSuggestion:
    meals: list[MealIdea]
    shopping_list: list[str]


def suggest_weekly_nutrition(
    session: Session, profile_id: str, session_types: list[SessionType]
) -> WeeklyNutritionSuggestion:
    config = profile_repo.get_config(session, profile_id)
    meals = suggest_meals_for_week(
        session_types, gluten_free=config.gluten_free, paleo_inspired=config.paleo_inspired
    )
    return WeeklyNutritionSuggestion(meals=meals, shopping_list=build_shopping_list(meals))
