"""Sunday Review orchestration — the primary weekly workflow. See
docs/PRODUCT_SPEC.md §45 (Steps A-H) and CLAUDE.md.

This module assembles the sanitized `CoachContext` handed to the coach
(never raw health/calendar data — see docs/PRIVACY.md), and drives
plan creation, approval, and calendar write-back. Calendar windows are
computed elsewhere (sophie.services.calendar_feasibility) and passed in here
as already-ranked `CalendarWindow`/`RejectedWindow` values — this module
never invents availability itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Protocol

from sqlalchemy.orm import Session

from sophie.db.models import Plan
from sophie.domain.coach_types import (
    CalendarWindow,
    CoachContext,
    CoachRecommendation,
    DomainStatus,
    RejectedWindow,
)
from sophie.repositories import planning_repo, profile_repo
from sophie.services import decision_log_service, health_intelligence
from sophie.services.weekly_summary_service import compute_and_store_weekly_summary


@dataclass
class LastWeekSummary:
    planned_km: float | None
    actual_km: float | None
    completion_note: str | None
    completion_ratio: float | None


def _previous_week_start(week_start: date) -> date:
    return week_start - timedelta(days=7)


def summarize_last_week(session: Session, profile_id: str, week_start: date) -> LastWeekSummary:
    prior_start = _previous_week_start(week_start)
    weekly = compute_and_store_weekly_summary(session, profile_id, prior_start)

    planned = weekly.planned_running_distance_m
    actual = weekly.actual_running_distance_m
    ratio = None
    note = None
    if planned and planned > 0:
        ratio = (actual or 0) / planned
        pct = round(ratio * 100)
        note = f"{pct}% of planned distance completed"
    elif actual:
        note = "Unplanned running logged"

    return LastWeekSummary(
        planned_km=(planned / 1000.0) if planned else None,
        actual_km=(actual / 1000.0) if actual else None,
        completion_note=note,
        completion_ratio=ratio,
    )


def _domain_statuses_from_snapshot(
    snapshot: health_intelligence.HealthIntelligenceSnapshot,
) -> list[DomainStatus]:
    return [
        DomainStatus(
            domain="cardiovascular",
            status=snapshot.cardio_trend.overall_trend,
            data_quality=snapshot.cardio_trend.data_quality,
            evidence_summary=str(snapshot.cardio_trend.evidence),
        ),
        DomainStatus(
            domain="aerobic_efficiency",
            status=snapshot.aerobic_efficiency_trend.trend,
            data_quality=snapshot.aerobic_efficiency_trend.data_quality,
        ),
        DomainStatus(
            domain="everyday_movement",
            status=snapshot.movement.status,
            data_quality=snapshot.movement.data_quality,
        ),
        DomainStatus(
            domain="circadian",
            status="tracked"
            if snapshot.circadian.data_quality != "insufficient"
            else "insufficient_data",
            data_quality=snapshot.circadian.data_quality,
        ),
        DomainStatus(
            domain="hearing",
            status="tracked"
            if snapshot.hearing.data_quality != "insufficient"
            else "insufficient_data",
            data_quality=snapshot.hearing.data_quality,
        ),
    ]


def build_coach_context(
    session: Session,
    profile_id: str,
    week_start: date,
    calendar_windows: list[CalendarWindow],
    rejected_windows: list[RejectedWindow],
    as_of_date: date,
) -> CoachContext:
    config = profile_repo.get_config(session, profile_id)
    checkin = planning_repo.get_checkin(session, profile_id, week_start)
    last_week = summarize_last_week(session, profile_id, week_start)
    snapshot = health_intelligence.refresh_all_health_intelligence(session, profile_id, as_of_date)

    current_block_week_number = _infer_block_week_number(session, profile_id, week_start)

    return CoachContext(
        week_start=week_start,
        current_block_week_number=current_block_week_number,
        max_runs_per_week=config.max_runs_per_week,
        padel_weekday=config.padel_weekday,
        race_name=config.race_name,
        race_date=config.race_date,
        weight_goal_kg=config.weight_goal_kg,
        current_weight_kg=config.current_weight_kg,
        last_week_planned_km=last_week.planned_km,
        last_week_actual_km=last_week.actual_km,
        last_week_completion_note=last_week.completion_note,
        training_load_status=snapshot.training_load.status,
        recovery_status=snapshot.recovery.status,
        domain_statuses=_domain_statuses_from_snapshot(snapshot),
        calendar_windows=calendar_windows,
        rejected_windows=rejected_windows,
        pain_0_10=checkin.pain_0_10 if checkin else None,
        pain_location=checkin.pain_location if checkin else None,
        stress_1_5=checkin.stress_1_5 if checkin else None,
        fasting_quality=checkin.fasting_quality if checkin else None,
        weekly_note=checkin.note if checkin else None,
        sophie_memory=config.sophie_memory,
        explicit_exclusions=config.explicit_exclusions or [],
    )


def _infer_block_week_number(session: Session, profile_id: str, week_start: date) -> int:
    """The active block is currently a fixed 4-week cycle counted from the
    first plan ever created for this profile (week 1). A future release may
    let the user pin a specific block start explicitly via Memory/Config;
    for now this keeps the block progressing automatically and predictably.
    """
    plans = planning_repo.list_plans(session, profile_id, limit=1000)
    if not plans:
        return 1
    first_week_start = (
        min(p.week_start for p in plans if p.week_start <= week_start)
        if any(p.week_start <= week_start for p in plans)
        else week_start
    )
    weeks_elapsed = (week_start - first_week_start).days // 7
    return weeks_elapsed + 1


def record_manual_checkin(
    session: Session,
    profile_id: str,
    week_start: date,
    pain_0_10: int | None,
    pain_location: str | None,
    stress_1_5: int | None,
    fasting_quality: str,
    nutrition_quality: str | None,
    alcohol: str | None,
    note: str | None,
) -> None:
    planning_repo.upsert_checkin(
        session,
        profile_id,
        week_start,
        pain_0_10=pain_0_10,
        pain_location=pain_location,
        stress_1_5=stress_1_5,
        fasting_quality=fasting_quality,
        nutrition_quality=nutrition_quality,
        alcohol=alcohol,
        note=note,
    )


class CalendarEventWriter(Protocol):
    """Minimal interface this module needs from a calendar provider — kept
    small and local so this orchestrator doesn't depend on the calendar
    provider's full surface. Adapt a real provider to this shape."""

    def create_event(self, start_at: datetime, end_at: datetime, subject: str) -> str: ...


