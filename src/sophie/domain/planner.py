"""Deterministic training planner. This is what runs when no LLM is
configured/reachable, and it is also the source of truth the LLM's output is
validated/repaired against (coach_validation.py) — see docs/PRODUCT_SPEC.md
§46-50 and CLAUDE.md ("deterministic constraints outrank LLM recommendations").
"""

from __future__ import annotations

from datetime import date, timedelta

from sophie.domain.coach_types import (
    CalendarWindow,
    CoachContext,
    CoachRecommendation,
    ConservativeAlternative,
    RecommendedSession,
    Verdict,
)
from sophie.domain.training_block import (
    DEFAULT_FOUR_WEEK_BLOCK,
    BlockWeek,
    SessionType,
    block_week_for,
)

_HIGH_PAIN_THRESHOLD = 4
_SEVERE_PAIN_THRESHOLD = 6
_HIGH_STRESS_THRESHOLD = 4


def decide_verdict(
    context: CoachContext, prior_completion_ratio: float | None
) -> tuple[Verdict, list[str]]:
    """Returns the verdict plus up to three short, concrete reasons. Order of
    precedence: pain > recovery/load concerns > stress > completion history >
    default progression. Never more than one verdict returned."""

    reasons: list[str] = []

    if context.pain_0_10 is not None and context.pain_0_10 >= _SEVERE_PAIN_THRESHOLD:
        reasons.append(f"Pain reported at {context.pain_0_10}/10 — prioritizing recovery.")
        return Verdict.MINIMUM_VIABLE, reasons

    if context.pain_0_10 is not None and context.pain_0_10 >= _HIGH_PAIN_THRESHOLD:
        reasons.append(f"Pain reported at {context.pain_0_10}/10 — reducing running load.")
        return Verdict.REDUCE, reasons

    if context.recovery_status == "concern":
        reasons.append("Recovery context shows a concern signal across multiple markers.")
        return Verdict.REDUCE, reasons

    if context.training_load_status == "very_elevated":
        reasons.append("Recent training load is very elevated versus your own baseline.")
        return Verdict.REDUCE, reasons

    if context.recovery_status == "watch" or context.training_load_status == "elevated":
        reasons.append(
            "Recovery/load context is showing early signs of strain — holding steady rather "
            "than progressing."
        )
        if context.stress_1_5 is not None and context.stress_1_5 >= _HIGH_STRESS_THRESHOLD:
            reasons.append(f"Reported stress/mental load is {context.stress_1_5}/5.")
        return Verdict.REPEAT, reasons

    if context.stress_1_5 is not None and context.stress_1_5 >= _HIGH_STRESS_THRESHOLD:
        reasons.append(f"Reported stress/mental load is {context.stress_1_5}/5 — holding steady.")
        return Verdict.REPEAT, reasons

    if prior_completion_ratio is not None and prior_completion_ratio < 0.6:
        reasons.append("Last week's plan was only partially completed.")
        return Verdict.REPEAT, reasons

    reasons.append("Recovery, training load and completion history all look supportive.")
    if context.race_date:
        reasons.append(
            f"Building toward {context.race_name or 'the race goal'} on {context.race_date}."
        )
    return Verdict.BUILD, reasons


def _pick_window(
    windows: list[CalendarWindow],
    preferred_weekdays: list[str] | None = None,
    exclude_dates: set[date] | None = None,
) -> CalendarWindow | None:
    exclude_dates = exclude_dates or set()
    candidates = [w for w in windows if w.date not in exclude_dates]
    if not candidates:
        return None
    if preferred_weekdays:
        preferred = [w for w in candidates if w.weekday_name in preferred_weekdays]
        if preferred:
            candidates = preferred
    return max(candidates, key=lambda w: w.rank_score)


