from __future__ import annotations

from datetime import date, datetime

from sophie.repositories import planning_repo, profile_repo, workout_repo
from sophie.services.weekly_summary_service import compute_and_store_weekly_summary


def test_compute_weekly_summary_from_plan_and_workouts(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    week_start = date(2026, 8, 10)

    plan = planning_repo.create_plan(db_session, profile.id, week_start, state="approved")
    planning_repo.add_session(
        db_session,
        plan.id,
        date=date(2026, 8, 12),
        session_type="easy",
        distance_m=8000,
        estimated_duration_min=50,
    )
    planning_repo.add_session(
        db_session,
        plan.id,
        date=date(2026, 8, 15),
        session_type="long",
        distance_m=15000,
        estimated_duration_min=90,
    )
    planning_repo.add_session(
        db_session, plan.id, date=date(2026, 8, 13), session_type="padel", estimated_duration_min=75
    )

    workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="run",
        start_at=datetime(2026, 8, 12, 9, 0),
        distance_m=8000,
    )
    workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="run",
        start_at=datetime(2026, 8, 15, 9, 0),
        distance_m=12000,
    )
    workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="padel",
        start_at=datetime(2026, 8, 13, 18, 0),
        duration_s=4500,
    )

    summary = compute_and_store_weekly_summary(db_session, profile.id, week_start)

    assert summary.planned_running_distance_m == 23000
    assert summary.planned_session_count == 2  # padel excluded
    assert summary.actual_running_distance_m == 20000
    assert summary.long_run_distance_m == 12000
    assert summary.other_training_minutes == 75


def test_compute_weekly_summary_with_no_plan_or_workouts(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    summary = compute_and_store_weekly_summary(db_session, profile.id, date(2026, 8, 10))
    assert summary.planned_running_distance_m is None
    assert summary.actual_running_distance_m is None
