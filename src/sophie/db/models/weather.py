from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from sophie.db.base import Base, UUIDPKMixin


class WeatherSnapshot(Base, UUIDPKMixin):
    """Coarse, user-configured location only — never derived from GPS routes."""

    __tablename__ = "weather_snapshot"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    for_date: Mapped[date] = mapped_column(Date, index=True)
    location_name: Mapped[str | None] = mapped_column(String(200), default=None)
    lat_rounded: Mapped[float | None] = mapped_column(Float, default=None)
    lon_rounded: Mapped[float | None] = mapped_column(Float, default=None)
    temp_c: Mapped[float | None] = mapped_column(Float, default=None)
    humidity_pct: Mapped[float | None] = mapped_column(Float, default=None)
    precip_mm: Mapped[float | None] = mapped_column(Float, default=None)
    wind_kph: Mapped[float | None] = mapped_column(Float, default=None)
    condition_summary: Mapped[str | None] = mapped_column(String(100), default=None)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str] = mapped_column(String(50), default="open-meteo")
