from __future__ import annotations

from datetime import UTC, datetime, timedelta
from datetime import date as date_cls

from sophie.repositories import clinical_repo, health_intel_repo, profile_repo, workout_repo
from sophie.repositories.summary_repo import upsert_daily_summary
from sophie.services import health_intelligence as svc


def _dt(day: date_cls, hour: int = 7) -> datetime:
    return datetime(day.year, day.month, day.day, hour, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Training load
# ---------------------------------------------------------------------------


def test_refresh_training_load_insufficient_with_sparse_history(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    as_of = date_cls(2026, 8, 15)

    workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="easy",
        start_at=_dt(as_of),
        duration_s=2400,
        avg_hr=130,
    )

    row = svc.refresh_training_load(db_session, profile.id, as_of)

    assert row.data_quality == "insufficient"
    assert row.status == "typical"
    assert row.week_start == as_of - timedelta(days=as_of.weekday())

    persisted = health_intel_repo.latest_training_load(db_session, profile.id)
    assert persisted is not None
    assert persisted.id == row.id


def test_refresh_training_load_numeric_ratio_with_multiweek_history(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    as_of = date_cls(2026, 8, 15)

    # Four prior weeks of modest, consistent load.
    for week in range(1, 5):
        week_end = as_of - timedelta(days=7 * week)
        workout_repo.create_canonical_workout(
            db_session,
            profile_id=profile.id,
            activity_type="easy",
            start_at=_dt(week_end),
            duration_s=2400,  # 40 min
            avg_hr=125,
        )

    # This week: much higher load (quality + long sessions).
    workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="quality",
        start_at=_dt(as_of),
        duration_s=5400,  # 90 min
        avg_hr=160,
    )
    workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="long",
        start_at=_dt(as_of - timedelta(days=1)),
        duration_s=5400,
        avg_hr=150,
    )

    row = svc.refresh_training_load(db_session, profile.id, as_of)

    assert row.data_quality == "sufficient"
    assert row.load_ratio is not None
    assert row.status in ("elevated", "very_elevated")
    assert row.evidence["baseline_weeks_used"] == 4


# ---------------------------------------------------------------------------
# Recovery
# ---------------------------------------------------------------------------