def _session_count_for_week(context: CoachContext, verdict: Verdict) -> int:
    base = min(context.max_runs_per_week, 3)
    available = len({w.date for w in context.calendar_windows})
    count = min(base, available) if available else base
    if verdict == Verdict.MINIMUM_VIABLE:
        count = min(count, 1)
    elif verdict == Verdict.REDUCE:
        count = min(count, max(1, base - 1))
    return max(0, count)


def build_deterministic_plan(
    context: CoachContext,
    block_week_number: int,
    block: list[BlockWeek] | None = None,
    prior_completion_ratio: float | None = None,
) -> CoachRecommendation:
    block_weeks = block or DEFAULT_FOUR_WEEK_BLOCK
    week = block_week_for(block_week_number, block_weeks)

    verdict, reasons = decide_verdict(context, prior_completion_ratio)
    session_count = _session_count_for_week(context, verdict)
    priority = [SessionType.LONG, SessionType.QUALITY, SessionType.EASY][:session_count]

    sessions: list[RecommendedSession] = []
    used_dates: set[date] = set()

    for session_type in priority:
        preferred = None
        if session_type == SessionType.LONG:
            preferred = ["Friday", "Saturday", "Sunday"]
        window = _pick_window(context.calendar_windows, preferred, used_dates)
        if window is None:
            continue
        used_dates.add(window.date)
        sessions.append(_build_session(session_type, window, week, verdict))

    conservative = _build_conservative_alternative(context, week, used_dates)

    return CoachRecommendation(
        verdict=verdict,
        reasons=reasons[:3],
        recommended_plan=sessions,
        conservative_alternative=conservative,
        coach_note="Deterministic plan (no LLM used)." if not sessions else None,
    )


def _build_session(
    session_type: SessionType, window: CalendarWindow, week: BlockWeek, verdict: Verdict
) -> RecommendedSession:
    reduce_factor = 0.85 if verdict == Verdict.REDUCE else 1.0
    if session_type == SessionType.LONG:
        distance = round(((week.long_km_low + week.long_km_high) / 2) * reduce_factor, 1)
        purpose = "Long run — easy, conversational effort."
    elif session_type == SessionType.QUALITY:
        distance = None
        purpose = f"Quality session — {week.quality.description}"
        if week.quality.rpe_hint:
            purpose += f" ({week.quality.rpe_hint})"
    else:
        distance = round(((week.easy_km_low + week.easy_km_high) / 2) * reduce_factor, 1)
        purpose = "Easy run — very easy, recovery-supportive pace."

    return RecommendedSession(
        date=window.date,
        start_time=window.start,
        session_type=session_type,
        purpose=purpose,
        distance_km=distance,
        estimated_duration_min=_estimate_duration(session_type, distance),
        note=None,
    )


def _estimate_duration(session_type: SessionType, distance_km: float | None) -> int | None:
    if session_type == SessionType.QUALITY:
        return 45
    if distance_km is None:
        return None
    # ~6:30/km easy-pace planning estimate, not a precise physiological prediction.
    return int(round(distance_km * 6.5))


def _build_conservative_alternative(
    context: CoachContext, week: BlockWeek, used_dates: set[date]
) -> ConservativeAlternative:
    window = _pick_window(context.calendar_windows, None, set())
    sessions: list[RecommendedSession] = []
    if window is not None:
        easy_km = round(week.easy_km_low * 0.8, 1)
        sessions.append(
            RecommendedSession(
                date=window.date,
                start_time=window.start,
                session_type=SessionType.EASY,
                purpose="Conservative alternative — one short, genuinely easy run.",
                distance_km=easy_km,
                estimated_duration_min=int(round(easy_km * 6.5)),
            )
        )
    return ConservativeAlternative(
        summary="A single easy run (or a walk) — genuinely lighter than the recommended plan.",
        sessions=sessions,
    )


def week_start_for(today: date) -> date:
    """Sunday Review's 'week_start' is the Monday of the upcoming week."""
    days_until_monday = (7 - today.weekday()) % 7 or 7
    return today + timedelta(days=days_until_monday)
