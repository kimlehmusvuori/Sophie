from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from sophie.db.base import Base, UUIDPKMixin


class DailyHealthSummary(Base, UUIDPKMixin):
    """One row per profile per calendar day. All health columns nullable —
    absence is meaningful and must be shown as such, never silently zero-filled."""

    __tablename__ = "daily_health_summary"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)

    weight_kg: Mapped[float | None] = mapped_column(Float, default=None)
    steps: Mapped[int | None] = mapped_column(Integer, default=None)
    walking_running_distance_m: Mapped[float | None] = mapped_column(Float, default=None)
    active_energy_kcal: Mapped[float | None] = mapped_column(Float, default=None)
    exercise_minutes: Mapped[float | None] = mapped_column(Float, default=None)
    resting_hr: Mapped[float | None] = mapped_column(Float, default=None)
    hrv_ms: Mapped[float | None] = mapped_column(Float, default=None)
    sleep_minutes: Mapped[float | None] = mapped_column(Float, default=None)
    sleep_efficiency: Mapped[float | None] = mapped_column(Float, default=None)
    bedtime_local: Mapped[str | None] = mapped_column(String(5), default=None)
    waketime_local: Mapped[str | None] = mapped_column(String(5), default=None)
    respiratory_rate: Mapped[float | None] = mapped_column(Float, default=None)
    spo2_pct: Mapped[float | None] = mapped_column(Float, default=None)
    wrist_temp_deviation_c: Mapped[float | None] = mapped_column(Float, default=None)
    vo2_max: Mapped[float | None] = mapped_column(Float, default=None)
    daylight_minutes: Mapped[float | None] = mapped_column(Float, default=None)
    dietary_energy_kcal: Mapped[float | None] = mapped_column(Float, default=None)
    protein_g: Mapped[float | None] = mapped_column(Float, default=None)
    carbs_g: Mapped[float | None] = mapped_column(Float, default=None)
    fat_g: Mapped[float | None] = mapped_column(Float, default=None)
    mindful_minutes: Mapped[float | None] = mapped_column(Float, default=None)
    headphone_audio_db: Mapped[float | None] = mapped_column(Float, default=None)
    environmental_audio_db: Mapped[float | None] = mapped_column(Float, default=None)


class WeeklySummary(Base, UUIDPKMixin):
    __tablename__ = "weekly_summary"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)

    planned_running_distance_m: Mapped[float | None] = mapped_column(Float, default=None)
    actual_running_distance_m: Mapped[float | None] = mapped_column(Float, default=None)
    planned_session_count: Mapped[int | None] = mapped_column(Integer, default=None)
    actual_session_count: Mapped[int | None] = mapped_column(Integer, default=None)
    long_run_distance_m: Mapped[float | None] = mapped_column(Float, default=None)
    other_training_minutes: Mapped[float | None] = mapped_column(Float, default=None)
    avg_weight_kg: Mapped[float | None] = mapped_column(Float, default=None)
    avg_resting_hr: Mapped[float | None] = mapped_column(Float, default=None)
    avg_hrv_ms: Mapped[float | None] = mapped_column(Float, default=None)
    avg_sleep_minutes: Mapped[float | None] = mapped_column(Float, default=None)
    calculation_version: Mapped[str] = mapped_column(String(10), default="1")