def create_plan_from_recommendation(
    session: Session,
    profile_id: str,
    week_start: date,
    recommendation: CoachRecommendation,
    llm_used: bool,
    validation_notes: list[str],
) -> Plan:
    plan = planning_repo.create_plan(
        session,
        profile_id,
        week_start,
        state="proposed",
        verdict=recommendation.verdict,
        reasons=recommendation.reasons,
        conservative_alternative=recommendation.conservative_alternative.model_dump(mode="json"),
        coach_note=recommendation.coach_note,
        llm_used=llm_used,
        validation_notes=validation_notes,
    )
    for planned in recommendation.recommended_plan:
        planning_repo.add_session(
            session,
            plan.id,
            date=planned.date,
            time=planned.start_time,
            session_type=planned.session_type,
            purpose=planned.purpose,
            distance_m=(planned.distance_km * 1000.0) if planned.distance_km is not None else None,
            estimated_duration_min=planned.estimated_duration_min,
            note=planned.note,
        )
    return plan


def approve_plan(session: Session, plan_id: str, modified: bool = False) -> Plan:
    plan = planning_repo.get_plan(session, plan_id)
    if plan is None:
        raise ValueError(f"Unknown plan: {plan_id}")
    planning_repo.update_plan_state(session, plan, "modified" if modified else "approved")
    return plan


def reject_plan(session: Session, plan_id: str) -> Plan:
    plan = planning_repo.get_plan(session, plan_id)
    if plan is None:
        raise ValueError(f"Unknown plan: {plan_id}")
    planning_repo.update_plan_state(session, plan, "rejected")
    return plan


def write_plan_to_calendar(session: Session, plan_id: str, writer: CalendarEventWriter) -> int:
    """Only ever called after final user confirmation (Sunday Review Step H).
    Returns the number of events written."""

    plan = planning_repo.get_plan(session, plan_id)
    if plan is None:
        raise ValueError(f"Unknown plan: {plan_id}")

    sessions = planning_repo.list_sessions_for_plan(session, plan_id)
    written = 0
    for planned in sessions:
        if planned.calendar_event_id is not None or planned.time is None:
            continue
        start_at = datetime.combine(planned.date, planned.time)
        duration_min = planned.estimated_duration_min or 60
        end_at = start_at + timedelta(minutes=duration_min)
        subject = f"Sophie: {planned.session_type} — {planned.purpose or ''}".strip()
        event_id = writer.create_event(start_at, end_at, subject)
        planned.calendar_event_id = event_id
        written += 1

    planning_repo.update_plan_state(session, plan, "calendar_written")
    session.flush()
    return written


def finalize_week_decision(
    session: Session,
    profile_id: str,
    week_start: date,
    plan_id: str,
    actual_result_summary: str | None = None,
) -> None:
    plan = planning_repo.get_plan(session, plan_id)
    if plan is None:
        raise ValueError(f"Unknown plan: {plan_id}")
    decision_log_service.record_decision(
        session,
        profile_id,
        week_start,
        verdict=plan.verdict,
        recommended_plan_id=plan.id,
        approved_plan_id=plan.id
        if plan.state in ("approved", "modified", "calendar_written")
        else None,
        actual_result_summary=actual_result_summary,
        training_load_status=None,
        data_quality_summary=None,
        coach_note=plan.coach_note,
        calendar_write_state=plan.state,
    )
