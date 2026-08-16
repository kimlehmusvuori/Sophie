"""Backing service for the Trends dashboard page: simple time-series +
trailing average per area (training, sleep, weight, resting heart rate,
HRV/recovery), bucketed by a user-chosen Week/Month/Year view. No composite
score — each metric stays a separate, literal number (see
docs/HEALTH_LOGIC_AND_SAFETY.md, "no composite health score").

Missing days are excluded from the average, never zero-filled, for every
metric except training distance, where a day with no workout is a genuine
zero (see sophie.db.models.summaries.DailyHealthSummary docstring: "absence
is meaningful and must be shown as such, never silently zero-filled").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from sophie.repositories import summary_repo, workout_repo

TIMEFRAMES: dict[str, int] = {"Week": 7, "Month": 30, "Year": 365}


@dataclass(frozen=True)
class _MetricSpec:
    label: str
    unit: str
    attr: str | None = None  # None only for "training", which is computed from workouts
    scale: float = 1.0


_METRIC_SPECS: dict[str, _MetricSpec] = {
    "training": _MetricSpec(label="Training distance", unit="km/day"),
    "sleep": _MetricSpec(
        label="Sleep duration", unit="hours/night", attr="sleep_minutes", scale=1 / 60
    ),
    "weight": _MetricSpec(label="Weight", unit="kg", attr="weight_kg"),
    "resting_hr": _MetricSpec(label="Resting heart rate", unit="bpm", attr="resting_hr"),
    "hrv": _MetricSpec(label="HRV (recovery)", unit="ms", attr="hrv_ms"),
}


@dataclass
class MetricPoint:
    day: date
    value: float | None


@dataclass
class MetricSeries:
    key: str
    label: str
    unit: str
    points: list[MetricPoint]
    average: float | None
    days_with_data: int
    window_days: int


def _date_range(since: date, until: date) -> list[date]:
    days = []
    day = since
    while day <= until:
        days.append(day)
        day += timedelta(days=1)
    return days


def _daily_summary_series(
    session: Session, profile_id: str, attr: str, scale: float, since: date, until: date
) -> list[MetricPoint]:
    rows = summary_repo.list_daily_summaries(session, profile_id, since, until)
    by_day: dict[date, float | None] = {row.day: getattr(row, attr) for row in rows}
    points = []
    for day in _date_range(since, until):
        raw = by_day.get(day)
        points.append(MetricPoint(day=day, value=raw * scale if raw is not None else None))
    return points


def _training_distance_series(
    session: Session, profile_id: str, since: date, until: date
) -> list[MetricPoint]:
    # Mirrors the safe pattern in weekly_summary_service.py: fetch once, filter/aggregate
    # in Python by plain `date` comparison — sidesteps any naive/aware datetime pitfalls
    # entirely (see docs/DECISIONS.md on SQLite's lack of tz-aware storage).
    workouts = workout_repo.list_workouts(session, profile_id)
    by_day: dict[date, float] = {}
    for workout in workouts:
        day = workout.start_at.date()
        if since <= day <= until:
            by_day[day] = by_day.get(day, 0.0) + (workout.distance_m or 0.0) / 1000.0
    return [
        MetricPoint(day=day, value=round(by_day.get(day, 0.0), 2))
        for day in _date_range(since, until)
    ]


def _bucket_weekly(points: list[MetricPoint]) -> list[MetricPoint]:
    """Collapses a long daily series into one point per ISO week (mean of
    available values within that week) — used for the Year view so the
    chart stays readable at ~52 points instead of ~365."""
    buckets: dict[date, list[float]] = {}
    order: list[date] = []
    for point in points:
        week_start = point.day - timedelta(days=point.day.weekday())
        if week_start not in buckets:
            buckets[week_start] = []
            order.append(week_start)
        if point.value is not None:
            buckets[week_start].append(point.value)
    return [
        MetricPoint(
            day=week_start,
            value=round(sum(buckets[week_start]) / len(buckets[week_start]), 2)
            if buckets[week_start]
            else None,
        )
        for week_start in order
    ]


def get_metric_series(
    session: Session, profile_id: str, metric_key: str, timeframe: str, today: date | None = None
) -> MetricSeries:
    today = today or date.today()
    window_days = TIMEFRAMES[timeframe]
    since = today - timedelta(days=window_days - 1)
    spec = _METRIC_SPECS[metric_key]

    if metric_key == "training" or spec.attr is None:
        points = _training_distance_series(session, profile_id, since, today)
    else:
        points = _daily_summary_series(session, profile_id, spec.attr, spec.scale, since, today)

    present = [p.value for p in points if p.value is not None]
    average = round(sum(present) / len(present), 2) if present else None
    display_points = _bucket_weekly(points) if timeframe == "Year" else points

    return MetricSeries(
        key=metric_key,
        label=spec.label,
        unit=spec.unit,
        points=display_points,
        average=average,
        days_with_data=len(present),
        window_days=window_days,
    )


def get_all_metric_series(
    session: Session, profile_id: str, timeframe: str, today: date | None = None
) -> list[MetricSeries]:
    return [get_metric_series(session, profile_id, key, timeframe, today) for key in _METRIC_SPECS]
