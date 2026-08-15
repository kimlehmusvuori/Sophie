"""Safe-language helpers for clinical/laboratory pattern surfacing. See
docs/HEALTH_LOGIC_AND_SAFETY.md §Autoimmune / clinical pattern language.

Only ever use the templates below. Never construct a sentence that names a
specific disease as present, likely, or ruled out.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

_MATERIAL_CHANGE_PCT = 0.20

FORBIDDEN_PATTERNS = (
    "you have",
    "you likely have",
    "diagnos",
    "rule out",
    "rules out",
    "ruled out",
    "does not have",
    "you don't have",
    "prescri",
    "you should take",
    "risk of developing",
    "probability of",
)


@dataclass
class LabPoint:
    sample_date: date
    value: float
    reference_low: float | None
    reference_high: float | None
    abnormal_flag: str | None  # only ever set by the lab itself


def is_outside_reference_range(point: LabPoint) -> bool:
    if point.reference_low is not None and point.value < point.reference_low:
        return True
    if point.reference_high is not None and point.value > point.reference_high:
        return True
    return bool(point.abnormal_flag)


def has_material_change(points: list[LabPoint]) -> bool:
    """True if the most recent value differs from the prior value by more
    than _MATERIAL_CHANGE_PCT, across at least two measurements."""

    ordered = sorted(points, key=lambda p: p.sample_date)
    if len(ordered) < 2:
        return False
    prior, latest = ordered[-2].value, ordered[-1].value
    if prior == 0:
        return False
    return abs(latest - prior) / abs(prior) >= _MATERIAL_CHANGE_PCT


def out_of_range_note(test_name: str) -> str:
    return f"{test_name}: this measurement is outside the supplied laboratory reference interval."


def material_change_note(test_name: str) -> str:
    return f"{test_name}: this marker has changed materially across several measurements."


def clinician_discussion_note() -> str:
    return (
        "Given the combination of longitudinal data and any context you've entered, consider "
        "discussing this pattern with your healthcare professional."
    )


def contains_forbidden_language(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in FORBIDDEN_PATTERNS)
