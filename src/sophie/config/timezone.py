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
