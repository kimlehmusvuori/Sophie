"""Hearing / noise-exposure context from Apple Health headphone & environmental
audio data. Surfaced at a monthly/quarterly cadence, never a daily dashboard.
These signals relate to *exposure*, not proof of hearing damage — never
phrase this as a hearing-loss diagnosis. See docs/HEALTH_LOGIC_AND_SAFETY.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# WHO/NIOSH-style caution levels for continuous exposure — used only as a
# descriptive threshold for "notably loud", not a diagnostic claim.
_ELEVATED_DB = 80.0
_HIGH_DB = 85.0


@dataclass
class DailyAudioExposure:
    day: date
    headphone_avg_db: float | None
    environmental_avg_db: float | None


@dataclass
class HearingResult:
    headphone_avg_db: float | None
    environmental_avg_db: float | None
    exposure_events: int
    data_quality: str


def summarize_hearing_exposure(days: list[DailyAudioExposure]) -> HearingResult:
    headphone_values = [d.headphone_avg_db for d in days if d.headphone_avg_db is not None]
    environmental_values = [
        d.environmental_avg_db for d in days if d.environmental_avg_db is not None
    ]

    if not headphone_values and not environmental_values:
        return HearingResult(
            headphone_avg_db=None,
            environmental_avg_db=None,
            exposure_events=0,
            data_quality="insufficient",
        )

    events = sum(1 for v in headphone_values + environmental_values if v >= _HIGH_DB)

    data_quality = (
        "sufficient" if (len(headphone_values) + len(environmental_values)) >= 14 else "limited"
    )

    return HearingResult(
        headphone_avg_db=round(sum(headphone_values) / len(headphone_values), 1)
        if headphone_values
        else None,
        environmental_avg_db=(
            round(sum(environmental_values) / len(environmental_values), 1)
            if environmental_values
            else None
        ),
        exposure_events=events,
        data_quality=data_quality,
    )
