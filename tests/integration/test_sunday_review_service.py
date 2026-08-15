from __future__ import annotations

from datetime import date, datetime, time

from sophie.domain.coach_types import CalendarWindow
from sophie.domain.training_block import SessionType
from sophie.repositories import planning_repo, profile_repo, workout_repo
from sophie.services import sunday_review


def test_build_coach_context_with_no_prior_data(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    windows = [
        CalendarWindow(
            date=date(2026, 8, 22),
            start=time(9, 0),
            end=time(10, 0),
            weekday_name="Saturday",
            rank_score=0.9,
        )
    ]
    context = sunday_review.build_coach_context(
        db_session, profile.id, date(2026, 8, 17), windows, [], as_of_date=date(2026, 8, 16)
    )
    assert context.max_runs_per_week == 3
    assert context.training_load_status == "typical"
    assert context.recovery_status == "normal"
    assert context.calendar_windows == windows


def test_manual_checkin_flows_into_context(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    sunday_review.record_manual_checkin(
        db_session,
        profile.id,
        date(2026, 8, 17),
        pain_0_10=2,
        pain_location="left knee",
        stress_1_5=3,
        fasting_quality="good",
        nutrition_quality=None,
        alcohol="low",
        note="Feeling good",
    )
    context = sunday_review.build_coach_context(
        db_session, profile.id, date(2026, 8, 17), [], [], as_of_date=date(2026, 8, 16)
    )
    assert context.pain_0_10 == 2
    assert context.weekly_note == "Feeling good"


def test_plan_lifecycle_create_approve_write_and_decision_log(db_session):
    from sophie.domain.coach_types import (
        CoachRecommendation,
        ConservativeAlternative,
        RecommendedSession,
        Verdict,
    )

    profile = profile_repo.get_or_create_profile(db_session)
    recommendation = CoachRecommendation(
        verdict=Verdict.BUILD,
        reasons=["all clear"],
        recommended_plan=[
            RecommendedSession(
                date=date(2026, 8, 22),
                start_time=time(9, 0),
                session_type=SessionType.EASY,
                purpose="Easy run",
                distance_km=8,
                estimated_duration_min=50,
            )
        ],
        conservative_alternative=ConservativeAlternative(summary="lighter", sessions=[]),
    )

    plan = sunday_review.create_plan_from_recommendation(
        db_session,
        profile.id,
        date(2026, 8, 17),
        recommendation,
        llm_used=False,
        validation_notes=[],
    )
    assert plan.state == "proposed"

    sunday_review.approve_plan(db_session, plan.id, modified=False)
    plan = planning_repo.get_plan(db_session, plan.id)
    assert plan.state == "approved"

    class _FakeWriter:
        def create_event(self, start_at, end_at, subject):
            return "event-123"

    written = sunday_review.write_plan_to_calendar(db_session, plan.id, _FakeWriter())
    assert written == 1
    plan = planning_repo.get_plan(db_session, plan.id)
    assert plan.state == "calendar_written"

    sunday_review.finalize_week_decision(
        db_session, profile.id, date(2026, 8, 17), plan.id, "1/1 completed"
    )
    from sophie.services import decision_log_service

    entries = decision_log_service.list_decision_log(db_session, profile.id)
    assert len(entries) == 1
    assert entries[0].calendar_write_state == "calendar_written"


def test_summarize_last_week_with_actual_workouts(db_session):
    prior_week_start = date(2026, 8, 10)
    profile = profile_repo.get_or_create_profile(db_session)
    plan = planning_repo.create_plan(db_session, profile.id, prior_week_start, state="approved")
    planning_repo.add_session(
        db_session, plan.id, date=date(2026, 8, 12), session_type="easy", distance_m=10000
    )
    planning_repo.add_session(
        db_session, plan.id, date=date(2026, 8, 15), session_type="long", distance_m=15000
    )
    workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="run",
        start_at=datetime(2026, 8, 12, 9, 0),
        distance_m=10000,
    )
    workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="run",
        start_at=datetime(2026, 8, 15, 9, 0),
        distance_m=10000,
    )

    result = sunday_review.summarize_last_week(db_session, profile.id, date(2026, 8, 17))
    assert result.planned_km == 25.0
    assert result.actual_km == 20.0
    assert result.completion_ratio == 0.8
