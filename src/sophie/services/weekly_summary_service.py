"""Computes and persists weekly_summary rows from the underlying plan,
session, canonical_workout and daily_health_summary data. See
docs/DATA_DICTIONARY.md §Daily / weekly derived summaries."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from sophie.db.models import WeeklySummary
from sophie.repositories import planning_repo, summary_repo, workout_repo


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def compute_and_store_weekly_summary(
    session: Session, profile_id: str, week_start: date
) -> WeeklySummary:
    week_end = week_start + timedelta(days=6)

    plan = planning_repo.get_plan_for_week(session, profile_id, week_start)
    planned_distance = None
    planned_count = None
    if plan is not None:
        planned_sessions = [
            s
            for s in planning_repo.list_sessions_for_plan(session, plan.id)
            if s.session_type != "padel"
        ]
        planned_count = len(planned_sessions)
        distances = [s.distance_m for s in planned_sessions if s.distance_m is not None]
        planned_distance = sum(distances) if distances else None

    workouts = [
        w
        for w in workout_repo.list_workouts(session, profile_id)
        if week_start <= w.start_at.date() <= week_end
    ]
    running_workouts = [w for w in workouts if w.activity_type == "run"]
    other_workouts = [w for w in workouts if w.activity_type != "run"]

    run_distances = [w.distance_m for w in running_workouts if w.distance_m is not None]
    actual_distance = sum(run_distances) if run_distances else None
    long_run_distance = max(run_distances) if run_distances else None
    other_minutes_values = [w.duration_s / 60.0 for w in other_workouts if w.duration_s is not None]
    other_minutes = sum(other_minutes_values) if other_minutes_values else None

    daily = summary_repo.list_daily_summaries(session, profile_id, week_start, week_end)
    avg_weight = _avg([d.weight_kg for d in daily if d.weight_kg is not None])
    avg_resting_hr = _avg([d.resting_hr for d in daily if d.resting_hr is not None])
    avg_hrv = _avg([d.hrv_ms for d in daily if d.hrv_ms is not None])
    avg_sleep = _avg([d.sleep_minutes for d in daily if d.sleep_minutes is not None])

    return summary_repo.upsert_weekly_summary(
        session,
        profile_id,
        week_start,
        planned_running_distance_m=planned_distance,
        actual_running_distance_m=actual_distance,
        planned_session_count=planned_count,
        actual_session_count=len(running_workouts) or None,
        long_run_distance_m=long_run_distance,
        other_training_minutes=other_minutes,
        avg_weight_kg=avg_weight,
        avg_resting_hr=avg_resting_hr,
        avg_hrv_ms=avg_hrv,
        avg_sleep_minutes=avg_sleep,
    )
