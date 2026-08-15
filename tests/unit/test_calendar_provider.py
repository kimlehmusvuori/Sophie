"""Tests for sophie.providers.calendar. All calendar payloads here are
synthetic. Covers:

- The Graph client extracts only start/end/all-day from Graph events and
  never leaks subject/body/attendees into its return value, even when a
  mocked Graph response includes them (docs/PRIVACY.md).
- With no `ms_graph_client_id` configured, the provider reports a clear
  "not connected" status without attempting any network call or raising.
- The ICS/mock fallback parses a small synthetic `.ics`-shaped string into
  correct busy intervals, also without leaking SUMMARY text.
"""

from __future__ import annotations

import json
import textwrap
from dataclasses import fields
from datetime import UTC, datetime

import httpx

from sophie.domain.calendar_types import BusyInterval
from sophie.providers.calendar.graph_client import (
    SOPHIE_OWNED_PROPERTY_ID,
    GraphCalendarClient,
)
from sophie.providers.calendar.mock_provider import (
    MockCalendarProvider,
    parse_ics_busy_intervals,
)

# ---------------------------------------------------------------------------
# GraphCalendarClient — not configured
# ---------------------------------------------------------------------------


def test_no_client_id_reports_not_connected_without_network_or_raise(tmp_path) -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no network call should be attempted when not configured")

    http_client = httpx.Client(transport=httpx.MockTransport(_handler))
    client = GraphCalendarClient(
        client_id=None,
        tenant_id="common",
        redirect_uri="http://localhost:8765/callback",
        token_cache_path=tmp_path / "token_cache.bin",
        http_client=http_client,
    )

    assert client.is_configured is False
    assert client.connection_status() == "not_configured"

    intervals = client.get_busy_intervals(
        datetime(2026, 8, 17, tzinfo=UTC), datetime(2026, 8, 24, tzinfo=UTC)
    )
    assert intervals == []


def test_configured_but_never_signed_in_reports_not_signed_in(tmp_path) -> None:
    client = GraphCalendarClient(
        client_id="fake-client-id",
        tenant_id="common",
        redirect_uri="http://localhost:8765/callback",
        token_cache_path=tmp_path / "token_cache.bin",
    )

    assert client.is_configured is True
    assert client.connection_status() == "not_signed_in"


# ---------------------------------------------------------------------------
# GraphCalendarClient — reads never leak subject/body/attendees
# ---------------------------------------------------------------------------


def test_get_busy_intervals_extracts_only_start_end_allday(tmp_path, monkeypatch) -> None:
    events_payload = {
        "value": [
            {
                "subject": "Secret doctor appointment",
                "body": {"content": "very private clinical details", "contentType": "text"},
                "attendees": [{"emailAddress": {"address": "someone@example.com"}}],
                "start": {"dateTime": "2026-08-17T09:00:00", "timeZone": "UTC"},
                "end": {"dateTime": "2026-08-17T10:00:00", "timeZone": "UTC"},
                "isAllDay": False,
            },
            {
                "subject": "Family vacation",
                "start": {"dateTime": "2026-08-18T00:00:00", "timeZone": "UTC"},
                "end": {"dateTime": "2026-08-19T00:00:00", "timeZone": "UTC"},
                "isAllDay": True,
            },
        ]
    }

    def _handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/me/calendarview")
        return httpx.Response(200, json=events_payload)

    http_client = httpx.Client(transport=httpx.MockTransport(_handler))
    client = GraphCalendarClient(
        client_id="fake-client-id",
        tenant_id="common",
        redirect_uri="http://localhost:8765/callback",
        token_cache_path=tmp_path / "token_cache.bin",
        http_client=http_client,
    )
    monkeypatch.setattr(client, "_acquire_token_silent", lambda: "fake-access-token")

    intervals = client.get_busy_intervals(
        datetime(2026, 8, 17, tzinfo=UTC), datetime(2026, 8, 20, tzinfo=UTC)
    )

    assert len(intervals) == 2
    assert all(isinstance(i, BusyInterval) for i in intervals)
    # BusyInterval only ever has these three fields — structurally impossible
    # for subject/body/attendees to hitch a ride.
    assert {f.name for i in intervals for f in fields(i)} == {"start", "end", "all_day"}

    dump = " ".join(repr(i) for i in intervals)
    assert "Secret doctor appointment" not in dump
    assert "very private clinical details" not in dump
    assert "someone@example.com" not in dump
    assert "Family vacation" not in dump

    assert intervals[0].all_day is False
    assert intervals[0].start == datetime(2026, 8, 17, 9, 0, tzinfo=UTC)
    assert intervals[0].end == datetime(2026, 8, 17, 10, 0, tzinfo=UTC)
    assert intervals[1].all_day is True


