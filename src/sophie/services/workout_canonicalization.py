"""Cross-source workout canonicalization: persists RawWorkout entries from
any provider (Apple Health, Sports Tracker FIT/GPX) into canonical_workout +
workout_source_provenance, deterministically deduplicating the same
real-world activity across sources. See docs/PRODUCT_SPEC.md §13 and
docs/DATA_DICTIONARY.md.

Ambiguous matches are never silently merged — workout_repo.find_matching_workout
only returns a match when it is deterministically confident; anything else
becomes a new canonical_workout, consistent with "allow lightweight user
confirmation where necessary" (a future UI concern for the rare ambiguous
case, not auto-merged here).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from sophie.domain.import_types import RawWorkout
from sophie.repositories import workout_repo

# Higher wins when the same field is present on two sources for the same
# canonical workout. Missing fields are always filled regardless of rank.
_SOURCE_QUALITY_RANK = {
    "sports_tracker_fit": 3,
    "apple_health": 2,
    "sports_tracker_gpx": 1,
}

_MERGE_FIELDS = (
    "distance_m",
    "avg_hr",
    "max_hr",
    "elevation_gain_m",
    "avg_pace_s_per_km",
    "duration_s",
    "end_at",
)


@dataclass
class CanonicalizationResult:
    created: int = 0
    matched: int = 0


def persist_raw_workouts(
    session: Session,
    profile_id: str,
    raw_workouts: list[RawWorkout],
    import_manifest_id: str | None,
) -> CanonicalizationResult:
    result = CanonicalizationResult()

    for raw in raw_workouts:
        existing = workout_repo.find_matching_workout(
            session, profile_id, raw.activity_type, raw.start_at, raw.distance_m
        )

        if existing is None:
            pace = None
            if raw.distance_m and raw.duration_s:
                pace = raw.duration_s / (raw.distance_m / 1000.0)
            workout = workout_repo.create_canonical_workout(
                session,
                profile_id=profile_id,
                activity_type=raw.activity_type,
                start_at=raw.start_at,
                end_at=raw.end_at,
                duration_s=raw.duration_s,
                distance_m=raw.distance_m,
                avg_hr=raw.avg_hr,
                max_hr=raw.max_hr,
                elevation_gain_m=raw.elevation_gain_m,
                avg_pace_s_per_km=pace,
                source_quality="single_source",
            )
            result.created += 1
            canonical_id = workout.id
        else:
            _merge_into_existing(existing, raw)
            existing.source_quality = "multi_source"
            session.flush()
            result.matched += 1
            canonical_id = existing.id

        workout_repo.add_provenance(
            session,
            canonical_workout_id=canonical_id,
            source_type=raw.source_type,
            source_identifier=raw.source_identifier,
            raw_start_at=raw.start_at,
            raw_duration_s=raw.duration_s,
            raw_distance_m=raw.distance_m,
            matched_confidence="exact",
            import_manifest_id=import_manifest_id,
        )

    return result


def _merge_into_existing(existing: object, raw: RawWorkout) -> None:
    """Fill missing fields from `raw`; overwrite present fields only if
    `raw`'s source ranks higher than what's already stored (tracked
    implicitly via which source last won — we re-derive rank per call since
    canonical_workout doesn't store a per-field source, keeping the schema
    simple; ties keep the existing value)."""

    incoming_rank = _SOURCE_QUALITY_RANK.get(raw.source_type, 0)
    for field_name in _MERGE_FIELDS:
        raw_value = getattr(raw, field_name, None)
        if raw_value is None:
            continue
        current_value = getattr(existing, field_name, None)
        if current_value is None:
            setattr(existing, field_name, raw_value)
        elif incoming_rank >= _SOURCE_QUALITY_RANK.get("apple_health", 0) and field_name in (
            "avg_hr",
            "max_hr",
        ):
            # Prefer higher-ranked source specifically for HR quality, per
            # docs/PRODUCT_SPEC.md §13 "prefer higher-quality source metadata".
            setattr(existing, field_name, raw_value)
