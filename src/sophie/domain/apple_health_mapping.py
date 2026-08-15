"""Apple Health record-type -> Sophie daily-summary-field mapping. This is
the single source of truth for how each HKQuantityTypeIdentifier /
HKCategoryTypeIdentifier is (or deliberately isn't) used, so the metric
catalogue (docs/PRODUCT_SPEC.md §10) and the daily-summary import (§15) never
drift apart.

Adding a newly-recognized-but-not-yet-used type: add it here with
``field=None`` and an appropriate status — it will show up in the catalogue
as "recognized_unused" without needing any parser changes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class QuantityMapping:
    friendly_name: str
    field: str | None  # DailyHealthSummary column name, or None if unused
    aggregation: str  # avg/sum/last
    status: str  # actively_used/stored_aggregate/recognized_unused/deliberately_excluded
    # Convert a value expressed in `unit` (as given in the Record) to the
    # canonical unit Sophie stores internally. Identity if None.
    unit_converters: dict[str, Callable[[float], float]] | None = None


def _identity(x: float) -> float:
    return x


def _lb_to_kg(x: float) -> float:
    return x * 0.45359237


def _km_to_m(x: float) -> float:
    return x * 1000.0


def _mi_to_m(x: float) -> float:
    return x * 1609.344


def _fraction_to_pct(x: float) -> float:
    return x * 100.0 if x <= 1.0 else x


QUANTITY_TYPE_MAP: dict[str, QuantityMapping] = {
    "HKQuantityTypeIdentifierBodyMass": QuantityMapping(
        "Body mass", "weight_kg", "last", "actively_used", {"kg": _identity, "lb": _lb_to_kg}
    ),
    "HKQuantityTypeIdentifierStepCount": QuantityMapping(
        "Step count", "steps", "sum", "actively_used", {"count": _identity}
    ),
    "HKQuantityTypeIdentifierDistanceWalkingRunning": QuantityMapping(
        "Walking + running distance",
        "walking_running_distance_m",
        "sum",
        "actively_used",
        {"km": _km_to_m, "mi": _mi_to_m, "m": _identity},
    ),
    "HKQuantityTypeIdentifierActiveEnergyBurned": QuantityMapping(
        "Active energy", "active_energy_kcal", "sum", "actively_used", {"kcal": _identity}
    ),
    "HKQuantityTypeIdentifierAppleExerciseTime": QuantityMapping(
        "Exercise minutes", "exercise_minutes", "sum", "actively_used", {"min": _identity}
    ),
    "HKQuantityTypeIdentifierRestingHeartRate": QuantityMapping(
        "Resting heart rate",
        "resting_hr",
        "avg",
        "actively_used",
        {"count/min": _identity},
    ),
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": QuantityMapping(
        "Heart rate variability (SDNN)", "hrv_ms", "avg", "actively_used", {"ms": _identity}
    ),
    "HKQuantityTypeIdentifierRespiratoryRate": QuantityMapping(
        "Respiratory rate",
        "respiratory_rate",
        "avg",
        "actively_used",
        {"count/min": _identity},
    ),
    "HKQuantityTypeIdentifierOxygenSaturation": QuantityMapping(
        "Oxygen saturation (SpO2)", "spo2_pct", "avg", "actively_used", {"%": _fraction_to_pct}
    ),
    "HKQuantityTypeIdentifierAppleSleepingWristTemperature": QuantityMapping(
        "Wrist temperature (sleeping)",
        "wrist_temp_deviation_c",
        "avg",
        "actively_used",
        {"degC": _identity},
    ),
    "HKQuantityTypeIdentifierVO2Max": QuantityMapping(
        "VO2 max / Cardio Fitness", "vo2_max", "avg", "actively_used", {"mL/min·kg": _identity}
    ),
    "HKQuantityTypeIdentifierTimeInDaylight": QuantityMapping(
        "Time in daylight", "daylight_minutes", "sum", "actively_used", {"min": _identity}
    ),
    "HKQuantityTypeIdentifierDietaryEnergyConsumed": QuantityMapping(
        "Dietary energy", "dietary_energy_kcal", "sum", "actively_used", {"kcal": _identity}
    ),
    "HKQuantityTypeIdentifierDietaryProtein": QuantityMapping(
        "Dietary protein", "protein_g", "sum", "actively_used", {"g": _identity}
    ),
    "HKQuantityTypeIdentifierDietaryCarbohydrates": QuantityMapping(
        "Dietary carbohydrates", "carbs_g", "sum", "actively_used", {"g": _identity}
    ),
    "HKQuantityTypeIdentifierDietaryFatTotal": QuantityMapping(
        "Dietary total fat", "fat_g", "sum", "actively_used", {"g": _identity}
    ),
    "HKQuantityTypeIdentifierHeadphoneAudioExposure": QuantityMapping(
        "Headphone audio exposure",
        "headphone_audio_db",
        "avg",
        "actively_used",
        {"dBASPL": _identity},
    ),
    "HKQuantityTypeIdentifierEnvironmentalAudioExposure": QuantityMapping(
        "Environmental audio exposure",
        "environmental_audio_db",
        "avg",
        "actively_used",
        {"dBASPL": _identity},
    ),
    # Deliberately excluded per docs/ROADMAP.md — recognized, never processed into
    # a daily field, never surfaced as a feature.
    "HKQuantityTypeIdentifierWalkingAsymmetryPercentage": QuantityMapping(
        "Walking asymmetry", None, "avg", "deliberately_excluded", None
    ),
    "HKQuantityTypeIdentifierWalkingDoubleSupportPercentage": QuantityMapping(
        "Walking double support time", None, "avg", "deliberately_excluded", None
    ),
    "HKQuantityTypeIdentifierWalkingSpeed": QuantityMapping(
        "Walking speed", None, "avg", "deliberately_excluded", None
    ),
    "HKQuantityTypeIdentifierWalkingStepLength": QuantityMapping(
        "Walking step length", None, "avg", "deliberately_excluded", None
    ),
}

CATEGORY_TYPE_SLEEP = "HKCategoryTypeIdentifierSleepAnalysis"
CATEGORY_TYPE_MINDFULNESS = "HKCategoryTypeIdentifierMindfulSession"

SLEEP_ASLEEP_VALUES = {
    "HKCategoryValueSleepAnalysisAsleep",
    "HKCategoryValueSleepAnalysisAsleepCore",
    "HKCategoryValueSleepAnalysisAsleepDeep",
    "HKCategoryValueSleepAnalysisAsleepREM",
    "HKCategoryValueSleepAnalysisAsleepUnspecified",
}


def friendly_name_for(record_type: str) -> str:
    if record_type in QUANTITY_TYPE_MAP:
        return QUANTITY_TYPE_MAP[record_type].friendly_name
    if record_type == CATEGORY_TYPE_SLEEP:
        return "Sleep analysis"
    if record_type == CATEGORY_TYPE_MINDFULNESS:
        return "Mindful session"
    # Fall back to a readable version of the raw identifier.
    return record_type.replace("HKQuantityTypeIdentifier", "").replace(
        "HKCategoryTypeIdentifier", ""
    )
