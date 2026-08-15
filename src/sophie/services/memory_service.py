"""Sophie Memory / Config service — the only path for editing goals,
planning preferences, nutrition preferences, data-source config, family
history, and free-text Sophie memory. See docs/PRODUCT_SPEC.md §53.

Critical rule (CLAUDE.md): LLM inferences must never automatically become
permanent user memory. Only explicit calls from a user-initiated UI action
may reach `update_sophie_memory()` — nothing in the coach/planning pipeline
calls it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from sophie.db.models import FamilyHistoryItem, UserConfig
from sophie.repositories import profile_repo


@dataclass
class MemorySnapshot:
    config: UserConfig
    family_history: list[FamilyHistoryItem]


def get_memory_snapshot(session: Session, profile_id: str) -> MemorySnapshot:
    config = profile_repo.get_config(session, profile_id)
    history = profile_repo.list_family_history(session, profile_id)
    return MemorySnapshot(config=config, family_history=history)


def update_goals(
    session: Session,
    profile_id: str,
    race_name: str | None = None,
    race_date: date | None = None,
    weight_goal_kg: float | None = None,
    current_weight_kg: float | None = None,
) -> UserConfig:
    fields = {
        k: v
        for k, v in {
            "race_name": race_name,
            "race_date": race_date,
            "weight_goal_kg": weight_goal_kg,
            "current_weight_kg": current_weight_kg,
        }.items()
        if v is not None
    }
    return profile_repo.update_config(session, profile_id, **fields)


def update_planning_preferences(session: Session, profile_id: str, **fields: object) -> UserConfig:
    """Accepts any subset of: max_runs_per_week, padel_weekday, dropoff_start,
    dropoff_end, earliest_weekday_session, latest_session,
    long_run_weekday_preference, preserve_rest_day, active_block_name."""
    return profile_repo.update_config(session, profile_id, **fields)


def update_nutrition_preferences(session: Session, profile_id: str, **fields: object) -> UserConfig:
    """Accepts any subset of: gluten_free, paleo_inspired, fasting_window."""
    return profile_repo.update_config(session, profile_id, **fields)


def update_weather_location(
    session: Session,
    profile_id: str,
    location_name: str | None,
    lat: float | None,
    lon: float | None,
) -> UserConfig:
    return profile_repo.update_config(
        session, profile_id, weather_location_name=location_name, weather_lat=lat, weather_lon=lon
    )


def update_explicit_exclusions(
    session: Session, profile_id: str, exclusions: list[str]
) -> UserConfig:
    return profile_repo.update_config(session, profile_id, explicit_exclusions=exclusions)


def update_sophie_memory(session: Session, profile_id: str, memory_text: str | None) -> UserConfig:
    return profile_repo.update_config(session, profile_id, sophie_memory=memory_text)


def add_family_history(
    session: Session, profile_id: str, category: str, note: str | None
) -> FamilyHistoryItem:
    return profile_repo.add_family_history_item(session, profile_id, category, note)


def remove_family_history(session: Session, item_id: str) -> None:
    profile_repo.delete_family_history_item(session, item_id)
