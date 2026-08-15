"""Tests for the deterministic calendar feasibility engine
(sophie.services.calendar_feasibility). Pure dataclasses in/out — no DB, no
network, no LLM. See docs/PRODUCT_SPEC.md §44 and
docs/ARCHITECTURE.md#calendar-feasibility-engine."""

from __future__ import annotations

from datetime import UTC, date, datetime, time

from sophie.domain.calendar_types import BusyInterval
from sophie.domain.training_block import SessionType
from sophie.services.calendar_feasibility import (
    SchedulingPreferences,
    WeatherContext,
    compute_feasible_windows,
)

WEEK_START = date(2026, 8, 17)  # a Monday


def _preferences(**overrides: object) -> SchedulingPreferences:
    defaults: dict[str, object] = {
        "dropoff_start": "08:00",
        "dropoff_end": "08:30",
        "earliest_weekday_session": "08:45",
        "latest_session": "20:00",
        "long_run_weekday_preference": ["Saturday", "Sunday", "Friday"],
        "padel_weekday": 3,  # Thursday
        "preserve_rest_day": True,
    }
    defaults.update(overrides)
    return SchedulingPreferences(**defaults)  # type: ignore[arg-type]


def _windows_for_date(windows: list, target: date) -> list:
    return [w for w in windows if w.date == target]


def test_fully_free_week_prefers_saturday_for_long_run() -> None:
    feasible, rejected = compute_feasible_windows(
        week_start=WEEK_START,
        busy_intervals=[],
        session_duration_min=90,
        buffer_min=15,
        preferences=_preferences(),
        training_load_status="typical",
        recovery_status="normal",
        weather_by_date=None,
        session_type=SessionType.LONG,
    )

    assert len(feasible) > 1
    best = max(feasible, key=lambda w: w.rank_score)
    assert best.weekday_name == "Saturday"

    saturday_best = max(_windows_for_date(feasible, date(2026, 8, 22)), key=lambda w: w.rank_score)
    sunday_best = max(_windows_for_date(feasible, date(2026, 8, 23)), key=lambda w: w.rank_score)
    tuesday_best = max(_windows_for_date(feasible, date(2026, 8, 18)), key=lambda w: w.rank_score)

    assert saturday_best.rank_score > sunday_best.rank_score
    assert saturday_best.rank_score > tuesday_best.rank_score


def test_fully_busy_day_only_produces_busy_calendar_rejections() -> None:
    busy_date = date(2026, 8, 18)  # Tuesday
    all_day_block = BusyInterval(
        start=datetime(2026, 8, 18, 0, 0, tzinfo=UTC),
        end=datetime(2026, 8, 19, 0, 0, tzinfo=UTC),
        all_day=True,
    )

    feasible, rejected = compute_feasible_windows(
        week_start=WEEK_START,
        busy_intervals=[all_day_block],
        session_duration_min=45,
        buffer_min=10,
        preferences=_preferences(),
        training_load_status="typical",
        recovery_status="normal",
        weather_by_date=None,
        session_type=SessionType.EASY,
    )

    assert _windows_for_date(feasible, busy_date) == []
    busy_day_rejections = _windows_for_date(rejected, busy_date)
    assert busy_day_rejections  # at least one candidate rejected that day
    # every candidate within allowed hours on that day is rejected as busy,
    # never for some other spurious reason, since the whole day is blocked
    within_hours = [w for w in busy_day_rejections if time(8, 45) <= w.start <= time(19, 0)]
    assert within_hours
    assert all(w.reason_code == "busy_calendar" for w in within_hours)


def test_latest_session_boundary_handled_correctly() -> None:
    target_date = date(2026, 8, 18)  # Tuesday, fully free

    feasible, rejected = compute_feasible_windows(
        week_start=WEEK_START,
        busy_intervals=[],
        session_duration_min=60,
        buffer_min=15,
        preferences=_preferences(latest_session="20:00"),
        training_load_status="typical",
        recovery_status="normal",
        weather_by_date=None,
        session_type=SessionType.EASY,
    )

    day_feasible = _windows_for_date(feasible, target_date)
    day_rejected = _windows_for_date(rejected, target_date)

    # 19:00 start -> ends exactly at 20:00 -> allowed (end == latest_session, not after it)
    assert any(w.start == time(19, 0) and w.end == time(20, 0) for w in day_feasible)

    # 19:30 start -> ends at 20:30 -> after latest_session -> rejected
    boundary_rejection = next(w for w in day_rejected if w.start == time(19, 30))
    assert boundary_rejection.reason_code == "after_latest_session_time"


def test_missing_weather_is_neutral_never_a_rejection_reason() -> None:
    target_date = date(2026, 8, 22)  # Saturday, fully free

    feasible_no_dict, rejected_no_dict = compute_feasible_windows(
        week_start=WEEK_START,
        busy_intervals=[],
        session_duration_min=60,
        buffer_min=10,
        preferences=_preferences(),
        training_load_status="typical",
        recovery_status="normal",
        weather_by_date=None,
        session_type=SessionType.LONG,
    )
    feasible_empty_context, _ = compute_feasible_windows(
        week_start=WEEK_START,
        busy_intervals=[],
        session_duration_min=60,
        buffer_min=10,
        preferences=_preferences(),
        training_load_status="typical",
        recovery_status="normal",
        weather_by_date={target_date: WeatherContext()},
        session_type=SessionType.LONG,
    )

    assert not any(w.reason_code == "weather" for w in rejected_no_dict)
    assert _windows_for_date(feasible_no_dict, target_date)
    assert _windows_for_date(feasible_empty_context, target_date)

    # No weather info at all vs. an all-None WeatherContext must score identically
    # (both neutral) for the same candidate slot.
    no_dict_scores = {
        w.start: w.rank_score for w in _windows_for_date(feasible_no_dict, target_date)
    }
    empty_context_scores = {
        w.start: w.rank_score for w in _windows_for_date(feasible_empty_context, target_date)
    }
    assert no_dict_scores == empty_context_scores


def test_day_after_padel_gets_soft_penalty_not_rejection() -> None:
    # padel_weekday=3 (Thursday) -> Friday is the day-after-padel.
    feasible, rejected = compute_feasible_windows(
        week_start=WEEK_START,
        busy_intervals=[],
        session_duration_min=45,
        buffer_min=10,
        preferences=_preferences(padel_weekday=3),
        training_load_status="typical",
        recovery_status="normal",
        weather_by_date=None,
        session_type=SessionType.QUALITY,
    )

    friday = date(2026, 8, 21)
    tuesday = date(2026, 8, 18)

    friday_at_nine = next(w for w in feasible if w.date == friday and w.start == time(9, 0))
    tuesday_at_nine = next(w for w in feasible if w.date == tuesday and w.start == time(9, 0))

    # Same session type, same weekday-vs-weekend bucket, same time-of-day slot:
    # the only difference should be the padel-spacing soft penalty.
    assert friday_at_nine.rank_score < tuesday_at_nine.rank_score
    # soft penalty, never a rejection: the same 09:00 slot that is feasible on
    # Tuesday must also be feasible (not rejected) on the day after padel.
    assert not any(w.date == friday and w.start == time(9, 0) for w in rejected)
    assert any("padel" in note.lower() for note in friday_at_nine.notes)
