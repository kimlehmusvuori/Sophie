"""Calendar provider: real Microsoft Graph delegated access (MSAL), plus an
always-available ICS/mock fallback. No sqlalchemy/streamlit imports here —
this package returns plain data (`sophie.domain.calendar_types.BusyInterval`
and friends); persistence and orchestration are a service layer's job.

Status of what's in this package:

- **Implemented, live-testable only with real Microsoft credentials**:
  `GraphCalendarClient` (interactive MSAL sign-in, `/me/calendarview` read,
  `/me/events` create/list/update/delete of Sophie-owned events). Covered by
  unit tests against a mocked `httpx` transport (`tests/unit/
  test_calendar_provider.py`) — no live Graph call has been made from this
  development environment; see docs/OUTLOOK_SETUP.md §6.
- **Implemented and always testable, no credentials needed**:
  `MockCalendarProvider` (in-memory, deterministic) and
  `parse_ics_busy_intervals`/`load_ics_file` (hand-rolled ICS parser). This
  is what keeps Sophie fully usable — "the product must work fully with
  calendar unconfigured" — with zero live Graph access: a user can export
  any calendar to `.ics` and get real busy/free data with no app
  registration at all.

Both paths return `sophie.domain.calendar_types.BusyInterval` — start, end,
all-day flag only. Event titles/bodies/attendees never appear in a return
value from anything in this package.
"""

from __future__ import annotations

from sophie.providers.calendar.graph_client import (
    DEFAULT_SCOPES,
    GRAPH_BASE_URL,
    SOPHIE_OWNED_PROPERTY_ID,
    SOPHIE_OWNED_PROPERTY_VALUE,
    CalendarNotSignedInError,
    ConnectionStatus,
    GraphCalendarClient,
    SophieOwnedEvent,
)
from sophie.providers.calendar.mock_provider import (
    MockCalendarProvider,
    load_ics_file,
    parse_ics_busy_intervals,
)

__all__ = [
    "GraphCalendarClient",
    "SophieOwnedEvent",
    "CalendarNotSignedInError",
    "ConnectionStatus",
    "DEFAULT_SCOPES",
    "GRAPH_BASE_URL",
    "SOPHIE_OWNED_PROPERTY_ID",
    "SOPHIE_OWNED_PROPERTY_VALUE",
    "MockCalendarProvider",
    "parse_ics_busy_intervals",
    "load_ics_file",
]
