from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from sophie.db.base import Base, TimestampMixin, UUIDPKMixin


class CanonicalWorkout(Base, UUIDPKMixin, TimestampMixin):
    """One row per real-world activity, deduplicated across sources."""

    __tablename__ = "canonical_workout"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    activity_type: Mapped[str] = mapped_column(
        String(50)
    )  # run/padel/cycling/tennis/strength/other
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    duration_s: Mapped[int | None] = mapped_column(Integer, default=None)
    distance_m: Mapped[float | None] = mapped_column(Float, default=None)
    avg_hr: Mapped[float | None] = mapped_column(Float, default=None)
    max_hr: Mapped[float | None] = mapped_column(Float, default=None)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float, default=None)
    avg_pace_s_per_km: Mapped[float | None] = mapped_column(Float, default=None)
    source_quality: Mapped[str] = mapped_column(String(30), default="single_source")
    notes: Mapped[str | None] = mapped_column(default=None)


class WorkoutSourceProvenance(Base, UUIDPKMixin):
    """Which raw source(s) contributed to a canonical workout, for dedup audit."""

    __tablename__ = "workout_source_provenance"

    canonical_workout_id: Mapped[str] = mapped_column(
        ForeignKey("canonical_workout.id"), index=True
    )
    source_type: Mapped[str] = mapped_column(
        String(30)
    )  # apple_health/sports_tracker_fit/sports_tracker_gpx
    source_identifier: Mapped[str | None] = mapped_column(String(200), default=None)
    raw_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    raw_duration_s: Mapped[int | None] = mapped_column(Integer, default=None)
    raw_distance_m: Mapped[float | None] = mapped_column(Float, default=None)
    matched_confidence: Mapped[str] = mapped_column(
        String(20), default="exact"
    )  # exact/high/user_confirmed
    import_manifest_id: Mapped[str | None] = mapped_column(
        ForeignKey("import_manifest.id"), default=None
    )
