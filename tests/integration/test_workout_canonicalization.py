from __future__ import annotations

from datetime import datetime

from sophie.domain.import_types import RawWorkout
from sophie.repositories import profile_repo, workout_repo
from sophie.services.workout_canonicalization import persist_raw_workouts


def test_new_workout_is_created(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    raw = RawWorkout(
        source_type="apple_health",
        source_identifier="Watch",
        activity_type="run",
        start_at=datetime(2026, 8, 1, 8, 0),
        end_at=datetime(2026, 8, 1, 8, 42),
        duration_s=2520,
        distance_m=10000,
        avg_hr=150,
    )
    result = persist_raw_workouts(db_session, profile.id, [raw], import_manifest_id=None)
    assert result.created == 1
    assert result.matched == 0

    workouts = workout_repo.list_workouts(db_session, profile.id)
    assert workouts[0].avg_pace_s_per_km == 252.0


def test_second_source_fills_missing_fields_and_prefers_higher_quality_hr(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    apple_health_raw = RawWorkout(
        source_type="apple_health",
        source_identifier="Watch",
        activity_type="run",
        start_at=datetime(2026, 8, 1, 8, 0),
        end_at=None,
        duration_s=2520,
        distance_m=10000,
        avg_hr=150,
        elevation_gain_m=None,
    )
    persist_raw_workouts(db_session, profile.id, [apple_health_raw], import_manifest_id=None)

    fit_raw = RawWorkout(
        source_type="sports_tracker_fit",
        source_identifier="fit-1",
        activity_type="run",
        start_at=datetime(2026, 8, 1, 8, 1),  # within match tolerance window
        end_at=datetime(2026, 8, 1, 8, 42),
        duration_s=2520,
        distance_m=10050,
        avg_hr=152,  # higher-quality source should win on HR
        elevation_gain_m=85.0,  # fills a field that was missing
    )
    result = persist_raw_workouts(db_session, profile.id, [fit_raw], import_manifest_id=None)
    assert result.matched == 1

    workouts = workout_repo.list_workouts(db_session, profile.id)
    assert len(workouts) == 1
    merged = workouts[0]
    assert merged.source_quality == "multi_source"
    assert merged.avg_hr == 152  # sports_tracker_fit outranks apple_health for HR
    assert merged.elevation_gain_m == 85.0  # filled from the second source
    assert merged.end_at is not None  # filled from the second source


def test_lower_quality_source_does_not_overwrite_higher_quality_hr(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    fit_raw = RawWorkout(
        source_type="sports_tracker_fit",
        source_identifier="fit-1",
        activity_type="run",
        start_at=datetime(2026, 8, 1, 8, 0),
        end_at=None,
        duration_s=2520,
        distance_m=10000,
        avg_hr=150,
    )
    persist_raw_workouts(db_session, profile.id, [fit_raw], import_manifest_id=None)

    gpx_raw = RawWorkout(
        source_type="sports_tracker_gpx",
        source_identifier="gpx-1",
        activity_type="run",
        start_at=datetime(2026, 8, 1, 8, 1),
        end_at=None,
        duration_s=2520,
        distance_m=10000,
        avg_hr=140,  # lower-ranked source, must not overwrite
    )
    persist_raw_workouts(db_session, profile.id, [gpx_raw], import_manifest_id=None)

    workouts = workout_repo.list_workouts(db_session, profile.id)
    assert len(workouts) == 1
    assert workouts[0].avg_hr == 150
