"""Shared calendar data contract. Pure data — no I/O, no `httpx`/`msal`/
SQLAlchemy imports (enforced by `tests/unit/test_architecture_boundaries.py`).

Per docs/PRIVACY.md, Sophie retains only busy/free intervals — start, end,
and an all-day flag — from any calendar source (live Microsoft Graph or a
local ICS/mock fallback). Event titles, bodies, and attendees are never
represented here and must never be threaded through this type.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BusyInterval:
    """One busy period on the calendar. Naive of *why* it is busy — only
    when, for how long, and whether it is an all-day (fully blocking) entry."""

    start: datetime
    end: datetime
    all_day: bool = False
