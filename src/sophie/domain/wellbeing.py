"""WHO-5 Well-Being Index — official 5-item instrument, ~biweekly cadence.
Source: WHO Regional Office for Europe / Psychiatric Research Unit,
Frederiksborg, 1998 version. Do not alter wording/scoring without bumping
INSTRUMENT_VERSION and updating docs/HEALTH_LOGIC_AND_SAFETY.md."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

INSTRUMENT = "WHO-5"
INSTRUMENT_VERSION = "1998-who-euro"

WHO5_QUESTIONS: list[str] = [
    "I have felt cheerful and in good spirits.",
    "I have felt calm and relaxed.",
    "I have felt active and vigorous.",
    "I woke up feeling fresh and rested.",
    "My daily life has been filled with things that interest me.",
]

# 0 = at no time ... 5 = all of the time, per the official instrument.
WHO5_SCALE: list[str] = [
    "At no time",
    "Some of the time",
    "Less than half of the time",
    "More than half of the time",
    "Most of the time",
    "All of the time",
]

_ASSESSMENT_INTERVAL_DAYS = 14


@dataclass
class WHO5Result:
    raw_score: int
    percentage_score: int


def score_who5(answers: list[int]) -> WHO5Result:
    if len(answers) != 5:
        raise ValueError("WHO-5 requires exactly 5 answers")
    if any(a < 0 or a > 5 for a in answers):
        raise ValueError("Each WHO-5 answer must be between 0 and 5")
    raw = sum(answers)
    return WHO5Result(raw_score=raw, percentage_score=raw * 4)


def is_assessment_due(last_assessed_at: date | None, today: date) -> bool:
    if last_assessed_at is None:
        return True
    return (today - last_assessed_at).days >= _ASSESSMENT_INTERVAL_DAYS


def next_due_date(last_assessed_at: date | None, today: date) -> date:
    if last_assessed_at is None:
        return today
    return last_assessed_at + timedelta(days=_ASSESSMENT_INTERVAL_DAYS)


def wellbeing_trend(scores: list[tuple[date, int]]) -> str:
    """scores: list of (assessed_at, percentage_score), chronological."""
    if len(scores) < 2:
        return "insufficient_data"
    ordered = sorted(scores, key=lambda s: s[0])
    half = max(1, len(ordered) // 2)
    earlier = [s for _, s in ordered[:half]]
    later = [s for _, s in ordered[half:]] or earlier
    earlier_avg = sum(earlier) / len(earlier)
    later_avg = sum(later) / len(later)
    diff = later_avg - earlier_avg
    if diff >= 8:
        return "improving"
    if diff <= -8:
        return "declining"
    return "stable"
