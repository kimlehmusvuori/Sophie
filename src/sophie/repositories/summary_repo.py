from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from sophie.db.models import DailyHealthSummary, WeeklySummary


def upsert_daily_summary(
    session: Session, profile_id: str, day: date, **fields: object
) -> DailyHealthSummary:
    row = session.execute(
        select(DailyHealthSummary).where(
            DailyHealthSummary.profile_id == profile_id, DailyHealthSummary.day == day
        )
    ).scalar_one_or_none()
    if row is None:
        row = DailyHealthSummary(profile_id=profile_id, day=day)
        session.add(row)
    for key, value in fields.items():
        if value is not None and hasattr(row, key):
            setattr(row, key, value)
    session.flush()
    return row


def list_daily_summaries(
    session: Session, profile_id: str, since: date, until: date
) -> list[DailyHealthSummary]:
    return list(
        session.execute(
            select(DailyHealthSummary)
            .where(
                DailyHealthSummary.profile_id == profile_id,
                DailyHealthSummary.day >= since,
                DailyHealthSummary.day <= until,
            )
            .order_by(DailyHealthSummary.day)
        ).scalars()
    )


def upsert_weekly_summary(
    session: Session, profile_id: str, week_start: date, **fields: object
) -> WeeklySummary:
    row = session.execute(
        select(WeeklySummary).where(
            WeeklySummary.profile_id == profile_id, WeeklySummary.week_start == week_start
        )
    ).scalar_one_or_none()
    if row is None:
        row = WeeklySummary(profile_id=profile_id, week_start=week_start)
        session.add(row)
    for key, value in fields.items():
        if hasattr(row, key):
            setattr(row, key, value)
    session.flush()
    return row


def list_weekly_summaries(
    session: Session, profile_id: str, limit: int = 12
) -> list[WeeklySummary]:
    return list(
        session.execute(
            select(WeeklySummary)
            .where(WeeklySummary.profile_id == profile_id)
            .order_by(WeeklySummary.week_start.desc())
            .limit(limit)
        ).scalars()
    )[::-1]
