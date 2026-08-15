"""Decision Log — view-only weekly record. See docs/PRODUCT_SPEC.md §56."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from sophie.db.models import DecisionLog
from sophie.repositories import planning_repo


def record_decision(
    session: Session,
    profile_id: str,
    week_start: date,
    verdict: str | None,
    recommended_plan_id: str | None,
    approved_plan_id: str | None,
    actual_result_summary: str | None,
    training_load_status: str | None,
    data_quality_summary: str | None,
    coach_note: str | None,
    calendar_write_state: str | None,
) -> DecisionLog:
    return planning_repo.add_decision_log_entry(
        session,
        profile_id=profile_id,
        week_start=week_start,
        verdict=verdict,
        recommended_plan_ref=recommended_plan_id,
        approved_plan_ref=approved_plan_id,
        actual_result_summary=actual_result_summary,
        training_load_status=training_load_status,
        data_quality_summary=data_quality_summary,
        coach_note=coach_note,
        calendar_write_state=calendar_write_state,
    )


def list_decision_log(session: Session, profile_id: str, limit: int = 52) -> list[DecisionLog]:
    return planning_repo.list_decision_log(session, profile_id, limit)
