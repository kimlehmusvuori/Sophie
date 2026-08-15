"""Aerobic efficiency proxy — never called "running economy" (a laboratory
metabolic-testing term Sophie cannot measure). Compares pace-to-heart-rate
ratio across reasonably similar easy/steady runs over a trailing window. See
docs/HEALTH_LOGIC_AND_SAFETY.md §Aerobic efficiency proxy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class EfficiencyRun:
    day: date
    pace_s_per_km: float
    avg_hr: float
    duration_min: float
    comparable_group: str = "easy"  # easy/steady — only compare within a group


@dataclass
class EfficiencyPoint:
    day: date
    efficiency_proxy: float  # lower pace-per-heartbeat is "better" (more efficient)


@dataclass
class EfficiencyTrend:
    trend: str  # improving/stable/watch/insufficient_data
    points: list[EfficiencyPoint]
    data_quality: str


_MIN_DURATION_MIN = 20.0
_MIN_RUNS_FOR_TREND = 4


def _proxy(run: EfficiencyRun) -> float:
    # Pace (s/km) per heartbeat: lower is more efficient at the same effort.
    return run.pace_s_per_km / run.avg_hr


def compute_aerobic_efficiency_trend(
    runs: list[EfficiencyRun], comparable_group: str = "easy"
) -> EfficiencyTrend:
    comparable = [
        r
        for r in runs
        if r.comparable_group == comparable_group and r.duration_min >= _MIN_DURATION_MIN
    ]
    comparable.sort(key=lambda r: r.day)
    points = [EfficiencyPoint(day=r.day, efficiency_proxy=round(_proxy(r), 4)) for r in comparable]

    if len(points) < _MIN_RUNS_FOR_TREND:
        return EfficiencyTrend(
            trend="insufficient_data", points=points, data_quality="insufficient"
        )

    half = len(points) // 2
    earlier = [p.efficiency_proxy for p in points[:half]]
    later = [p.efficiency_proxy for p in points[half:]]
    earlier_avg = sum(earlier) / len(earlier)
    later_avg = sum(later) / len(later)

    change_pct = (later_avg - earlier_avg) / earlier_avg if earlier_avg else 0.0
    # Lower proxy value = more efficient, so a negative change is improvement.
    if change_pct <= -0.03:
        trend = "improving"
    elif change_pct >= 0.03:
        trend = "watch"
    else:
        trend = "stable"

    data_quality = "sufficient" if len(points) >= 6 else "limited"
    return EfficiencyTrend(trend=trend, points=points, data_quality=data_quality)
