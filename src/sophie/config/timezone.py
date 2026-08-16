"""Centralized timezone handling. Storage is always UTC; display/interpretation
converts at the edges using the configured local timezone."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sophie.config.settings import get_settings


def local_zone() -> ZoneInfo:
    return ZoneInfo(get_settings().sophie_timezone)


def utc_now() -> datetime:
    return datetime.now(UTC)


def local_now() -> datetime:
    return utc_now().astimezone(local_zone())


def to_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(local_zone())


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=local_zone())
    return dt.astimezone(UTC)


def assume_utc(dt: datetime) -> datetime:
    """Reattaches UTC tzinfo to an already-UTC-but-naive datetime, without
    shifting the wall-clock value (unlike `to_utc`, which assumes a naive
    input is in local time and converts it).

    SQLite has no native timezone-aware storage: SQLAlchemy's
    `DateTime(timezone=True)` columns silently round-trip to naive Python
    datetimes once read back from the database, even though the value
    written was UTC-aware (see docs/DECISIONS.md). Any code that compares a
    freshly-constructed aware datetime (e.g. `utc_now()`) against one loaded
    back from such a column must normalize both sides through this function
    first, or the subtraction raises `TypeError: can't subtract
    offset-naive and offset-aware datetimes`.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
