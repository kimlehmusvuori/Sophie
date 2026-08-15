"""The current editable four-week running block (seeded per docs/PRODUCT_SPEC.md
§16), plus the weekly training rules (§17-18) as pure, testable predicates.

The block itself is data, not hard-coded planning logic — future blocks are
just another BlockWeek list. Nothing here assumes *this* is the only block
that will ever exist.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SessionType(StrEnum):
    LONG = "long"
    QUALITY = "quality"
    EASY = "easy"
    PADEL = "padel"
    OTHER = "other"


class QualitySessionSpec(BaseModel):
    description: str
    rpe_hint: str | None = None


class BlockWeek(BaseModel):
    """One week of the active running block. Distances are (low, high) km
    ranges to leave room for real-world judgement, not a single fake-precise
    number."""

    week_number: int
    quality: QualitySessionSpec
    easy_km_low: float
    easy_km_high: float
    long_km_low: float
    long_km_high: float
    long_km_conditional_high: float | None = None
    long_km_conditional_note: str | None = None
    notes: str | None = None


DEFAULT_FOUR_WEEK_BLOCK: list[BlockWeek] = [
    BlockWeek(
        week_number=1,
        quality=QualitySessionSpec(
            description="6 x 250m uphill", rpe_hint="~8/10, hard and controlled, not maximal"
        ),
        easy_km_low=8,
        easy_km_high=9,
        long_km_low=13.5,
        long_km_high=14.5,
        notes="Optional 4 x ~10s hill strides on an easy day.",
    ),
    BlockWeek(
        week_number=2,
        quality=QualitySessionSpec(
            description="3 x 8min controlled threshold, 2-3min easy between"
        ),
        easy_km_low=9,
        easy_km_high=10,
        long_km_low=14.5,
        long_km_high=15.5,
    ),
    BlockWeek(
        week_number=3,
        quality=QualitySessionSpec(description="7 x 250m uphill"),
        easy_km_low=9,
        easy_km_high=11,
        long_km_low=15,
        long_km_high=16,
        long_km_conditional_high=17,
        long_km_conditional_note=(
            "16-17km only if prior training/recovery has gone well; otherwise ~15-16km."
        ),
    ),
    BlockWeek(
        week_number=4,
        quality=QualitySessionSpec(description="3 x 6min controlled threshold"),
        easy_km_low=7,
        easy_km_high=9,
        long_km_low=12,
        long_km_high=14,
        notes="Down week.",
    ),
]

ALLOWED_QUALITY_KEYWORDS = (
    "threshold",
    "uphill",
    "hill",
    "steady",
    "stride",
    "progression",
)

DISALLOWED_QUALITY_KEYWORDS = (
    "sprint",
    "vo2",
    "maximal",
    "all-out",
    "time trial",
    "race pace repeat",
)


def is_permissible_quality_session(description: str) -> bool:
    """Allowed: controlled threshold, uphill repetitions, easy/steady
    progression, short strides, ~3x5min steady. Disallowed: hero workouts,
    maximal sprinting, aggressive VO2max programming."""

    text = description.lower()
    if any(bad in text for bad in DISALLOWED_QUALITY_KEYWORDS):
        return False
    return any(good in text for good in ALLOWED_QUALITY_KEYWORDS)


class WeeklyConstraint(BaseModel):
    max_running_sessions: int = Field(default=3, ge=0, le=3)
    max_quality_sessions: int = Field(default=1, ge=0, le=1)
    padel_weekday: int | None = 3  # Monday=0 ... Thursday=3


def session_priority_order() -> list[SessionType]:
    """1. long run  2. quality  3. easy run — used when a constrained week
    can only fit fewer than 3 running sessions."""

    return [SessionType.LONG, SessionType.QUALITY, SessionType.EASY]


def block_week_for(week_index_in_block: int, block: list[BlockWeek] | None = None) -> BlockWeek:
    """week_index_in_block is 1-based and wraps once the block repeats
    (weeks 5, 9, ... map back onto week 1 of the block)."""

    weeks = block or DEFAULT_FOUR_WEEK_BLOCK
    idx = (week_index_in_block - 1) % len(weeks)
    return weeks[idx]
