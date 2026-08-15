"""Centralized unit helpers. Domain/services work in metric internally
(meters, seconds, kg, celsius); formatting for display is a UI concern that
may call into these helpers."""

from __future__ import annotations


def km_to_m(km: float) -> float:
    return km * 1000.0


def m_to_km(m: float) -> float:
    return m / 1000.0


def pace_s_per_km(distance_m: float, duration_s: float) -> float | None:
    if distance_m <= 0 or duration_s <= 0:
        return None
    return duration_s / (distance_m / 1000.0)


def format_pace(pace_s_per_km_value: float | None) -> str:
    if pace_s_per_km_value is None:
        return "—"
    minutes, seconds = divmod(int(round(pace_s_per_km_value)), 60)
    return f"{minutes}:{seconds:02d}/km"


def format_duration(seconds: int | float | None) -> str:
    if seconds is None:
        return "—"
    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def lb_to_kg(lb: float) -> float:
    return lb * 0.45359237


def kg_to_lb(kg: float) -> float:
    return kg / 0.45359237
