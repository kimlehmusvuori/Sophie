from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from sophie.db.models import CalendarSnapshot, DecisionLog, ManualCheckin, Plan
from sophie.db.models import Session as SessionModel


def upsert_checkin(
    session: Session, profile_id: str, week_start: date, **fields: object
) -> ManualCheckin:
    row = session.execute(
        select(ManualCheckin).where(
            ManualCheckin.profile_id == profile_id, ManualCheckin.week_start == week_start
        )
    ).scalar_one_or_none()
    if row is None:
        row = ManualCheckin(profile_id=profile_id, week_start=week_start)
        session.add(row)
    for key, value in fields.items():
        if hasattr(row, key):
            setattr(row, key, value)
    session.flush()
    return row


def get_checkin(session: Session, profile_id: str, week_start: date) -> ManualCheckin | None:
    return session.execute(
        select(ManualCheckin).where(
            ManualCheckin.profile_id == profile_id, ManualCheckin.week_start == week_start
        )
    ).scalar_one_or_none()


def create_plan(session: Session, profile_id: str, week_start: date, **fields: object) -> Plan:
    plan = Plan(profile_id=profile_id, week_start=week_start, **fields)
    session.add(plan)
    session.flush()
    return plan


def get_plan(session: Session, plan_id: str) -> Plan | None:
    return session.get(Plan, plan_id)


def get_plan_for_week(session: Session, profile_id: str, week_start: date) -> Plan | None:
    return session.execute(
        select(Plan)
        .where(Plan.profile_id == profile_id, Plan.week_start == week_start)
        .order_by(Plan.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def update_plan_state(session: Session, plan: Plan, state: str) -> Plan:
    plan.state = state
    session.flush()
    return plan


def add_session(session: Session, plan_id: str, **fields: object) -> SessionModel:
    row = SessionModel(plan_id=plan_id, **fields)
    session.add(row)
    session.flush()
    return row


def list_sessions_for_plan(session: Session, plan_id: str) -> list[SessionModel]:
    return list(
        session.execute(
            select(SessionModel).where(SessionModel.plan_id == plan_id).order_by(SessionModel.date)
        ).scalars()
    )


def list_plans(session: Session, profile_id: str, limit: int = 20) -> list[Plan]:
    return list(
        session.execute(
            select(Plan)
            .where(Plan.profile_id == profile_id)
            .order_by(Plan.week_start.desc())
            .limit(limit)
        ).scalars()
    )[::-1]


def save_calendar_snapshot(
    session: Session, profile_id: str, week_start: date, busy_intervals: list[dict], source: str
) -> CalendarSnapshot:
    row = CalendarSnapshot(
        profile_id=profile_id,
        week_start=week_start,
        fetched_at=datetime.now(),
        busy_intervals=busy_intervals,
        source=source,
    )
    session.add(row)
    session.flush()
    return row


def add_decision_log_entry(session: Session, **fields: object) -> DecisionLog:
    row = DecisionLog(**fields)
    session.add(row)
    session.flush()
    return row


def list_decision_log(session: Session, profile_id: str, limit: int = 52) -> list[DecisionLog]:
    return list(
        session.execute(
            select(DecisionLog)
            .where(DecisionLog.profile_id == profile_id)
            .order_by(DecisionLog.week_start.desc())
            .limit(limit)
        ).scalars()
    )
