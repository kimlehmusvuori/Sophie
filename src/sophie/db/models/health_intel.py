from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from sophie.db.base import Base, UUIDPKMixin


class TrainingLoadSummary(Base, UUIDPKMixin):
    __tablename__ = "training_load_summary"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20))  # low/typical/elevated/very_elevated
    load_ratio: Mapped[float | None] = mapped_column(Float, default=None)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    calculation_version: Mapped[str] = mapped_column(String(10), default="1")
    data_quality: Mapped[str] = mapped_column(String(20), default="sufficient")


class RecoverySummary(Base, UUIDPKMixin):
    __tablename__ = "recovery_summary"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20))  # normal/watch/concern
    signals: Mapped[dict] = mapped_column(JSON, default=dict)
    calculation_version: Mapped[str] = mapped_column(String(10), default="1")
    data_quality: Mapped[str] = mapped_column(String(20), default="sufficient")


class CircadianSummary(Base, UUIDPKMixin):
    __tablename__ = "circadian_summary"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    bedtime_variability_min: Mapped[float | None] = mapped_column(Float, default=None)
    waketime_variability_min: Mapped[float | None] = mapped_column(Float, default=None)
    sleep_midpoint_local: Mapped[str | None] = mapped_column(String(5), default=None)
    duration_consistency: Mapped[float | None] = mapped_column(Float, default=None)
    disrupted_nights: Mapped[int] = mapped_column(Integer, default=0)
    avg_daylight_minutes: Mapped[float | None] = mapped_column(Float, default=None)
    calculation_version: Mapped[str] = mapped_column(String(10), default="1")
    data_quality: Mapped[str] = mapped_column(String(20), default="sufficient")


class WellbeingAssessment(Base, UUIDPKMixin):
    __tablename__ = "wellbeing_assessment"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    instrument: Mapped[str] = mapped_column(String(20), default="WHO-5")
    instrument_version: Mapped[str] = mapped_column(String(20), default="1998-who-euro")
    raw_score: Mapped[int] = mapped_column(Integer)
    percentage_score: Mapped[int] = mapped_column(Integer)
    answers: Mapped[list] = mapped_column(JSON, default=list)


class HearingSummary(Base, UUIDPKMixin):
    __tablename__ = "hearing_summary"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    headphone_avg_db: Mapped[float | None] = mapped_column(Float, default=None)
    environmental_avg_db: Mapped[float | None] = mapped_column(Float, default=None)
    exposure_events: Mapped[int] = mapped_column(Integer, default=0)
    calculation_version: Mapped[str] = mapped_column(String(10), default="1")
    data_quality: Mapped[str] = mapped_column(String(20), default="sufficient")


class AerobicEfficiencyPoint(Base, UUIDPKMixin):
    __tablename__ = "aerobic_efficiency_point"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    workout_id: Mapped[str] = mapped_column(ForeignKey("canonical_workout.id"))
    week_start: Mapped[date] = mapped_column(Date, index=True)
    pace_s_per_km: Mapped[float] = mapped_column(Float)
    avg_hr: Mapped[float] = mapped_column(Float)
    efficiency_proxy: Mapped[float] = mapped_column(Float)
    comparable_group: Mapped[str] = mapped_column(String(20), default="easy")
    calculation_version: Mapped[str] = mapped_column(String(10), default="1")


class MovementBaseline(Base, UUIDPKMixin):
    __tablename__ = "movement_baseline"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    avg_daily_steps: Mapped[float | None] = mapped_column(Float, default=None)
    personal_baseline_steps: Mapped[float | None] = mapped_column(Float, default=None)
    status: Mapped[str] = mapped_column(String(20), default="insufficient_data")
    data_quality: Mapped[str] = mapped_column(String(20), default="sufficient")
