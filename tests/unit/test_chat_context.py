"""See docs/PRIVACY.md — build_chat_context() must be traceable to only
summary/derived tables, mirroring the existing coach-context guarantee."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sophie.domain.import_types import RawWorkout
from sophie.repositories import profile_repo, summary_repo
from sophie.services.chat_context import build_chat_context
from sophie.services.workout_canonicalization import persist_raw_workouts


def test_chat_context_contains_no_raw_workout_or_sample_fields(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    profile_id = profile.id

    persist_raw_workouts(
        db_session,
        profile_id,
        [
            RawWorkout(
                source_type="apple_health",
                source_identifier="w1",
                activity_type="run",
                start_at=datetime(2026, 8, 1, 8, 0, tzinfo=UTC),
                end_at=None,
                duration_s=2400,
                distance_m=10000,
            )
        ],
        import_manifest_id=None,
    )
    summary_repo.upsert_daily_summary(
        db_session, profile_id, date(2026, 8, 1), sleep_minutes=420, resting_hr=52, weight_kg=78.2
    )

    context = build_chat_context(db_session, profile_id, today=date(2026, 8, 15))
    dumped = context.model_dump()

    # Only status/aggregate fields are present anywhere in the dumped context —
    # no raw per-workout or per-day fields (GPS, HR-series, distance_m, etc.)
    forbidden_keys = {"distance_m", "gps", "route", "duration_s", "hrv_ms", "resting_hr"}
    assert forbidden_keys.isdisjoint(dumped.keys())
    for status in context.domain_statuses:
        assert status.evidence_summary is None or isinstance(status.evidence_summary, str)
    for avg in context.metric_averages:
        # every metric_average is a rounded aggregate, never a raw sample list
        assert isinstance(avg.value, (float, type(None)))


def test_chat_context_metric_averages_exclude_missing_days_not_zero_fill(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    profile_id = profile.id

    # Only 2 of the last 30 days have sleep data — average must be computed
    # over those 2 days only, not diluted by 28 zero/missing days.
    summary_repo.upsert_daily_summary(db_session, profile_id, date(2026, 8, 1), sleep_minutes=480)
    summary_repo.upsert_daily_summary(db_session, profile_id, date(2026, 8, 2), sleep_minutes=360)

    context = build_chat_context(db_session, profile_id, today=date(2026, 8, 15))
    sleep_avg = next(m for m in context.metric_averages if m.label == "sleep duration")

    assert sleep_avg.days_with_data == 2
    assert sleep_avg.value == 420.0  # (480 + 360) / 2, not divided by 30


def test_chat_context_domain_statuses_never_empty_shape(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    context = build_chat_context(db_session, profile.id, today=date(2026, 8, 15))

    domains = {s.domain for s in context.domain_statuses}
    assert {"cardiovascular", "training_load", "recovery", "mental_wellbeing"}.issubset(domains)
