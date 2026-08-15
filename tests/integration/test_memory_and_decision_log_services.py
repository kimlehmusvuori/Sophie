from __future__ import annotations

from datetime import date

from sophie.domain.training_block import SessionType
from sophie.repositories import profile_repo
from sophie.services import decision_log_service, memory_service, nutrition_service


def test_update_goals_and_snapshot(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    memory_service.update_goals(
        db_session, profile.id, race_name="Half marathon", weight_goal_kg=79.0
    )
    snapshot = memory_service.get_memory_snapshot(db_session, profile.id)
    assert snapshot.config.race_name == "Half marathon"
    assert snapshot.config.weight_goal_kg == 79.0
    assert snapshot.family_history == []


def test_family_history_add_remove(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    item = memory_service.add_family_history(db_session, profile.id, "cardiovascular", "context")
    snapshot = memory_service.get_memory_snapshot(db_session, profile.id)
    assert len(snapshot.family_history) == 1
    memory_service.remove_family_history(db_session, item.id)
    snapshot = memory_service.get_memory_snapshot(db_session, profile.id)
    assert snapshot.family_history == []


def test_sophie_memory_only_updated_explicitly(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    memory_service.update_sophie_memory(db_session, profile.id, "User prefers Saturday long runs.")
    snapshot = memory_service.get_memory_snapshot(db_session, profile.id)
    assert snapshot.config.sophie_memory == "User prefers Saturday long runs."


def test_decision_log_record_and_list(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    decision_log_service.record_decision(
        db_session,
        profile.id,
        week_start=date(2026, 8, 17),
        verdict="build",
        recommended_plan_id=None,
        approved_plan_id=None,
        actual_result_summary="3/3 sessions completed",
        training_load_status="typical",
        data_quality_summary="sufficient",
        coach_note="Good week",
        calendar_write_state="written",
    )
    entries = decision_log_service.list_decision_log(db_session, profile.id)
    assert len(entries) == 1
    assert entries[0].verdict == "build"


def test_nutrition_suggestions_respect_gluten_free_default(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    suggestion = nutrition_service.suggest_weekly_nutrition(
        db_session, profile.id, [SessionType.LONG]
    )
    assert all("gluten_free" in m.tags for m in suggestion.meals)
    assert suggestion.shopping_list == sorted(set(suggestion.shopping_list))
