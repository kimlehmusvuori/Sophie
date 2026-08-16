from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sophie.db.base import Base, TimestampMixin, UUIDPKMixin


class Profile(Base, UUIDPKMixin, TimestampMixin):
    """The single local user. profile_id everywhere else FKs to this row."""

    __tablename__ = "profile"

    display_name: Mapped[str] = mapped_column(String(200), default="Sophie user")
    sex: Mapped[str | None] = mapped_column(String(20), default=None)
    birth_year: Mapped[int | None] = mapped_column(default=None)
    height_cm: Mapped[float | None] = mapped_column(default=None)

    config: Mapped[UserConfig] = relationship(back_populates="profile", uselist=False)


class UserConfig(Base, UUIDPKMixin, TimestampMixin):
    """Editable planning/goal/nutrition config. One row per profile."""

    __tablename__ = "user_config"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), unique=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=None)

    # Goals
    current_weight_kg: Mapped[float | None] = mapped_column(default=None)
    weight_goal_kg: Mapped[float | None] = mapped_column(default=None)
    race_name: Mapped[str | None] = mapped_column(String(200), default=None)
    race_date: Mapped[date | None] = mapped_column(Date, default=None)
    other_goals: Mapped[list] = mapped_column(JSON, default=list)

    # Planning preferences
    max_runs_per_week: Mapped[int] = mapped_column(default=3)
    padel_weekday: Mapped[int | None] = mapped_column(default=3)  # Mon=0 ... Thu=3
    dropoff_start: Mapped[str] = mapped_column(String(5), default="08:00")
    dropoff_end: Mapped[str] = mapped_column(String(5), default="08:30")
    earliest_weekday_session: Mapped[str] = mapped_column(String(5), default="08:45")
    latest_session: Mapped[str] = mapped_column(String(5), default="20:00")
    long_run_weekday_preference: Mapped[list] = mapped_column(
        JSON, default=lambda: ["Saturday", "Sunday", "Friday"]
    )
    preserve_rest_day: Mapped[bool] = mapped_column(default=True)

    # Nutrition preferences
    gluten_free: Mapped[bool] = mapped_column(default=True)
    paleo_inspired: Mapped[bool] = mapped_column(default=True)
    fasting_window: Mapped[str | None] = mapped_column(String(20), default="18:00-11:30")

    # Data source coarse location (weather) — never derived from GPS routes
    weather_location_name: Mapped[str | None] = mapped_column(String(200), default=None)
    weather_lat: Mapped[float | None] = mapped_column(default=None)
    weather_lon: Mapped[float | None] = mapped_column(default=None)

    active_block_name: Mapped[str | None] = mapped_column(String(200), default=None)
    explicit_exclusions: Mapped[list] = mapped_column(JSON, default=list)
    sophie_memory: Mapped[str | None] = mapped_column(default=None)

    # anthropic/openai/xai — which Chat page provider to use by default.
    llm_chat_provider: Mapped[str] = mapped_column(String(20), default="anthropic")

    profile: Mapped[Profile] = relationship(back_populates="config")


class FamilyHistoryItem(Base, UUIDPKMixin, TimestampMixin):
    """Optional, private, context-only. Never a diagnostic input — see
    docs/HEALTH_LOGIC_AND_SAFETY.md."""

    __tablename__ = "family_history_item"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"))
    category: Mapped[str] = mapped_column(
        String(50)
    )  # cardiovascular/diabetes/autoimmune_inflammatory/other
    note: Mapped[str | None] = mapped_column(default=None)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=None)
