"""Typed contract for the free-form Chat feature. See docs/PRIVACY.md — like
CoachContext, ChatContext is the only shape allowed to reach a chat LLM
provider, and it is assembled exclusively from already-derived summary/status
data (sophie.services.chat_context.build_chat_context()) — never raw
Apple Health/Sports Tracker/clinical rows."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from sophie.domain.coach_types import DomainStatus


class MetricAverage(BaseModel):
    """A single already-aggregated number over a trailing window — e.g. "avg
    resting HR over the last 30 days: 54 bpm (data on 27 of 30 days)". Never a
    raw per-sample series."""

    label: str
    value: float | None
    unit: str
    window_days: int
    days_with_data: int


class ChatTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatContext(BaseModel):
    """Everything the chat LLM is allowed to see for one question. Contains
    only pre-computed domain statuses, rounded trailing-window averages, and
    user-entered goals/preferences/memory — the same category of data
    docs/PRIVACY.md allows for the structured coach, generalized to
    open-ended Q&A."""

    domain_statuses: list[DomainStatus]
    metric_averages: list[MetricAverage]
    race_name: str | None
    race_date: date | None
    weight_goal_kg: float | None
    current_weight_kg: float | None
    max_runs_per_week: int
    sophie_memory: str | None
    explicit_exclusions: list[str] = Field(default_factory=list)
