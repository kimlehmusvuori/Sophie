"""Circadian / sleep-regularity context — goes beyond average sleep duration.
Long-term health/recovery context, not a precise daily readiness instruction.
See docs/HEALTH_LOGIC_AND_SAFETY.md."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, time


@dataclass
class NightlySleep:
    day: date
    bedtime_minutes_from_midnight: (
        float | None
    )  # can be negative for pre-midnight bedtimes if normalized
    waketime_minutes_from_midnight: float | None
    sleep_minutes: float | None
    daylight_minutes: float | None = None


@dataclass
class CircadianResult:
    bedtime_variability_min: float | None
    waketime_variability_min: float | None
    sleep_midpoint: time | None
    duration_consistency: float | None  # 0-1, higher = more consistent
    disrupted_nights: int
    avg_daylight_minutes: float | None
    data_quality: str


_DISRUPTION_THRESHOLD_MIN = 180  # a night with < 3h sleep counts as disrupted


def compute_circadian_summary(nights: list[NightlySleep]) -> CircadianResult:
    bedtimes = [
        n.bedtime_minutes_from_midnight
        for n in nights
        if n.bedtime_minutes_from_midnight is not None
    ]
    waketimes = [
        n.waketime_minutes_from_midnight
        for n in nights
        if n.waketime_minutes_from_midnight is not None
    ]
    durations = [n.sleep_minutes for n in nights if n.sleep_minutes is not None]
    daylight = [n.daylight_minutes for n in nights if n.daylight_minutes is not None]

    if len(durations) < 3:
        return CircadianResult(
            bedtime_variability_min=None,
            waketime_variability_min=None,
            sleep_midpoint=None,
            duration_consistency=None,
            disrupted_nights=sum(1 for d in durations if d < _DISRUPTION_THRESHOLD_MIN),
            avg_daylight_minutes=(sum(daylight) / len(daylight)) if daylight else None,
            data_quality="insufficient",
        )

    bedtime_var = statistics.pstdev(bedtimes) if len(bedtimes) >= 3 else None
    waketime_var = statistics.pstdev(waketimes) if len(waketimes) >= 3 else None

    midpoint_val = None
    if bedtimes and waketimes and len(bedtimes) == len(waketimes):
        midpoints = []
        for b, w in zip(bedtimes, waketimes, strict=False):
            wake = w if w >= b else w + 24 * 60
            mid = (b + wake) / 2 % (24 * 60)
            midpoints.append(mid)
        avg_mid = statistics.median(midpoints)
        midpoint_val = time(hour=int(avg_mid // 60) % 24, minute=int(avg_mid % 60))

    mean_duration = statistics.mean(durations)
    stdev_duration = statistics.pstdev(durations)
    consistency = None
    if mean_duration > 0:
        consistency = max(0.0, min(1.0, 1 - (stdev_duration / mean_duration)))

    disrupted = sum(1 for d in durations if d < _DISRUPTION_THRESHOLD_MIN)

    data_quality = "sufficient" if len(durations) >= 7 else "limited"

    return CircadianResult(
        bedtime_variability_min=round(bedtime_var, 1) if bedtime_var is not None else None,
        waketime_variability_min=round(waketime_var, 1) if waketime_var is not None else None,
        sleep_midpoint=midpoint_val,
        duration_consistency=round(consistency, 2) if consistency is not None else None,
        disrupted_nights=disrupted,
        avg_daylight_minutes=(round(sum(daylight) / len(daylight), 1) if daylight else None),
        data_quality=data_quality,
    )
