"""Typed structured output contract between the coach (deterministic + LLM)
and the rest of Sophie. See docs/PRODUCT_SPEC.md §49 and CLAUDE.md — the
deterministic validator (coach_validation.py) is what actually reaches the UI
for approval, never raw LLM output."""

from __future__ import annotations

from datetime import date, time
from enum import StrEnum

from pydantic import BaseModel, Field

from sophie.domain.training_block import SessionType


class Verdict(StrEnum):
    BUILD = "build"
    REPEAT = "repeat"
    REDUCE = "reduce"
    MINIMUM_VIABLE = "minimum_viable"


class RecommendedSession(BaseModel):
    date: date
    start_time: time | None = None
    session_type: SessionType
    purpose: str
    distance_km: float | None = None
    estimated_duration_min: int | None = None
    note: str | None = None


class ConservativeAlternative(BaseModel):
    summary: str
    sessions: list[RecommendedSession]


class CoachRecommendation(BaseModel):
    verdict: Verdict
    reasons: list[str] = Field(max_length=3)
    recommended_plan: list[RecommendedSession]
    conservative_alternative: ConservativeAlternative
    coach_note: str | None = None


class CalendarWindow(BaseModel):
    """One feasible scheduling window, as produced by the calendar
    feasibility engine. The LLM never invents these — it only selects among
    windows already computed deterministically."""

    date: date
    start: time
    end: time
    weekday_name: str
    rank_score: float
    notes: list[str] = Field(default_factory=list)


class RejectedWindow(BaseModel):
    date: date
    start: time
    end: time
    reason_code: str


class DomainStatus(BaseModel):
    """A single health-domain status line handed to the coach context — never
    a raw sample, always a pre-computed status + brief evidence summary."""

    domain: str
    status: str
    data_quality: str
    evidence_summary: str | None = None


class CoachContext(BaseModel):
    """Everything the LLM coach is allowed to see. Assembled by
    services/coach.py::build_context() from already-sanitized inputs only —
    see docs/PRIVACY.md."""

    week_start: date
    current_block_week_number: int
    max_runs_per_week: int
    padel_weekday: int | None
    race_name: str | None
    race_date: date | None
    weight_goal_kg: float | None
    current_weight_kg: float | None
    last_week_planned_km: float | None
    last_week_actual_km: float | None
    last_week_completion_note: str | None
    training_load_status: str  # low/typical/elevated/very_elevated
    recovery_status: str  # normal/watch/concern
    domain_statuses: list[DomainStatus]
    calendar_windows: list[CalendarWindow]
    rejected_windows: list[RejectedWindow]
    pain_0_10: int | None
    pain_location: str | None
    stress_1_5: int | None
    fasting_quality: str | None
    weekly_note: str | None
    sophie_memory: str | None
    explicit_exclusions: list[str] = Field(default_factory=list)
