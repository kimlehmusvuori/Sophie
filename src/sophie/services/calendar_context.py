"""Bridges the calendar provider(s) + calendar feasibility engine + weather
into what Sunday Review needs. See docs/PRODUCT_SPEC.md §44-45 Step E.

Busy-interval source priority for a given week:
1. Live Microsoft Graph, if configured and already signed in.
2. The most recently saved `calendar_snapshot` for that week (e.g. from an
   ICS upload via the UI).
3. An empty list — planning must continue even with zero calendar info.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from sophie.config.settings import Settings
from sophie.db.models import CalendarSnapshot, UserConfig
from sophie.domain.calendar_types import BusyInterval
from sophie.domain.coach_types import CalendarWindow, RejectedWindow
from sophie.domain.training_block import SessionType
from sophie.providers.calendar.graph_client import GraphCalendarClient
from sophie.providers.calendar.mock_provider import parse_ics_busy_intervals
from sophie.repositories import planning_repo, weather_repo
from sophie.services.calendar_feasibility import (
    SchedulingPreferences,
    WeatherContext,
    compute_feasible_windows,
)


def scheduling_preferences_from_config(config: UserConfig) -> SchedulingPreferences:
    return SchedulingPreferences(
        dropoff_start=config.dropoff_start,
        dropoff_end=config.dropoff_end,
        earliest_weekday_session=config.earliest_weekday_session,
        latest_session=config.latest_session,
        long_run_weekday_preference=list(config.long_run_weekday_preference or []),
        padel_weekday=config.padel_weekday,
        preserve_rest_day=config.preserve_rest_day,
    )


@dataclass
class CalendarFetchResult:
    busy_intervals: list[BusyInterval]
    source: str  # graph/ics_fallback/mock/none


def fetch_busy_intervals_for_week(
    session: Session, profile_id: str, week_start: date, settings: Settings
) -> CalendarFetchResult:
    week_end_exclusive = week_start + timedelta(days=7)
    start_dt = datetime.combine(week_start, time.min)
    end_dt = datetime.combine(week_end_exclusive, time.min)

    if settings.calendar_configured:
        client = GraphCalendarClient(
            client_id=settings.ms_graph_client_id,
            tenant_id=settings.ms_graph_tenant_id,
            redirect_uri=settings.ms_graph_redirect_uri,
            token_cache_path=settings.token_cache_path,
        )
        if client.connection_status() == "connected":
            intervals = client.get_busy_intervals(start_dt, end_dt)
            planning_repo.save_calendar_snapshot(
                session, profile_id, week_start, _serialize(intervals), source="graph"
            )
            return CalendarFetchResult(busy_intervals=intervals, source="graph")

    snapshot = session.execute(
        select(CalendarSnapshot)
        .where(CalendarSnapshot.profile_id == profile_id, CalendarSnapshot.week_start == week_start)
        .order_by(CalendarSnapshot.fetched_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if snapshot is not None:
        return CalendarFetchResult(
            busy_intervals=_deserialize(snapshot.busy_intervals), source=snapshot.source
        )

    return CalendarFetchResult(busy_intervals=[], source="none")


def save_ics_upload(
    session: Session, profile_id: str, week_start: date, ics_text: str
) -> CalendarFetchResult:
    intervals = parse_ics_busy_intervals(ics_text)
    planning_repo.save_calendar_snapshot(
        session, profile_id, week_start, _serialize(intervals), source="ics_fallback"
    )
    return CalendarFetchResult(busy_intervals=intervals, source="ics_fallback")


def _serialize(intervals: list[BusyInterval]) -> list[dict]:
    return [
        {"start": i.start.isoformat(), "end": i.end.isoformat(), "all_day": i.all_day}
        for i in intervals
    ]


def _deserialize(raw: list[dict]) -> list[BusyInterval]:
    return [
        BusyInterval(
            start=datetime.fromisoformat(i["start"]),
            end=datetime.fromisoformat(i["end"]),
            all_day=i.get("all_day", False),
        )
        for i in raw
    ]


def weather_context_by_date(
    session: Session, profile_id: str, week_start: date
) -> dict[date, WeatherContext]:
    week_end = week_start + timedelta(days=6)
    snapshots = weather_repo.list_weather_for_range(session, profile_id, week_start, week_end)
    return {
        s.for_date: WeatherContext(
            temp_c=s.temp_c,
            precip_mm=s.precip_mm,
            wind_kph=s.wind_kph,
            condition_summary=s.condition_summary,
        )
        for s in snapshots
    }


class GraphEventWriter:
    """Adapts GraphCalendarClient to sophie.services.sunday_review.CalendarEventWriter."""

    def __init__(self, client: GraphCalendarClient) -> None:
        self._client = client

    def create_event(self, start_at: datetime, end_at: datetime, subject: str) -> str:
        return self._client.create_sophie_event(subject, start_at, end_at)


def build_graph_client(settings: Settings) -> GraphCalendarClient:
    return GraphCalendarClient(
        client_id=settings.ms_graph_client_id,
        tenant_id=settings.ms_graph_tenant_id,
        redirect_uri=settings.ms_graph_redirect_uri,
        token_cache_path=settings.token_cache_path,
    )


def build_calendar_windows(
    session: Session,
    profile_id: str,
    week_start: date,
    config: UserConfig,
    training_load_status: str,
    recovery_status: str,
    busy_intervals: list[BusyInterval],
    session_duration_min: int = 60,
    buffer_min: int = 15,
) -> tuple[list[CalendarWindow], list[RejectedWindow]]:
    preferences = scheduling_preferences_from_config(config)
    weather_by_date = weather_context_by_date(session, profile_id, week_start)

    return compute_feasible_windows(
        week_start,
        busy_intervals,
        session_duration_min,
        buffer_min,
        preferences,
        training_load_status,
        recovery_status,
        weather_by_date,
        session_type=SessionType.LONG,
    )
