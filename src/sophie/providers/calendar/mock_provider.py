"""Calendar fallback for when live Microsoft Graph access isn't configured
or hasn't been signed into yet: an in-memory mock provider, and a small
hand-rolled ICS parser that turns a user-supplied `.ics` export (e.g.
exported from Outlook/Google/Apple Calendar) into the same busy/free
interval shape Sophie uses everywhere else.

Per docs/PRODUCT_SPEC.md / docs/OUTLOOK_SETUP.md, Sophie must remain fully
usable with zero live credentials — this module is what makes that true for
calendar-aware planning: point Sophie at an exported `.ics` file and it gets
*real* availability without any Graph app registration.

Only DTSTART/DTEND/(VALUE=DATE all-day) are extracted from each VEVENT.
SUMMARY (and any other field) is read only long enough to skip past it and
is never retained or returned — same busy-interval-only contract as the live
Graph client (see docs/PRIVACY.md).

This is a deliberately minimal RFC 5545 subset, not a full ICS library:
- Line folding (continuation lines starting with a space/tab) is unfolded.
- DTSTART/DTEND values are parsed either as `YYYYMMDD` (all-day) or
  `YYYYMMDDTHHMMSS[Z]`, with an optional `TZID=...` parameter resolved via
  the stdlib `zoneinfo` database when present.
- RRULE (recurrence) is not expanded — only the literal VEVENT occurrences
  present in the file are returned. Good enough for "what does my exported
  calendar say for this week", not a general-purpose calendar engine.
No third-party ICS dependency is added — `pyproject.toml` has none, and this
hand-rolled parser is sufficient for the common case, per project brief.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sophie.domain.calendar_types import BusyInterval

_DATE_ONLY_RE = re.compile(r"^\d{8}$")
_DATETIME_RE = re.compile(r"^(\d{8})T(\d{6})(Z)?$")


class MockCalendarProvider:
    """Deterministic in-memory calendar provider for tests/demo mode. Not
    backed by any file or network call — just a fixed list of busy
    intervals handed in by the caller."""

    def __init__(self, busy_intervals: list[BusyInterval] | None = None) -> None:
        self._busy_intervals = list(busy_intervals or [])

    def get_busy_intervals(self, start: datetime, end: datetime) -> list[BusyInterval]:
        return [b for b in self._busy_intervals if b.start < end and b.end > start]


def parse_ics_busy_intervals(ics_text: str) -> list[BusyInterval]:
    """Parses a `.ics` document's VEVENT blocks into busy intervals. Never
    returns SUMMARY/DESCRIPTION/ATTENDEE content — only start/end/all-day."""

    lines = _unfold_lines(ics_text)
    intervals: list[BusyInterval] = []
    in_event = False
    dtstart: datetime | date | None = None
    dtend: datetime | date | None = None

    for line in lines:
        stripped = line.strip()
        if stripped == "BEGIN:VEVENT":
            in_event = True
            dtstart = None
            dtend = None
            continue
        if stripped == "END:VEVENT":
            if in_event:
                interval = _build_interval(dtstart, dtend)
                if interval is not None:
                    intervals.append(interval)
            in_event = False
            dtstart = None
            dtend = None
            continue
        if not in_event or not stripped:
            continue

        name, _, rest = stripped.partition(":")
        if not rest:
            continue
        prop_name = name.split(";", 1)[0].upper()
        if prop_name == "DTSTART":
            dtstart = _parse_ics_datetime(name, rest)
        elif prop_name == "DTEND":
            dtend = _parse_ics_datetime(name, rest)
        # Any other property (SUMMARY, DESCRIPTION, ATTENDEE, LOCATION, ...)
        # is intentionally ignored here — never assigned, never retained.

    return intervals


def load_ics_file(path: str | Path) -> list[BusyInterval]:
    """Reads and parses a user-supplied `.ics` file from disk."""

    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return parse_ics_busy_intervals(text)


def _unfold_lines(ics_text: str) -> list[str]:
    """RFC 5545 line unfolding: a line that starts with a space or tab is a
    continuation of the previous line."""

    raw_lines = ics_text.replace("\r\n", "\n").split("\n")
    unfolded: list[str] = []
    for raw_line in raw_lines:
        if raw_line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += raw_line[1:]
        else:
            unfolded.append(raw_line)
    return unfolded


def _parse_ics_datetime(prop_field: str, value: str) -> datetime | date | None:
    value = value.strip()

    tzid: str | None = None
    is_all_day = False
    if ";" in prop_field:
        for param in prop_field.split(";")[1:]:
            if "=" not in param:
                continue
            key, _, val = param.partition("=")
            if key.upper() == "TZID":
                tzid = val
            elif key.upper() == "VALUE" and val.upper() == "DATE":
                is_all_day = True

    if is_all_day or _DATE_ONLY_RE.match(value):
        try:
            return datetime.strptime(value, "%Y%m%d").date()
        except ValueError:
            return None

    match = _DATETIME_RE.match(value)
    if not match:
        return None
    date_part, time_part, is_utc = match.groups()
    try:
        naive = datetime.strptime(date_part + time_part, "%Y%m%d%H%M%S")
    except ValueError:
        return None

    if is_utc:
        return naive.replace(tzinfo=UTC)
    if tzid:
        try:
            return naive.replace(tzinfo=ZoneInfo(tzid))
        except (ZoneInfoNotFoundError, ValueError):
            return naive.replace(tzinfo=UTC)
    return naive.replace(tzinfo=UTC)


def _build_interval(
    dtstart: datetime | date | None, dtend: datetime | date | None
) -> BusyInterval | None:
    if dtstart is None:
        return None

    all_day = isinstance(dtstart, date) and not isinstance(dtstart, datetime)
    if all_day:
        start_dt = datetime.combine(dtstart, datetime.min.time(), tzinfo=UTC)
        if dtend is not None:
            end_date = dtend if not isinstance(dtend, datetime) else dtend.date()
            end_dt = datetime.combine(end_date, datetime.min.time(), tzinfo=UTC)
        else:
            end_dt = start_dt + timedelta(days=1)
        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(days=1)
        return BusyInterval(start=start_dt, end=end_dt, all_day=True)

    assert isinstance(dtstart, datetime)  # narrowed above (not all_day)
    if dtend is None:
        return None
    end_dt = (
        dtend
        if isinstance(dtend, datetime)
        else datetime.combine(dtend, datetime.min.time(), tzinfo=dtstart.tzinfo)
    )
    if end_dt <= dtstart:
        return None
    return BusyInterval(start=dtstart, end=end_dt, all_day=False)
