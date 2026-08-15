from __future__ import annotations

from datetime import date

from sophie.config.settings import Settings
from sophie.repositories import profile_repo
from sophie.services.calendar_context import (
    build_calendar_windows,
    fetch_busy_intervals_for_week,
    save_ics_upload,
)

ICS_TEXT = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:1@example.com
SUMMARY:Busy block
DTSTART:20260817T090000Z
DTEND:20260817T170000Z
END:VEVENT
END:VCALENDAR
"""


def test_no_calendar_configured_returns_empty(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    settings = Settings(ms_graph_client_id=None)
    result = fetch_busy_intervals_for_week(db_session, profile.id, date(2026, 8, 17), settings)
    assert result.busy_intervals == []
    assert result.source == "none"


def test_ics_upload_then_fetch_returns_saved_snapshot(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    week_start = date(2026, 8, 17)
    upload_result = save_ics_upload(db_session, profile.id, week_start, ICS_TEXT)
    assert len(upload_result.busy_intervals) == 1

    settings = Settings(ms_graph_client_id=None)
    fetched = fetch_busy_intervals_for_week(db_session, profile.id, week_start, settings)
    assert fetched.source == "ics_fallback"
    assert len(fetched.busy_intervals) == 1


def test_build_calendar_windows_produces_feasible_windows(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    config = profile_repo.get_config(db_session, profile.id)
    week_start = date(2026, 8, 17)

    windows, rejected = build_calendar_windows(
        db_session, profile.id, week_start, config, "typical", "normal", busy_intervals=[]
    )
    assert len(windows) > 0
    assert any(w.weekday_name == "Saturday" for w in windows)
