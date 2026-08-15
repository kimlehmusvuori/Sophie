from __future__ import annotations

import zipfile

from sophie.repositories import profile_repo, workout_repo
from sophie.services.sports_tracker_import import import_sports_tracker_zip_file

VALID_GPX = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
<trk><name>Morning Run</name><trkseg>
<trkpt lat="60.170" lon="24.940"><ele>10</ele><time>2026-08-01T08:00:00Z</time></trkpt>
<trkpt lat="60.171" lon="24.942"><ele>11</ele><time>2026-08-01T08:05:00Z</time></trkpt>
<trkpt lat="60.173" lon="24.944"><ele>12</ele><time>2026-08-01T08:10:00Z</time></trkpt>
</trkseg></trk>
</gpx>
"""


def _make_zip(path) -> object:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("run1.gpx", VALID_GPX)
    return path


def test_sports_tracker_import_persists_workout(db_session, tmp_path):
    profile = profile_repo.get_or_create_profile(db_session)
    zip_path = _make_zip(tmp_path / "sports_tracker.zip")

    result = import_sports_tracker_zip_file(db_session, profile.id, zip_path)

    assert result.state == "success"
    assert result.workouts_created == 1
    workouts = workout_repo.list_workouts(db_session, profile.id)
    assert len(workouts) == 1


def test_sports_tracker_reimport_is_idempotent(db_session, tmp_path):
    profile = profile_repo.get_or_create_profile(db_session)
    zip_path = _make_zip(tmp_path / "sports_tracker.zip")

    first = import_sports_tracker_zip_file(db_session, profile.id, zip_path)
    second = import_sports_tracker_zip_file(db_session, profile.id, zip_path)

    assert first.state == "success"
    assert second.state == "skipped_duplicate"
    assert len(workout_repo.list_workouts(db_session, profile.id)) == 1
