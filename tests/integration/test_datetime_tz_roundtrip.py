"""Regression tests for a real bug found during real-data import: SQLite has
no native timezone-aware storage, so SQLAlchemy's `DateTime(timezone=True)`
columns silently round-trip to *naive* Python datetimes once reloaded in a
fresh session — even though an aware value was written. Code that compares
a freshly-constructed aware datetime against one loaded back from such a
column must go through `sophie.config.timezone.assume_utc()` first.

Unlike most of this suite's tests (which share one long-lived session via
the `db_session` fixture and never actually reload a row from disk), these
tests use a real file-backed database across independent `session_scope()`
blocks — the same lifecycle the actual app has (a fresh session per page
render / per import call) — so they actually exercise the round-trip.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sophie.db import base as db_base
from sophie.db.models import Base
from sophie.domain.import_types import RawWorkout
from sophie.repositories import import_repo, profile_repo, workout_repo
from sophie.services import data_status
from sophie.services.workout_canonicalization import persist_raw_workouts


def _fresh_file_db(tmp_path):
    db_path = tmp_path / "roundtrip.db"
    db_base.configure(f"sqlite:///{db_path}")
    Base.metadata.create_all(db_base.get_engine())


def test_find_matching_workout_survives_naive_reload_from_db(tmp_path):
    _fresh_file_db(tmp_path)

    with db_base.session_scope() as session:
        profile = profile_repo.get_or_create_profile(session)
        profile_id = profile.id
        workout_repo.create_canonical_workout(
            session,
            profile_id=profile_id,
            activity_type="run",
            start_at=datetime(2026, 8, 1, 8, 0, tzinfo=UTC),
            distance_m=10000,
        )
    # New session: the row above is now reloaded from disk, naive.
    with db_base.session_scope() as session:
        match = workout_repo.find_matching_workout(
            session, profile_id, "run", datetime(2026, 8, 1, 8, 5, tzinfo=UTC), 10050
        )
        assert match is not None


def test_persist_raw_workouts_across_sessions_does_not_crash(tmp_path):
    _fresh_file_db(tmp_path)

    with db_base.session_scope() as session:
        profile = profile_repo.get_or_create_profile(session)
        profile_id = profile.id
        persist_raw_workouts(
            session,
            profile_id,
            [
                RawWorkout(
                    source_type="apple_health",
                    source_identifier="watch",
                    activity_type="run",
                    start_at=datetime(2026, 8, 1, 8, 0, tzinfo=UTC),
                    end_at=None,
                    duration_s=2400,
                    distance_m=10000,
                )
            ],
            import_manifest_id=None,
        )

    # Second, independent session/import batch — this is what crashed on
    # real Sports Tracker data (many workouts imported across a batch that
    # triggers intermediate flushes/reloads).
    with db_base.session_scope() as session:
        result = persist_raw_workouts(
            session,
            profile_id,
            [
                RawWorkout(
                    source_type="sports_tracker_fit",
                    source_identifier="fit-1",
                    activity_type="run",
                    start_at=datetime(2026, 8, 1, 8, 1, tzinfo=UTC),
                    end_at=None,
                    duration_s=2400,
                    distance_m=10020,
                )
            ],
            import_manifest_id=None,
        )
        assert result.matched == 1


def test_data_status_age_calculation_survives_naive_reload(tmp_path):
    _fresh_file_db(tmp_path)

    with db_base.session_scope() as session:
        profile = profile_repo.get_or_create_profile(session)
        profile_id = profile.id
        manifest = import_repo.start_manifest(session, profile_id, "apple_health", "fp-1")
        import_repo.finish_manifest(session, manifest, state="success", records_processed=10)

    with db_base.session_scope() as session:
        from sophie.config.settings import Settings

        statuses = data_status.get_data_status(
            session,
            profile_id,
            Settings(
                ms_graph_client_id=None, weather_lat=None, weather_lon=None, openai_api_key=None
            ),
        )
        by_name = {s.name: s for s in statuses}
        assert by_name["Apple Health"].status == "ok"
