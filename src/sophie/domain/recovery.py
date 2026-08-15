"""Personal-baseline recovery deviation engine. Compares the user against
their own historical range — never a generic population cutoff. Weekly
planning context only; must not become a daily readiness trigger. See
docs/HEALTH_LOGIC_AND_SAFETY.md."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date

SIGNAL_NAMES = (
    "resting_hr",
    "hrv_ms",
    "sleep_minutes",
    "respiratory_rate",
    "wrist_temp_deviation_c",
)

# A signal "deviates" when it is this many of the trailing-baseline's standard
# deviations away from the median, in the unfavorable direction.
_DEVIATION_Z = 1.5


@dataclass
class DailySignals:
    day: date
    resting_hr: float | None = None
    hrv_ms: float | None = None
    sleep_minutes: float | None = None
    respiratory_rate: float | None = None
    wrist_temp_deviation_c: float | None = None


@dataclass
class RecoveryResult:
    status: str  # normal/watch/concern
    data_quality: str
    signals: dict = field(default_factory=dict)
    calculation_version: str = "1"


# direction: +1 means "higher than baseline is unfavorable", -1 means "lower is unfavorable"
_UNFAVORABLE_DIRECTION = {
    "resting_hr": 1,
    "hrv_ms": -1,
    "sleep_minutes": -1,
    "respiratory_rate": 1,
    "wrist_temp_deviation_c": 1,
}


def _baseline_stats(history: list[DailySignals], field_name: str) -> tuple[float, float] | None:
    values = [getattr(d, field_name) for d in history if getattr(d, field_name) is not None]
    if len(values) < 7:
        return None
    return statistics.median(values), statistics.pstdev(values) or 1.0


def compute_recovery(today: DailySignals, history: list[DailySignals]) -> RecoveryResult:
    """`history` should be the trailing ~60-90 days *excluding* `today`."""

    signal_report: dict[str, dict] = {}
    deviated = 0
    available = 0

    for name in SIGNAL_NAMES:
        today_value = getattr(today, name)
        stats = _baseline_stats(history, name)
        if today_value is None or stats is None:
            signal_report[name] = {"available": False}
            continue
        available += 1
        median, stdev = stats
        z = (today_value - median) / stdev if stdev else 0.0
        direction = _UNFAVORABLE_DIRECTION[name]
        is_deviated = (z * direction) >= _DEVIATION_Z
        if is_deviated:
            deviated += 1
        signal_report[name] = {
            "available": True,
            "value": today_value,
            "baseline_median": round(median, 2),
            "z_vs_baseline": round(z, 2),
            "deviated": is_deviated,
        }

    if available < 2:
        return RecoveryResult(
            status="normal",
            data_quality="insufficient",
            signals=signal_report,
        )

    data_quality = "sufficient" if available >= 3 else "limited"

    if deviated >= 3 or (deviated >= 2 and available <= 2):
        status = "concern"
    elif deviated >= 2:
        status = "watch"
    else:
        status = "normal"

    return RecoveryResult(status=status, data_quality=data_quality, signals=signal_report)
