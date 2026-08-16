from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sophie.domain.import_types import RawWorkout
from sophie.repositories import profile_repo, summary_repo
from sophie.services import dashboard_service
from sophie.services.workout_canonicalization import persist_raw_workouts

TODAY = date(2026, 8, 16)


def test_training_distance_zero_fills_rest_days(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    persist_raw_workouts(
        db_session,
        profile.id,
        [
            RawWorkout(
                source_type="apple_health",
                source_identifier="w1",
                activity_type="run",
                start_at=datetime(2026, 8, 15, 8, 0, tzinfo=UTC),
                end_at=None,
                duration_s=1800,
                distance_m=10000,
            )
        ],
        import_manifest_id=None,
    )

    series = dashboard_service.get_metric_series(db_session, profile.id, "training", "Week", TODAY)

    assert series.window_days == 7
    assert len(series.points) == 7
    # 6 rest days (value 0.0, not None) + 1 day with 10km
    assert sum(1 for p in series.points if p.value == 0.0) == 6
    assert any(p.value == 10.0 for p in series.points)
    # average is over ALL 7 days including zeros — genuinely "km/day"
    assert series.average == round(10.0 / 7, 2)
    assert series.days_with_data == 7  # every day counts for training (0 is a real value)


def test_sleep_average_excludes_missing_days_not_zero_fill(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    summary_repo.upsert_daily_summary(db_session, profile.id, TODAY, sleep_minutes=480)
    summary_repo.upsert_daily_summary(
        db_session, profile.id, TODAY - timedelta(days=1), sleep_minutes=360
    )
    # remaining 5 days in the week window have no data at all

    series = dashboard_service.get_metric_series(db_session, profile.id, "sleep", "Week", TODAY)

    assert series.days_with_data == 2
    assert series.average == round((8.0 + 6.0) / 2, 2)  # hours, not diluted by missing days


def test_year_view_buckets_weekly(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    for offset in range(0, 365, 10):
        summary_repo.upsert_daily_summary(
            db_session, profile.id, TODAY - timedelta(days=offset), weight_kg=80.0
        )

    series = dashboard_service.get_metric_series(db_session, profile.id, "weight", "Year", TODAY)

    assert series.window_days == 365
    # bucketed to ~weeks, so far fewer points than 365 raw days
    assert len(series.points) < 60
    assert series.average == 80.0


def test_week_and_month_views_stay_daily(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    series_week = dashboard_service.get_metric_series(
        db_session, profile.id, "weight", "Week", TODAY
    )
    series_month = dashboard_service.get_metric_series(
        db_session, profile.id, "weight", "Month", TODAY
    )

    assert len(series_week.points) == 7
    assert len(series_month.points) == 30


def test_get_all_metric_series_covers_five_areas(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    series_list = dashboard_service.get_all_metric_series(db_session, profile.id, "Week", TODAY)

    assert {s.key for s in series_list} == {"training", "sleep", "weight", "resting_hr", "hrv"}
