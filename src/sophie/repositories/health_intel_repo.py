from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from sophie.db.models import (
    AerobicEfficiencyPoint,
    CircadianSummary,
    HearingSummary,
    MovementBaseline,
    RecoverySummary,
    TrainingLoadSummary,
    WellbeingAssessment,
)


def upsert_training_load(
    session: Session, profile_id: str, week_start: date, **fields: object
) -> TrainingLoadSummary:
    row = session.execute(
        select(TrainingLoadSummary).where(
            TrainingLoadSummary.profile_id == profile_id,
            TrainingLoadSummary.week_start == week_start,
        )
    ).scalar_one_or_none()
    if row is None:
        row = TrainingLoadSummary(
            profile_id=profile_id, week_start=week_start, status=fields.get("status", "typical")
        )
        session.add(row)
    for key, value in fields.items():
        if hasattr(row, key):
            setattr(row, key, value)
    session.flush()
    return row


def latest_training_load(session: Session, profile_id: str) -> TrainingLoadSummary | None:
    return session.execute(
        select(TrainingLoadSummary)
        .where(TrainingLoadSummary.profile_id == profile_id)
        .order_by(TrainingLoadSummary.week_start.desc())
        .limit(1)
    ).scalar_one_or_none()


def upsert_recovery(
    session: Session, profile_id: str, day: date, **fields: object
) -> RecoverySummary:
    row = session.execute(
        select(RecoverySummary).where(
            RecoverySummary.profile_id == profile_id, RecoverySummary.day == day
        )
    ).scalar_one_or_none()
    if row is None:
        row = RecoverySummary(profile_id=profile_id, day=day, status=fields.get("status", "normal"))
        session.add(row)
    for key, value in fields.items():
        if hasattr(row, key):
            setattr(row, key, value)
    session.flush()
    return row


def latest_recovery(session: Session, profile_id: str) -> RecoverySummary | None:
    return session.execute(
        select(RecoverySummary)
        .where(RecoverySummary.profile_id == profile_id)
        .order_by(RecoverySummary.day.desc())
        .limit(1)
    ).scalar_one_or_none()


def upsert_circadian(
    session: Session, profile_id: str, week_start: date, **fields: object
) -> CircadianSummary:
    row = session.execute(
        select(CircadianSummary).where(
            CircadianSummary.profile_id == profile_id, CircadianSummary.week_start == week_start
        )
    ).scalar_one_or_none()
    if row is None:
        row = CircadianSummary(profile_id=profile_id, week_start=week_start)
        session.add(row)
    for key, value in fields.items():
        if hasattr(row, key):
            setattr(row, key, value)
    session.flush()
    return row


def add_wellbeing_assessment(session: Session, **fields: object) -> WellbeingAssessment:
    row = WellbeingAssessment(**fields)
    session.add(row)
    session.flush()
    return row


def list_wellbeing_assessments(session: Session, profile_id: str) -> list[WellbeingAssessment]:
    return list(
        session.execute(
            select(WellbeingAssessment)
            .where(WellbeingAssessment.profile_id == profile_id)
            .order_by(WellbeingAssessment.assessed_at)
        ).scalars()
    )


def upsert_hearing_summary(
    session: Session, profile_id: str, period_start: date, period_end: date, **fields: object
) -> HearingSummary:
    row = session.execute(
        select(HearingSummary).where(
            HearingSummary.profile_id == profile_id,
            HearingSummary.period_start == period_start,
            HearingSummary.period_end == period_end,
        )
    ).scalar_one_or_none()
    if row is None:
        row = HearingSummary(
            profile_id=profile_id, period_start=period_start, period_end=period_end
        )
        session.add(row)
    for key, value in fields.items():
        if hasattr(row, key):
            setattr(row, key, value)
    session.flush()
    return row


def add_aerobic_efficiency_points(session: Session, points: list[AerobicEfficiencyPoint]) -> None:
    session.add_all(points)
    session.flush()


def list_aerobic_efficiency_points(
    session: Session, profile_id: str
) -> list[AerobicEfficiencyPoint]:
    return list(
        session.execute(
            select(AerobicEfficiencyPoint)
            .where(AerobicEfficiencyPoint.profile_id == profile_id)
            .order_by(AerobicEfficiencyPoint.week_start)
        ).scalars()
    )


def upsert_movement_baseline(
    session: Session, profile_id: str, week_start: date, **fields: object
) -> MovementBaseline:
    row = session.execute(
        select(MovementBaseline).where(
            MovementBaseline.profile_id == profile_id, MovementBaseline.week_start == week_start
        )
    ).scalar_one_or_none()
    if row is None:
        row = MovementBaseline(profile_id=profile_id, week_start=week_start)
        session.add(row)
    for key, value in fields.items():
        if hasattr(row, key):
            setattr(row, key, value)
    session.flush()
    return row