def test_refresh_recovery_insufficient_with_no_data(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    as_of = date_cls(2026, 8, 15)

    row = svc.refresh_recovery(db_session, profile.id, as_of)

    assert row.data_quality == "insufficient"
    assert row.status == "normal"
    assert row.day == as_of


def test_refresh_recovery_normal_with_stable_history(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    as_of = date_cls(2026, 8, 15)

    for i in range(1, 30):
        day = as_of - timedelta(days=i)
        upsert_daily_summary(
            db_session,
            profile.id,
            day,
            resting_hr=55,
            hrv_ms=60,
            sleep_minutes=420,
            respiratory_rate=14,
        )
    upsert_daily_summary(
        db_session,
        profile.id,
        as_of,
        resting_hr=55,
        hrv_ms=60,
        sleep_minutes=420,
        respiratory_rate=14,
    )

    row = svc.refresh_recovery(db_session, profile.id, as_of)

    assert row.status == "normal"
    assert row.data_quality == "sufficient"
    assert row.signals["resting_hr"]["deviated"] is False


def test_refresh_recovery_concern_with_deviated_signals(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    as_of = date_cls(2026, 8, 15)

    for i in range(1, 30):
        day = as_of - timedelta(days=i)
        upsert_daily_summary(
            db_session,
            profile.id,
            day,
            resting_hr=55,
            hrv_ms=60,
            sleep_minutes=420,
            respiratory_rate=14,
        )
    upsert_daily_summary(
        db_session,
        profile.id,
        as_of,
        resting_hr=70,
        hrv_ms=30,
        sleep_minutes=240,
        respiratory_rate=20,
    )

    row = svc.refresh_recovery(db_session, profile.id, as_of)

    assert row.status == "concern"


# ---------------------------------------------------------------------------
# Circadian
# ---------------------------------------------------------------------------


def test_refresh_circadian_from_two_weeks_of_bed_wake_times(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    as_of = date_cls(2026, 8, 15)

    for i in range(14):
        day = as_of - timedelta(days=i)
        upsert_daily_summary(
            db_session,
            profile.id,
            day,
            bedtime_local="23:30",
            waketime_local="07:00",
            sleep_minutes=440,
            daylight_minutes=45,
        )

    row = svc.refresh_circadian(db_session, profile.id, as_of)

    assert row.data_quality in ("sufficient", "limited")
    assert row.week_start == as_of - timedelta(days=as_of.weekday())
    assert row.avg_daylight_minutes == 45
    # 23:30 parsed literally as minutes-from-midnight = 23*60+30 = 1410.
    assert row.disrupted_nights == 0
    assert row.sleep_midpoint_local is not None


def test_refresh_circadian_insufficient_with_single_night(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    as_of = date_cls(2026, 8, 15)

    upsert_daily_summary(
        db_session,
        profile.id,
        as_of,
        bedtime_local="22:30",
        waketime_local="06:30",
        sleep_minutes=480,
    )

    row = svc.refresh_circadian(db_session, profile.id, as_of)
    assert row.data_quality == "insufficient"


# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------


def test_refresh_movement_below_baseline(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    as_of = date_cls(2026, 8, 15)

    for i in range(1, 40):
        upsert_daily_summary(db_session, profile.id, as_of - timedelta(days=i), steps=8000)
    for i in range(6):
        upsert_daily_summary(db_session, profile.id, as_of - timedelta(days=i), steps=5000)

    row = svc.refresh_movement(db_session, profile.id, as_of)

    assert row.status == "below_baseline"
    assert row.data_quality in ("sufficient", "limited")


def test_refresh_movement_insufficient_with_no_history(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    as_of = date_cls(2026, 8, 15)

    row = svc.refresh_movement(db_session, profile.id, as_of)
    assert row.status == "insufficient_data"
    assert row.data_quality == "insufficient"


# ---------------------------------------------------------------------------
# Hearing
# ---------------------------------------------------------------------------


def test_refresh_hearing_summary(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    period_end = date_cls(2026, 8, 15)
    period_start = period_end - timedelta(days=19)

    for i in range(20):
        upsert_daily_summary(
            db_session,
            profile.id,
            period_start + timedelta(days=i),
            headphone_audio_db=82,
            environmental_audio_db=70,
        )

    row = svc.refresh_hearing(db_session, profile.id, period_start, period_end)

    assert row.data_quality == "sufficient"
    assert row.headphone_avg_db == 82
    assert row.period_start == period_start
    assert row.period_end == period_end


# ---------------------------------------------------------------------------
# Aerobic efficiency
# ---------------------------------------------------------------------------


def test_compute_aerobic_efficiency_persists_points_idempotently(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    base = date_cls(2026, 6, 1)

    for i in range(8):
        workout_repo.create_canonical_workout(
            db_session,
            profile_id=profile.id,
            activity_type="run",
            start_at=_dt(base + timedelta(days=7 * i)),
            duration_s=2400,  # 40 min, >= domain's 20 min minimum
            avg_pace_s_per_km=340 - i * 3,
            avg_hr=140,
        )
    # A non-run workout and a run missing avg_hr must both be excluded.
    workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="padel",
        start_at=_dt(base),
        duration_s=3600,
        avg_hr=150,
    )
    workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="run",
        start_at=_dt(base + timedelta(days=100)),
        duration_s=1800,
        avg_pace_s_per_km=320,
        avg_hr=None,
    )

    trend = svc.compute_aerobic_efficiency(db_session, profile.id)

    assert trend.trend == "improving"
    persisted = health_intel_repo.list_aerobic_efficiency_points(db_session, profile.id)
    assert len(persisted) == len(trend.points) == 8

    # Re-running must not create duplicate points for the same workouts.
    trend_again = svc.compute_aerobic_efficiency(db_session, profile.id)
    persisted_again = health_intel_repo.list_aerobic_efficiency_points(db_session, profile.id)
    assert len(persisted_again) == len(persisted)
    assert trend_again.trend == trend.trend


# ---------------------------------------------------------------------------
# Cardio trend
# ---------------------------------------------------------------------------


def test_compute_cardio_trend_picks_up_lab_abnormal_flag(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    as_of = date_cls(2026, 8, 15)

    for i, vo2 in enumerate([40.0, 40.0, 40.0, 40.0]):
        upsert_daily_summary(
            db_session,
            profile.id,
            as_of - timedelta(days=(4 - i) * 7),
            vo2_max=vo2,
            resting_hr=55,
        )

    clinical_import = clinical_repo.create_clinical_import(
        db_session,
        profile_id=profile.id,
        provider="Test Lab",
        source_kind="csv",
        imported_at=datetime.now(UTC),
        user_confirmed=True,
    )
    clinical_repo.add_lab_result(
        db_session,
        profile_id=profile.id,
        clinical_import_id=clinical_import.id,
        sample_date=as_of,
        test_name="LDL cholesterol",
        canonical_test_id="ldl",
        value=4.5,
        unit="mmol/L",
        reference_low=1.0,
        reference_high=3.0,
        abnormal_flag="H",
        category="lipids",
    )
    # A lab result with no lab-supplied abnormal flag must never be inferred as one.
    clinical_repo.add_lab_result(
        db_session,
        profile_id=profile.id,
        clinical_import_id=clinical_import.id,
        sample_date=as_of,
        test_name="HbA1c",
        canonical_test_id="hba1c",
        value=5.2,
        unit="%",
        reference_low=4.0,
        reference_high=6.0,
        abnormal_flag=None,
        category="glucose",
    )

    result = svc.compute_cardio_trend(db_session, profile.id)

    assert result.evidence["lab_abnormal_flags"] == ["LDL cholesterol"]
    assert result.overall_trend in ("watch", "stable")


def test_compute_cardio_trend_insufficient_with_no_data(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    result = svc.compute_cardio_trend(db_session, profile.id)
    assert result.overall_trend == "insufficient_data"
    assert result.evidence["lab_abnormal_flags"] == []


# ---------------------------------------------------------------------------
# Wellbeing status
# ---------------------------------------------------------------------------


def test_wellbeing_status_due_with_no_assessments(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    status = svc.wellbeing_status(db_session, profile.id, date_cls(2026, 8, 15))

    assert status == {"due": True, "trend": "insufficient_data", "latest_percentage": None}


def test_wellbeing_status_not_due_after_recent_assessment(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    today = date_cls(2026, 8, 15)

    health_intel_repo.add_wellbeing_assessment(
        db_session,
        profile_id=profile.id,
        assessed_at=datetime.combine(today - timedelta(days=20), datetime.min.time(), tzinfo=UTC),
        raw_score=20,
        percentage_score=80,
        answers=[4, 4, 4, 4, 4],
    )
    health_intel_repo.add_wellbeing_assessment(
        db_session,
        profile_id=profile.id,
        assessed_at=datetime.combine(today - timedelta(days=3), datetime.min.time(), tzinfo=UTC),
        raw_score=14,
        percentage_score=56,
        answers=[3, 3, 3, 3, 2],
    )

    status = svc.wellbeing_status(db_session, profile.id, today)

    assert status["due"] is False
    assert status["latest_percentage"] == 56
    assert status["trend"] in ("declining", "stable", "improving")


# ---------------------------------------------------------------------------
# refresh_all_health_intelligence
# ---------------------------------------------------------------------------


def test_refresh_all_health_intelligence_bundles_every_domain_without_crashing(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    as_of = date_cls(2026, 8, 15)

    upsert_daily_summary(
        db_session,
        profile.id,
        as_of,
        resting_hr=55,
        hrv_ms=60,
        sleep_minutes=420,
        bedtime_local="23:00",
        waketime_local="07:00",
        steps=7000,
    )
    workout_repo.create_canonical_workout(
        db_session,
        profile_id=profile.id,
        activity_type="easy",
        start_at=_dt(as_of),
        duration_s=2400,
        avg_hr=130,
    )

    snapshot = svc.refresh_all_health_intelligence(db_session, profile.id, as_of)

    assert snapshot.training_load is not None
    assert snapshot.recovery is not None
    assert snapshot.circadian is not None
    assert snapshot.movement is not None
    assert snapshot.hearing is not None
    assert snapshot.aerobic_efficiency_trend is not None
    assert snapshot.cardio_trend is not None
    assert "due" in snapshot.wellbeing
