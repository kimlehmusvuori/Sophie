"""Real Microsoft Graph delegated calendar access via MSAL.

This is a public-client (desktop, no secret) OAuth2 flow: interactive sign-in
opens the user's browser, MSAL runs a local loopback listener on the port of
`MS_GRAPH_REDIRECT_URI`, and the resulting token set is cached to a file the
caller controls (`get_settings().token_cache_path`) — never inside
`data/sophie.db` (see docs/PRIVACY.md, docs/OUTLOOK_SETUP.md).

Privacy contract enforced in this module:

- Reading events (`get_busy_intervals`) requests only `start`, `end`,
  `isAllDay` from Graph (`$select`) and immediately discards the rest of the
  JSON payload — event subject/body/attendees are never assigned to a local
  variable that outlives the parsing of a single event, let alone returned.
- Writing events (`create_sophie_event`) is the one place Sophie sends a
  subject/body to Graph — that content is Sophie's own generated training
  note, not user calendar data, and every event Sophie creates is tagged with
  a stable `singleValueExtendedProperties` marker (`SOPHIE_OWNED_PROPERTY_ID`)
  so a future sync can find, update, or delete *only* Sophie's own events.

Not-connected behavior (docs/OUTLOOK_SETUP.md §4): if `client_id` is falsy,
or no signed-in account is cached, `get_busy_intervals` returns an empty list
immediately — no network attempt, no exception. Call `connection_status()`
to distinguish "not configured" from "not signed in" from "connected" for
UI display. Only explicit write actions (create/update/delete/list Sophie's
own events) raise `CalendarNotSignedInError` when no usable token exists,
since those happen only after the user explicitly asks Sophie to write to
Outlook and a clear failure is more useful there than silent no-ops.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
import msal

from sophie.domain.calendar_types import BusyInterval

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
DEFAULT_SCOPES = ["Calendars.ReadWrite", "User.Read"]

# Stable identifier for events Sophie itself creates, so a future sync can
# find/update/delete only Sophie's own events and never touch unrelated
# calendar entries. The GUID is arbitrary but must stay stable once chosen.
SOPHIE_OWNED_PROPERTY_ID = "String {66f5a359-4659-4830-9070-00047ec6ac6e} Name sophie_owned"
SOPHIE_OWNED_PROPERTY_VALUE = "true"

ConnectionStatus = Literal["not_configured", "not_signed_in", "connected"]

_TIMEOUT_S = 15.0
_MAX_PAGES = 20


class CalendarNotSignedInError(RuntimeError):
    """Raised by write/list operations when Graph is configured but no
    signed-in account/token is available. Read-path (`get_busy_intervals`)
    never raises this — it degrades to an empty list instead."""


@dataclass(frozen=True)
class SophieOwnedEvent:
    """A calendar event Sophie itself created (identified by the
    `sophie_owned` extended property), for future update/delete. Carries only
    the Graph event id plus the same busy-interval shape as everything
    else — never subject/body."""

    event_id: str
    start: datetime
    end: datetime
    all_day: bool


class GraphCalendarClient:
    """Wraps `msal.PublicClientApplication` for the interactive desktop
    (public client) auth flow plus the handful of Graph calendar REST calls
    Sophie needs. One instance per profile/config; cheap to construct."""

    def __init__(
        self,
        client_id: str | None,
        tenant_id: str,
        redirect_uri: str,
        token_cache_path: Path,
        scopes: list[str] | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.redirect_uri = redirect_uri
        self.token_cache_path = token_cache_path
        self.scopes = scopes or list(DEFAULT_SCOPES)
        self._http_client = http_client

    # -- configuration / connection state ---------------------------------

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id)

    def connection_status(self) -> ConnectionStatus:
        """Local-only check (no network): not_configured / not_signed_in /
        connected. Safe to call unconditionally from UI status displays."""

        if not self.is_configured:
            return "not_configured"
        if self._cached_account() is None:
            return "not_signed_in"
        return "connected"

    # -- token cache / MSAL plumbing ---------------------------------------

    def _load_cache(self) -> msal.SerializableTokenCache:
        cache = msal.SerializableTokenCache()
        if self.token_cache_path.exists():
            with contextlib.suppress(OSError, ValueError):
                cache.deserialize(self.token_cache_path.read_text(encoding="utf-8"))
        return cache

    def _save_cache(self, cache: msal.SerializableTokenCache) -> None:
        if not cache.has_state_changed:
            return
        self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_cache_path.write_text(cache.serialize(), encoding="utf-8")
        with contextlib.suppress(OSError):
            self.token_cache_path.chmod(0o600)

    def _build_app(self, cache: msal.SerializableTokenCache) -> msal.PublicClientApplication:
        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        return msal.PublicClientApplication(self.client_id, authority=authority, token_cache=cache)

    def _cached_account(self) -> dict[str, Any] | None:
        """Best-effort local (no network) check for a cached account."""

        if not self.is_configured:
            return None
        cache = self._load_cache()
        app = self._build_app(cache)
        accounts = app.get_accounts()
        return accounts[0] if accounts else None

    def _acquire_token_silent(self) -> str | None:
        """Local cache lookup, refreshing over the network only if a
        cached refresh token exists. Returns None (never raises) when no
        usable account/token is available."""

        if not self.is_configured:
            return None
        cache = self._load_cache()
        app = self._build_app(cache)
        accounts = app.get_accounts()
        if not accounts:
            return None
        result = app.acquire_token_silent(self.scopes, account=accounts[0])
        self._save_cache(cache)
        if result is None or "access_token" not in result:
            return None
        return str(result["access_token"])

    def authenticate_interactive(self) -> bool:
        """Opens the system browser for interactive sign-in via a loopback
        redirect listener, per docs/OUTLOOK_SETUP.md. Only call this in
        response to an explicit user "Connect Outlook" action."""

        if not self.is_configured:
            raise CalendarNotSignedInError(
                "Cannot start sign-in: MS_GRAPH_CLIENT_ID is not configured."
            )
        cache = self._load_cache()
        app = self._build_app(cache)
        port = urlparse(self.redirect_uri).port or 8765
        result = app.acquire_token_interactive(scopes=self.scopes, port=port)
        self._save_cache(cache)
        return bool(result and "access_token" in result)

    # -- HTTP helpers --------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        *,
        token: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {token}",
            "Prefer": 'outlook.timezone="UTC"',
        }
        if self._http_client is not None:
            response = self._http_client.request(
                method, url, headers=headers, params=params, json=json_body, timeout=_TIMEOUT_S
            )
        else:
            response = httpx.request(
                method, url, headers=headers, params=params, json=json_body, timeout=_TIMEOUT_S
            )
        response.raise_for_status()
        return response

    # -- reads: only start/end/all-day ever leave this module ---------------

    def get_busy_intervals(self, start: datetime, end: datetime) -> list[BusyInterval]:
        """Fetch busy intervals for [start, end) via /me/calendarview.

        Requests only start/end/isAllDay from Graph and discards everything
        else immediately while parsing each event — no subject, body, or
        attendee data is ever assigned to a variable here, per docs/PRIVACY.md.

        Returns an empty list (never raises) if calendar is not configured or
        no signed-in account is available — the product must work fully with
        calendar unconfigured."""

        token = self._acquire_token_silent()
        if token is None:
            return []

        url = f"{GRAPH_BASE_URL}/me/calendarview"
        params = {
            "startDateTime": start.isoformat(),
            "endDateTime": end.isoformat(),
            "$select": "start,end,isAllDay",
            "$top": "50",
        }
        intervals: list[BusyInterval] = []
        pages = 0
        while url and pages < _MAX_PAGES:
            response = self._request("GET", url, token=token, params=params if pages == 0 else None)
            payload = response.json()
            for raw_event in payload.get("value", []):
                interval = _extract_busy_interval(raw_event)
                if interval is not None:
                    intervals.append(interval)
            url = payload.get("@odata.nextLink") or ""
            pages += 1
        return intervals

    # -- writes: Sophie's own events only ------------------------------------

    def create_sophie_event(
        self,
        subject: str,
        start: datetime,
        end: datetime,
        all_day: bool = False,
    ) -> str:
        """Creates a calendar event for an approved Sophie training session,
        tagged with the sophie_owned extended property. Returns the new
        Graph event id. Raises CalendarNotSignedInError if not signed in."""

        token = self._acquire_token_silent()
        if token is None:
            raise CalendarNotSignedInError("Cannot write to Outlook: not signed in.")

        body = {
            "subject": subject,
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
            "isAllDay": all_day,
            "singleValueExtendedProperties": [
                {"id": SOPHIE_OWNED_PROPERTY_ID, "value": SOPHIE_OWNED_PROPERTY_VALUE}
            ],
        }
        response = self._request("POST", f"{GRAPH_BASE_URL}/me/events", token=token, json_body=body)
        event_id = response.json().get("id")
        if not isinstance(event_id, str):
            raise CalendarNotSignedInError("Graph did not return an event id.")
        return event_id

    def list_sophie_events(self, start: datetime, end: datetime) -> list[SophieOwnedEvent]:
        """Lists only events Sophie itself created (filtered server-side by
        the sophie_owned extended property) in [start, end) — never
        unrelated events. Raises CalendarNotSignedInError if not signed in."""

        token = self._acquire_token_silent()
        if token is None:
            raise CalendarNotSignedInError("Cannot read Outlook: not signed in.")

        filter_clause = (
            f"start/dateTime ge '{start.isoformat()}' and "
            f"end/dateTime le '{end.isoformat()}' and "
            "singleValueExtendedProperties/Any(ep: ep/id eq "
            f"'{SOPHIE_OWNED_PROPERTY_ID}' and ep/value eq "
            f"'{SOPHIE_OWNED_PROPERTY_VALUE}')"
        )
        params = {"$filter": filter_clause, "$select": "id,start,end,isAllDay", "$top": "50"}
        url = f"{GRAPH_BASE_URL}/me/events"
        events: list[SophieOwnedEvent] = []
        pages = 0
        while url and pages < _MAX_PAGES:
            response = self._request("GET", url, token=token, params=params if pages == 0 else None)
            payload = response.json()
            for raw_event in payload.get("value", []):
                interval = _extract_busy_interval(raw_event)
                event_id = raw_event.get("id")
                if interval is not None and isinstance(event_id, str):
                    events.append(
                        SophieOwnedEvent(
                            event_id=event_id,
                            start=interval.start,
                            end=interval.end,
                            all_day=interval.all_day,
                        )
                    )
            url = payload.get("@odata.nextLink") or ""
            pages += 1
        return events

    def update_sophie_event(self, event_id: str, start: datetime, end: datetime) -> None:
        """Updates the start/end of one of Sophie's own events (by id, as
        returned from `list_sophie_events`/`create_sophie_event`). Never
        call this with an id you did not get from this module."""

        token = self._acquire_token_silent()
        if token is None:
            raise CalendarNotSignedInError("Cannot write to Outlook: not signed in.")
        body = {
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
        }
        self._request(
            "PATCH", f"{GRAPH_BASE_URL}/me/events/{event_id}", token=token, json_body=body
        )

    def delete_sophie_event(self, event_id: str) -> None:
        """Deletes one of Sophie's own events by id."""

        token = self._acquire_token_silent()
        if token is None:
            raise CalendarNotSignedInError("Cannot write to Outlook: not signed in.")
        self._request("DELETE", f"{GRAPH_BASE_URL}/me/events/{event_id}", token=token)


def _extract_busy_interval(raw_event: dict[str, Any]) -> BusyInterval | None:
    """Pulls only start/end/isAllDay out of one Graph event JSON object and
    discards everything else. This is the single choke point that keeps
    subject/body/attendees from ever escaping the Graph client."""

    start_obj = raw_event.get("start")
    end_obj = raw_event.get("end")
    if not isinstance(start_obj, dict) or not isinstance(end_obj, dict):
        return None
    start_dt = _parse_graph_datetime(start_obj)
    end_dt = _parse_graph_datetime(end_obj)
    if start_dt is None or end_dt is None:
        return None
    all_day = bool(raw_event.get("isAllDay", False))
    return BusyInterval(start=start_dt, end=end_dt, all_day=all_day)


def _parse_graph_datetime(obj: dict[str, Any]) -> datetime | None:
    """Graph's {"dateTime": "...", "timeZone": "..."} shape. We request
    Prefer: outlook.timezone="UTC", so dateTime arrives as a naive
    UTC-wall-clock string; attach UTC tzinfo explicitly."""

    raw = obj.get("dateTime")
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed
