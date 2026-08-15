"""Shared normalized data contracts between import providers
(apple_health/sports_tracker/clinical) and the import pipeline services that
persist them. Providers never touch SQLAlchemy directly — they return these
plain dataclasses; sophie.services.* repositories persist them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class RawWorkout:
    source_type: str  # apple_health / sports_tracker_fit / sports_tracker_gpx
    source_identifier: str | None
    activity_type: str  # normalized: run/padel/cycling/tennis/strength/other
    start_at: datetime  # timezone-aware, UTC
    end_at: datetime | None
    duration_s: int | None
    distance_m: float | None
    avg_hr: float | None = None
    max_hr: float | None = None
    elevation_gain_m: float | None = None
    raw_activity_name: str | None = None


# Field names below must match sophie.db.models.summaries.DailyHealthSummary columns.
DAILY_SUMMARY_FIELDS = (
    "weight_kg",
    "steps",
    "walking_running_distance_m",
    "active_energy_kcal",
    "exercise_minutes",
    "resting_hr",
    "hrv_ms",
    "sleep_minutes",
    "sleep_efficiency",
    "bedtime_local",
    "waketime_local",
    "respiratory_rate",
    "spo2_pct",
    "wrist_temp_deviation_c",
    "vo2_max",
    "daylight_minutes",
    "dietary_energy_kcal",
    "protein_g",
    "carbs_g",
    "fat_g",
    "mindful_minutes",
    "headphone_audio_db",
    "environmental_audio_db",
)


@dataclass
class DailyQuantitySample:
    day: date
    field: str  # must be one of DAILY_SUMMARY_FIELDS
    value: float
    aggregation: str = "avg"  # avg/sum/last — how the pipeline should combine same-day samples


@dataclass
class MetricCatalogEntry:
    record_type: str
    friendly_name: str
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    count: int
    unit: str | None
    status: str  # actively_used/stored_aggregate/recognized_unused/deliberately_excluded
    sophie_use: str | None = None


@dataclass
class ImportOutcome:
    """Common result shape for any provider import pass."""

    workouts: list[RawWorkout] = field(default_factory=list)
    daily_samples: list[DailyQuantitySample] = field(default_factory=list)
    catalog_entries: list[MetricCatalogEntry] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    records_processed: int = 0


@dataclass
class ParsedLabResult:
    sample_date: date
    test_name: str
    canonical_test_id: str | None
    value: float | None
    value_text: str | None
    unit: str | None
    reference_low: float | None
    reference_high: float | None
    reference_text: str | None
    abnormal_flag: str | None
    category: str
    notes: str | None = None


@dataclass
class ClinicalImportOutcome:
    results: list[ParsedLabResult] = field(default_factory=list)
    requires_confirmation: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass
class ParsedBodyComposition:
    assessed_at: date
    method: str
    provider: str | None
    weight_kg: float | None
    body_fat_pct: float | None
    lean_mass_kg: float | None
    segmental: dict | None
    visceral_metric: float | None
    notes: str | None = None
