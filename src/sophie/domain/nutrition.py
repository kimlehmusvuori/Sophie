"""Lightweight, optional nutrition suggestions — a supporting feature, not a
calorie-obsession app or micronutrient dashboard. See docs/PRODUCT_SPEC.md
§41. Lower-carb/paleo-inspired is a *preference*; harder/long sessions permit
targeted carbohydrate fueling."""

from __future__ import annotations

from dataclasses import dataclass

from sophie.domain.training_block import SessionType


@dataclass
class MealIdea:
    name: str
    tags: tuple[str, ...]  # e.g. "gluten_free", "paleo", "high_protein", "fueling"
    ingredients: tuple[str, ...]


MEAL_LIBRARY: list[MealIdea] = [
    MealIdea(
        "Grilled chicken, roasted vegetables, olive oil",
        ("gluten_free", "paleo", "high_protein"),
        ("chicken breast", "broccoli", "sweet potato", "olive oil"),
    ),
    MealIdea(
        "Salmon, spinach and avocado salad",
        ("gluten_free", "paleo", "high_protein"),
        ("salmon fillet", "spinach", "avocado", "lemon"),
    ),
    MealIdea(
        "Beef and vegetable stir-fry (tamari instead of soy sauce)",
        ("gluten_free", "paleo", "high_protein"),
        ("beef strips", "bell pepper", "broccoli", "tamari sauce"),
    ),
    MealIdea(
        "Eggs, smoked salmon and avocado",
        ("gluten_free", "paleo", "high_protein"),
        ("eggs", "smoked salmon", "avocado"),
    ),
    MealIdea(
        "Rice, grilled chicken and banana — pre-long-run fueling",
        ("gluten_free", "fueling"),
        ("white rice", "chicken breast", "banana"),
    ),
    MealIdea(
        "Potatoes, eggs and fruit — post-long-run recovery",
        ("gluten_free", "paleo", "fueling"),
        ("potatoes", "eggs", "berries"),
    ),
    MealIdea(
        "Turkey chili with beans (skip if strict paleo)",
        ("gluten_free", "high_protein"),
        ("ground turkey", "kidney beans", "tomato", "onion"),
    ),
]


def suggest_meals_for_week(
    session_types: list[SessionType], gluten_free: bool, paleo_inspired: bool, count: int = 5
) -> list[MealIdea]:
    """Practical food around the week's sessions: default to paleo/gluten-free
    preference, but include fueling-tagged meals around long/quality days."""

    has_hard_session = SessionType.LONG in session_types or SessionType.QUALITY in session_types

    candidates = [m for m in MEAL_LIBRARY if (not gluten_free or "gluten_free" in m.tags)]
    if paleo_inspired and not has_hard_session:
        preferred = [m for m in candidates if "paleo" in m.tags]
        if preferred:
            candidates = preferred

    if has_hard_session:
        fueling = [m for m in candidates if "fueling" in m.tags]
        rest = [m for m in candidates if "fueling" not in m.tags]
        ordered = fueling + rest
    else:
        ordered = candidates

    return ordered[:count]


def build_shopping_list(meals: list[MealIdea]) -> list[str]:
    seen: dict[str, None] = {}
    for meal in meals:
        for ingredient in meal.ingredients:
            seen.setdefault(ingredient, None)
    return sorted(seen.keys())
