from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from sophie.db.base import Base, TimestampMixin, UUIDPKMixin


class ManualCheckin(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "manual_checkin"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    pain_0_10: Mapped[int | None] = mapped_column(Integer, default=None)
    pain_location: Mapped[str | None] = mapped_column(String(100), default=None)
    stress_1_5: Mapped[int | None] = mapped_column(Integer, default=None)
    fasting_quality: Mapped[str | None] = mapped_column(String(10), default=None)  # good/mixed/poor
    nutrition_quality: Mapped[str | None] = mapped_column(String(10), default=None)
    alcohol: Mapped[str | None] = mapped_column(String(10), default=None)  # low/medium/high
    note: Mapped[str | None] = mapped_column(default=None)


class Plan(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "plan"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    state: Mapped[str] = mapped_column(String(20), default="proposed")
    verdict: Mapped[str | None] = mapped_column(String(20), default=None)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    conservative_alternative: Mapped[dict | None] = mapped_column(JSON, default=None)
    coach_note: Mapped[str | None] = mapped_column(default=None)
    llm_used: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_notes: Mapped[list] = mapped_column(JSON, default=list)


class Session(Base, UUIDPKMixin):
    __tablename__ = "session"

    plan_id: Mapped[str] = mapped_column(ForeignKey("plan.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    time: Mapped[time | None] = mapped_column(Time, default=None)
    session_type: Mapped[str] = mapped_column(String(20))  # long/quality/easy/padel/other
    purpose: Mapped[str | None] = mapped_column(String(200), default=None)
    distance_m: Mapped[float | None] = mapped_column(Float, default=None)
    estimated_duration_min: Mapped[int | None] = mapped_column(Integer, default=None)
    note: Mapped[str | None] = mapped_column(default=None)
    calendar_event_id: Mapped[str | None] = mapped_column(String(200), default=None)
    matched_workout_id: Mapped[str | None] = mapped_column(
        ForeignKey("canonical_workout.id"), default=None
    )
    completion_status: Mapped[str | None] = mapped_column(
        String(20), default=None
    )  # completed/partial/moved/missed


class CalendarSnapshot(Base, UUIDPKMixin):
    """Busy/free intervals only — never titles, bodies, or attendees."""

    __tablename__ = "calendar_snapshot"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    busy_intervals: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(20), default="mock")  # graph/ics_fallback/mock


class DecisionLog(Base, UUIDPKMixin, TimestampMixin):
    """View-only weekly record for the Decision Log page."""

    __tablename__ = "decision_log"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    verdict: Mapped[str | None] = mapped_column(String(20), default=None)
    recommended_plan_ref: Mapped[str | None] = mapped_column(ForeignKey("plan.id"), default=None)
    approved_plan_ref: Mapped[str | None] = mapped_column(ForeignKey("plan.id"), default=None)
    actual_result_summary: Mapped[str | None] = mapped_column(default=None)
    training_load_status: Mapped[str | None] = mapped_column(String(20), default=None)
    data_quality_summary: Mapped[str | None] = mapped_column(default=None)
    coach_note: Mapped[str | None] = mapped_column(default=None)
    calendar_write_state: Mapped[str | None] = mapped_column(String(20), default=None)