def test_create_sophie_event_tags_extended_property(tmp_path, monkeypatch) -> None:
    captured_body: dict = {}

    def _handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_body
        assert request.url.path.endswith("/me/events")
        captured_body = json.loads(request.content)
        return httpx.Response(200, json={"id": "sophie-event-123"})

    http_client = httpx.Client(transport=httpx.MockTransport(_handler))
    client = GraphCalendarClient(
        client_id="fake-client-id",
        tenant_id="common",
        redirect_uri="http://localhost:8765/callback",
        token_cache_path=tmp_path / "token_cache.bin",
        http_client=http_client,
    )
    monkeypatch.setattr(client, "_acquire_token_silent", lambda: "fake-access-token")

    event_id = client.create_sophie_event(
        subject="Easy run 8km",
        start=datetime(2026, 8, 22, 9, 0, tzinfo=UTC),
        end=datetime(2026, 8, 22, 10, 0, tzinfo=UTC),
    )

    assert event_id == "sophie-event-123"
    extended_props = captured_body["singleValueExtendedProperties"]
    assert extended_props == [{"id": SOPHIE_OWNED_PROPERTY_ID, "value": "true"}]


def test_get_busy_intervals_without_signed_in_account_is_empty_not_raising(tmp_path) -> None:
    client = GraphCalendarClient(
        client_id="fake-client-id",
        tenant_id="common",
        redirect_uri="http://localhost:8765/callback",
        token_cache_path=tmp_path / "token_cache.bin",
    )

    intervals = client.get_busy_intervals(
        datetime(2026, 8, 17, tzinfo=UTC), datetime(2026, 8, 24, tzinfo=UTC)
    )
    assert intervals == []


# ---------------------------------------------------------------------------
# ICS / mock fallback
# ---------------------------------------------------------------------------


def test_parse_ics_busy_intervals_timed_and_all_day_events() -> None:
    ics_text = textwrap.dedent(
        """\
        BEGIN:VCALENDAR
        VERSION:2.0
        BEGIN:VEVENT
        UID:1@example.com
        SUMMARY:Private therapy session nobody should see
        DTSTART:20260817T090000Z
        DTEND:20260817T100000Z
        END:VEVENT
        BEGIN:VEVENT
        UID:2@example.com
        SUMMARY:Family vacation
        DTSTART;VALUE=DATE:20260818
        DTEND;VALUE=DATE:20260820
        END:VEVENT
        END:VCALENDAR
        """
    )

    intervals = parse_ics_busy_intervals(ics_text)

    assert len(intervals) == 2
    timed, all_day = intervals[0], intervals[1]

    assert timed.all_day is False
    assert timed.start == datetime(2026, 8, 17, 9, 0, tzinfo=UTC)
    assert timed.end == datetime(2026, 8, 17, 10, 0, tzinfo=UTC)

    assert all_day.all_day is True
    assert all_day.start == datetime(2026, 8, 18, 0, 0, tzinfo=UTC)
    assert all_day.end == datetime(2026, 8, 20, 0, 0, tzinfo=UTC)

    dump = " ".join(repr(i) for i in intervals)
    assert "Private therapy session" not in dump
    assert "Family vacation" not in dump


def test_parse_ics_handles_folded_lines_and_missing_dtend_all_day() -> None:
    # A folded SUMMARY line (continuation starting with a space) plus an
    # all-day event with no DTEND, which RFC 5545 defaults to a 1-day span.
    ics_text = (
        "BEGIN:VEVENT\r\n"
        "SUMMARY:A very long summary that has been\r\n"
        " folded across two physical lines\r\n"
        "DTSTART;VALUE=DATE:20260821\r\n"
        "END:VEVENT\r\n"
    )

    intervals = parse_ics_busy_intervals(ics_text)

    assert len(intervals) == 1
    assert intervals[0].all_day is True
    assert intervals[0].start == datetime(2026, 8, 21, 0, 0, tzinfo=UTC)
    assert intervals[0].end == datetime(2026, 8, 22, 0, 0, tzinfo=UTC)


def test_mock_calendar_provider_filters_by_range() -> None:
    busy = [
        BusyInterval(
            start=datetime(2026, 8, 17, 9, 0, tzinfo=UTC),
            end=datetime(2026, 8, 17, 10, 0, tzinfo=UTC),
        ),
        BusyInterval(
            start=datetime(2026, 8, 25, 9, 0, tzinfo=UTC),
            end=datetime(2026, 8, 25, 10, 0, tzinfo=UTC),
        ),
    ]
    provider = MockCalendarProvider(busy)

    in_range = provider.get_busy_intervals(
        datetime(2026, 8, 17, tzinfo=UTC), datetime(2026, 8, 20, tzinfo=UTC)
    )

    assert len(in_range) == 1
    assert in_range[0].start == datetime(2026, 8, 17, 9, 0, tzinfo=UTC)
