from __future__ import annotations

from datetime import date, timedelta

import pytest

from sophie.domain.aerobic_efficiency import EfficiencyRun, compute_aerobic_efficiency_trend
from sophie.domain.cardio import CardioInputs, compute_cardio_trend
from sophie.domain.circadian import NightlySleep, compute_circadian_summary
from sophie.domain.clinical_safety import (
    LabPoint,
    contains_forbidden_language,
    has_material_change,
    is_outside_reference_range,
)
from sophie.domain.hearing import DailyAudioExposure, summarize_hearing_exposure
from sophie.domain.movement import DailySteps, compute_movement_baseline
from sophie.domain.recovery import DailySignals, compute_recovery
from sophie.domain.training_load import LoadSession, compute_training_load
from sophie.domain.wellbeing import is_assessment_due, score_who5, wellbeing_trend


def _dates(n: int, start: date) -> list[date]:
    return [start + timedelta(days=i) for i in range(n)]


def test_training_load_insufficient_baseline():
    today = date(2026, 8, 15)
    sessions = [LoadSession(day=today, activity_type="easy", duration_min=40)]
    result = compute_training_load(sessions, today)
    assert result.data_quality == "insufficient"
    assert result.status == "typical"


def test_training_load_elevated_when_recent_much_higher():
    today = date(2026, 8, 15)
    sessions = []
    for i in range(1, 5):
        week_end = today - timedelta(days=7 * i)
        sessions.append(LoadSession(day=week_end, activity_type="easy", duration_min=40))
    # Recent week has much more load than baseline
    sessions.append(LoadSession(day=today, activity_type="quality", duration_min=90))
    sessions.append(
        LoadSession(day=today - timedelta(days=1), activity_type="long", duration_min=90)
    )
    result = compute_training_load(sessions, today)
    assert result.data_quality == "sufficient"
    assert result.status in ("elevated", "very_elevated")


def test_recovery_normal_with_no_deviation():
    today = date(2026, 8, 15)
    history = [
        DailySignals(day=today - timedelta(days=i), resting_hr=55, hrv_ms=60, sleep_minutes=420)
        for i in range(1, 30)
    ]
    today_signals = DailySignals(day=today, resting_hr=55, hrv_ms=60, sleep_minutes=420)
    result = compute_recovery(today_signals, history)
    assert result.status == "normal"


def test_recovery_concern_with_multiple_deviated_signals():
    today = date(2026, 8, 15)
    history = [
        DailySignals(
            day=today - timedelta(days=i),
            resting_hr=55,
            hrv_ms=60,
            sleep_minutes=420,
            respiratory_rate=14,
        )
        for i in range(1, 30)
    ]
    today_signals = DailySignals(
        day=today, resting_hr=70, hrv_ms=30, sleep_minutes=240, respiratory_rate=20
    )
    result = compute_recovery(today_signals, history)
    assert result.status == "concern"
    assert result.signals["resting_hr"]["deviated"] is True


def test_recovery_insufficient_data():
    today = date(2026, 8, 15)
    result = compute_recovery(DailySignals(day=today), [])
    assert result.data_quality == "insufficient"
    assert result.status == "normal"


def test_aerobic_efficiency_insufficient_then_improving():
    base = date(2026, 6, 1)
    few_runs = [
        EfficiencyRun(
            day=base + timedelta(days=7 * i), pace_s_per_km=330, avg_hr=140, duration_min=40
        )
        for i in range(2)
    ]
    assert compute_aerobic_efficiency_trend(few_runs).trend == "insufficient_data"

    improving_runs = [
        EfficiencyRun(
            day=base + timedelta(days=7 * i), pace_s_per_km=340 - i * 3, avg_hr=140, duration_min=40
        )
        for i in range(8)
    ]
    trend = compute_aerobic_efficiency_trend(improving_runs)
    assert trend.trend == "improving"


def test_circadian_insufficient_then_computed():
    today = date(2026, 8, 15)
    few_nights = [
        NightlySleep(
            day=today,
            bedtime_minutes_from_midnight=1350,
            waketime_minutes_from_midnight=420,
            sleep_minutes=420,
        )
    ]
    assert compute_circadian_summary(few_nights).data_quality == "insufficient"

    nights = [
        NightlySleep(
            day=today - timedelta(days=i),
            bedtime_minutes_from_midnight=1350 + (i % 3) * 5,
            waketime_minutes_from_midnight=420 + (i % 3) * 5,
            sleep_minutes=420,
            daylight_minutes=60,
        )
        for i in range(10)
    ]
    result = compute_circadian_summary(nights)
    assert result.data_quality in ("sufficient", "limited")
    assert result.avg_daylight_minutes == 60


def test_wellbeing_scoring_and_cadence():
    result = score_who5([5, 5, 5, 5, 5])
    assert result.raw_score == 25
    assert result.percentage_score == 100

    with pytest.raises(ValueError):
        score_who5([5, 5, 5, 5])

    today = date(2026, 8, 15)
    assert is_assessment_due(None, today) is True
    assert is_assessment_due(today - timedelta(days=20), today) is True
    assert is_assessment_due(today - timedelta(days=3), today) is False


def test_wellbeing_trend_flags_decline_even_if_physical_improving():
    scores = [
        (date(2026, 6, 1), 80),
        (date(2026, 6, 15), 78),
        (date(2026, 7, 1), 60),
        (date(2026, 7, 15), 55),
    ]
    assert wellbeing_trend(scores) == "declining"


def test_hearing_exposure_summary():
    today = date(2026, 8, 1)
    days = [
        DailyAudioExposure(
            day=today + timedelta(days=i), headphone_avg_db=82, environmental_avg_db=70
        )
        for i in range(20)
    ]
    result = summarize_hearing_exposure(days)
    assert result.data_quality == "sufficient"
    assert result.headphone_avg_db == 82


def test_movement_baseline_below_and_insufficient():
    today = date(2026, 8, 15)
    history = [DailySteps(day=today - timedelta(days=i), steps=8000) for i in range(1, 40)]
    recent = [DailySteps(day=today - timedelta(days=i), steps=5000) for i in range(6)]
    result = compute_movement_baseline(recent, history)
    assert result.status == "below_baseline"

    assert compute_movement_baseline([], []).status == "insufficient_data"


def test_cardio_trend_insufficient_then_watch_on_lab_flag():
    assert compute_cardio_trend(CardioInputs()).overall_trend == "insufficient_data"

    inputs = CardioInputs(
        vo2_max_series=[40, 40, 40, 40],
        resting_hr_series=[55, 55, 55, 55],
        lab_abnormal_flags=["LDL cholesterol"],
    )
    result = compute_cardio_trend(inputs)
    assert result.overall_trend in ("watch", "stable")
    assert result.evidence["lab_abnormal_flags"] == ["LDL cholesterol"]


def test_clinical_safety_never_diagnoses():
    point_in_range = LabPoint(date(2026, 1, 1), 5.0, 4.0, 6.0, None)
    point_out = LabPoint(date(2026, 1, 1), 8.0, 4.0, 6.0, None)
    assert is_outside_reference_range(point_in_range) is False
    assert is_outside_reference_range(point_out) is True

    points = [
        LabPoint(date(2026, 1, 1), 5.0, 4.0, 6.0, None),
        LabPoint(date(2026, 6, 1), 7.0, 4.0, 6.0, None),
    ]
    assert has_material_change(points) is True

    assert contains_forbidden_language("You have an autoimmune disease.") is True
    assert (
        contains_forbidden_language(
            "This measurement is outside the supplied laboratory reference interval."
        )
        is False
    )
