"""Everyday movement (steps/walking/active energy) vs. structured exercise.
Uses a personal baseline rather than an arbitrary 10,000-step target. See
docs/HEALTH_LOGIC_AND_SAFETY.md."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date


@dataclass
class DailySteps:
    day: date
    steps: float | None


@dataclass
class MovementResult:
    avg_daily_steps: float | None
    personal_baseline_steps: float | None
    status: str  # below_baseline/at_baseline/above_baseline/insufficient_data
    data_quality: str


def compute_movement_baseline(
    recent_week: list[DailySteps], trailing_history: list[DailySteps]
) -> MovementResult:
    recent_values = [d.steps for d in recent_week if d.steps is not None]
    baseline_values = [d.steps for d in trailing_history if d.steps is not None]

    if len(baseline_values) < 14 or not recent_values:
        return MovementResult(
            avg_daily_steps=(sum(recent_values) / len(recent_values)) if recent_values else None,
            personal_baseline_steps=None,
            status="insufficient_data",
            data_quality="insufficient",
        )

    avg_recent = sum(recent_values) / len(recent_values)
    baseline = statistics.median(baseline_values)

    if avg_recent < baseline * 0.85:
        status = "below_baseline"
    elif avg_recent > baseline * 1.15:
        status = "above_baseline"
    else:
        status = "at_baseline"

    return MovementResult(
        avg_daily_steps=round(avg_recent),
        personal_baseline_steps=round(baseline),
        status=status,
        data_quality="sufficient" if len(baseline_values) >= 30 else "limited",
    )
