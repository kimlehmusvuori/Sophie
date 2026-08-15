"""Shared weather data contract. Pure data — no I/O. See docs/PRIVACY.md:
location is always an explicitly configured coarse point, never derived from
GPS routes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class WeatherDay:
    for_date: date
    temp_c: float | None
    humidity_pct: float | None
    precip_mm: float | None
    wind_kph: float | None
    condition_summary: str | None


@dataclass
class WeatherLocation:
    name: str | None
    lat: float
    lon: float
