from __future__ import annotations

import zipfile
from pathlib import Path

from sophie.repositories import profile_repo, summary_repo, workout_repo
from sophie.services.apple_health_import import import_apple_health_zip

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
<Record type="HKQuantityTypeIdentifierBodyMass" sourceName="Health" unit="kg"
 startDate="2026-08-01 08:00:00 +0000" endDate="2026-08-01 08:00:00 +0000" value="90.2"/>
<Record type="HKQuantityTypeIdentifierStepCount" sourceName="Watch" unit="count"
 startDate="2026-08-01 09:00:00 +0000" endDate="2026-08-01 09:05:00 +0000" value="500"/>
<Workout workoutActivityType="HKWorkoutActivityTypeRunning" sourceName="Watch"
 duration="42" durationUnit="min" totalDistance="10" totalDistanceUnit="km"
 startDate="2026-08-01 08:00:00 +0000" endDate="2026-08-01 08:42:00 +0000">
</Workout>
</HealthData>
"""


def _make_zip(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("apple_health_export/export.xml", SAMPLE_XML)
    return path


def test_full_import_persists_workout_and_daily_summary(db_session, tmp_path):
    profile = profile_repo.get_or_create_profile(db_session)
    zip_path = _make_zip(tmp_path / "export.zip")

    result = import_apple_health_zip(db_session, profile.id, zip_path)

    assert result.state == "success"
    assert result.workouts_created == 1

    workouts = workout_repo.list_workouts(db_session, profile.id)
    assert len(workouts) == 1
    assert workouts[0].distance_m == 10000

    from datetime import date

    summaries = summary_repo.list_daily_summaries(
        db_session, profile.id, date(2026, 8, 1), date(2026, 8, 1)
    )
    assert summaries and summaries[0].weight_kg == 90.2
    assert summaries[0].steps == 500


def test_reimport_same_file_is_idempotent(db_session, tmp_path):
    profile = profile_repo.get_or_create_profile(db_session)
    zip_path = _make_zip(tmp_path / "export.zip")

    first = import_apple_health_zip(db_session, profile.id, zip_path)
    second = import_apple_health_zip(db_session, profile.id, zip_path)

    assert first.state == "success"
    assert second.state == "skipped_duplicate"
    workouts = workout_repo.list_workouts(db_session, profile.id)
    assert len(workouts) == 1


def test_bad_zip_marks_manifest_failed_not_successful(db_session, tmp_path):
    profile = profile_repo.get_or_create_profile(db_session)
    bad_zip = tmp_path / "bad.zip"
    bad_zip.write_bytes(b"not a zip")

    result = import_apple_health_zip(db_session, profile.id, bad_zip)
    assert result.state == "failed"
    assert result.error_summary is not None
