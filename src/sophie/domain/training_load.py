"""Unified training-load / stress-budget layer across running, padel,
strength, cycling, tennis, etc. Transparent relative-load logic against the
user's own recent history — not a scientifically unsupported injury-risk
formula. See docs/HEALTH_LOGIC_AND_SAFETY.md."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

_DEFAULT_INTENSITY_BY_TYPE = {
    "long": 0.80,
    "quality": 1.15,
    "easy": 0.60,
    "padel": 0.90,
    "cycling": 0.65,
    "tennis": 0.85,
    "strength": 0.70,
    "other": 0.55,
}

# Band edges are a documented heuristic, not a clinically validated cutoff.
_LOW_MAX = 0.8
_TYPICAL_MAX = 1.3
_ELEVATED_MAX = 1.6


@dataclass
class LoadSession:
    day: date
    activity_type: str
    duration_min: float
    avg_hr: float | None = None
    hr_reserve_pct: float | None = (
        None  # (avg_hr - resting_hr) / (max_hr - resting_hr), if derivable
    )


@dataclass
class TrainingLoadResult:
    status: str  # low/typical/elevated/very_elevated
    load_ratio: float | None
    data_quality: str  # sufficient/limited/insufficient
    evidence: dict = field(default_factory=dict)
    calculation_version: str = "1"


def _intensity_factor(session: LoadSession) -> float:
    if session.hr_reserve_pct is not None:
        return max(0.3, min(1.5, session.hr_reserve_pct * 1.4))
    return _DEFAULT_INTENSITY_BY_TYPE.get(session.activity_type, 0.6)


def _load_units(session: LoadSession) -> float:
    return session.duration_min * _intensity_factor(session)


def _weekly_load(sessions: list[LoadSession], week_end: date) -> float:
    week_start = week_end - timedelta(days=6)
    return sum(_load_units(s) for s in sessions if week_start <= s.day <= week_end)


def compute_training_load(
    sessions: list[LoadSession], as_of: date, baseline_weeks: int = 4
) -> TrainingLoadResult:
    """Recent 7-day load vs the user's own trailing baseline (mean of the
    `baseline_weeks` 7-day windows preceding the recent week)."""

    recent_load = _weekly_load(sessions, as_of)

    baseline_values: list[float] = []
    for i in range(1, baseline_weeks + 1):
        window_end = as_of - timedelta(days=7 * i)
        week_sessions = [
            s for s in sessions if (window_end - timedelta(days=6)) <= s.day <= window_end
        ]
        if week_sessions:
            baseline_values.append(_weekly_load(sessions, window_end))

    if len(baseline_values) < 2:
        return TrainingLoadResult(
            status="typical",
            load_ratio=None,
            data_quality="insufficient",
            evidence={
                "recent_load_units": round(recent_load, 1),
                "reason": "Fewer than 2 prior weeks of history — no reliable baseline yet.",
            },
        )

    baseline_load = sum(baseline_values) / len(baseline_values)
    if baseline_load <= 0:
        ratio = None
        status = "typical"
        data_quality = "limited"
    else:
        ratio = recent_load / baseline_load
        data_quality = "sufficient"
        if ratio < _LOW_MAX:
            status = "low"
        elif ratio < _TYPICAL_MAX:
            status = "typical"
        elif ratio < _ELEVATED_MAX:
            status = "elevated"
        else:
            status = "very_elevated"

    return TrainingLoadResult(
        status=status,
        load_ratio=round(ratio, 2) if ratio is not None else None,
        data_quality=data_quality,
        evidence={
            "recent_load_units": round(recent_load, 1),
            "baseline_load_units": round(baseline_load, 1),
            "baseline_weeks_used": len(baseline_values),
        },
    )
