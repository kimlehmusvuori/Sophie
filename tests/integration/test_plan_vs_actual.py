from __future__ import annotations

from datetime import date, datetime

from sophie.repositories import planning_repo, profile_repo, workout_repo
from sophie.services.plan_vs_actual import match_plan_to_actuals


def _make_plan_with_session(session, profile_id, session_date, session_type, distance_m):
    plan = planning_repo.create_plan(
        session, profile_id, week_start=date(2026, 8, 17), state="approved"
    )
    planning_repo.add_session(
        session,
        plan.id,
        date=session_date,
        session_type=session_type,
        purpose="test",
        distance_m=distance_m,
        estimated_duration_min=50,
    )
    return plan


def test_completed_session_matches_same_day_workout(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    plan = _make_plan_with_session(db_session, profile.id, date(2026, 8, 22), "easy", 8000)
    workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="easy",
        start_at=datetime(2026, 8, 22, 9, 0),
        distance_m=8100,
    )

    result = match_plan_to_actuals(db_session, plan.id, profile.id)
    assert result.session_results[0].status == "completed"


def test_missed_session_has_no_matching_workout(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    plan = _make_plan_with_session(db_session, profile.id, date(2026, 8, 22), "easy", 8000)

    result = match_plan_to_actuals(db_session, plan.id, profile.id)
    assert result.session_results[0].status == "missed"


def test_moved_session_matches_nearby_day(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    plan = _make_plan_with_session(db_session, profile.id, date(2026, 8, 22), "easy", 8000)
    workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="easy",
        start_at=datetime(2026, 8, 23, 9, 0),
        distance_m=8000,
    )

    result = match_plan_to_actuals(db_session, plan.id, profile.id)
    assert result.session_results[0].status == "moved"


def test_partial_when_actual_much_shorter(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    plan = _make_plan_with_session(db_session, profile.id, date(2026, 8, 22), "long", 15000)
    workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="long",
        start_at=datetime(2026, 8, 22, 9, 0),
        distance_m=6000,
    )

    result = match_plan_to_actuals(db_session, plan.id, profile.id)
    assert result.session_results[0].status == "partial"


def test_ambiguous_when_multiple_candidates(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    plan = _make_plan_with_session(db_session, profile.id, date(2026, 8, 22), "easy", 8000)
    for hour in (7, 18):
        workout_repo.create_canonical_workout(
            db_session,
            profile_id=profile.id,
            activity_type="easy",
            start_at=datetime(2026, 8, 22, hour, 0),
            distance_m=8000,
        )

    result = match_plan_to_actuals(db_session, plan.id, profile.id)
    assert result.session_results[0].status == "ambiguous"
    assert result.session_results[0].matched_workout_id is None


def test_extra_unplanned_workout_reported(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    plan = _make_plan_with_session(db_session, profile.id, date(2026, 8, 22), "easy", 8000)
    workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="easy",
        start_at=datetime(2026, 8, 22, 9, 0),
        distance_m=8000,
    )
    extra = workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="padel",
        start_at=datetime(2026, 8, 21, 18, 0),
        distance_m=None,
    )

    result = match_plan_to_actuals(db_session, plan.id, profile.id)
    assert extra.id in result.extra_unplanned_workout_ids
