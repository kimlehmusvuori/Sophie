"""Normalizes provider-specific activity/sport identifiers (Apple Health
HKWorkoutActivityType strings, Garmin/FIT sport codes, Sports Tracker export
labels) onto Sophie's small canonical set used throughout planning and load
calculations."""

from __future__ import annotations

CANONICAL_ACTIVITY_TYPES = ("run", "padel", "cycling", "tennis", "strength", "other")

_APPLE_HEALTH_MAP = {
    "HKWorkoutActivityTypeRunning": "run",
    "HKWorkoutActivityTypeTrackAndField": "run",
    "HKWorkoutActivityTypeCycling": "cycling",
    "HKWorkoutActivityTypeTennis": "tennis",
    "HKWorkoutActivityTypeRacquetball": "padel",
    "HKWorkoutActivityTypePickleball": "padel",
    "HKWorkoutActivityTypeSquash": "padel",
    "HKWorkoutActivityTypeTraditionalStrengthTraining": "strength",
    "HKWorkoutActivityTypeFunctionalStrengthTraining": "strength",
    "HKWorkoutActivityTypeCoreTraining": "strength",
}

_FIT_SPORT_MAP = {
    "running": "run",
    "trail_running": "run",
    "track_running": "run",
    "treadmill_running": "run",
    "cycling": "cycling",
    "tennis": "tennis",
    "padel": "padel",
    "racquetball": "padel",
    "training": "strength",
    "strength_training": "strength",
}

_FREE_TEXT_KEYWORDS = {
    "run": "run",
    "running": "run",
    "jog": "run",
    "padel": "padel",
    "cycling": "cycling",
    "bike": "cycling",
    "tennis": "tennis",
    "strength": "strength",
    "gym": "strength",
    "weights": "strength",
}


def normalize_apple_health_activity(activity_type: str) -> str:
    return _APPLE_HEALTH_MAP.get(activity_type, "other")


def normalize_fit_sport(sport: str | None) -> str:
    if not sport:
        return "other"
    return _FIT_SPORT_MAP.get(sport.lower(), "other")


def normalize_free_text_activity(label: str | None) -> str:
    if not label:
        return "other"
    lowered = label.lower()
    for keyword, canonical in _FREE_TEXT_KEYWORDS.items():
        if keyword in lowered:
            return canonical
    return "other"
