"""Deterministic post-validation of any LLM-proposed plan. This module is the
enforcement point for CLAUDE.md's "deterministic constraints outrank LLM
recommendations" rule and docs/PRODUCT_SPEC.md §50.

validate_and_repair() either returns a repaired-safe recommendation (with an
audit trail of what was changed) or reports that the recommendation could not
be safely repaired, in which case the caller (services/coach.py) should
attempt one structured regeneration and, failing that, fall back to
domain.planner.build_deterministic_plan().
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sophie.domain.coach_types import CoachContext, CoachRecommendation, RecommendedSession, Verdict
from sophie.domain.training_block import BlockWeek, SessionType, is_permissible_quality_session

_LONG_RUN_TOLERANCE = 0.1  # 10% slack either side of the block's stated range


@dataclass
class ValidationResult:
    recommendation: CoachRecommendation
    notes: list[str] = field(default_factory=list)
    safe: bool = True


def validate_and_repair(
    recommendation: CoachRecommendation,
    context: CoachContext,
    block_week: BlockWeek,
) -> ValidationResult:
    notes: list[str] = []
    safe = True
    feasible_dates = {w.date for w in context.calendar_windows}

    sessions = list(recommendation.recommended_plan)

    # 1. Drop sessions on dates the calendar feasibility engine did not offer.
    kept: list[RecommendedSession] = []
    for s in sessions:
        if s.session_type == SessionType.PADEL:
            kept.append(s)
            continue
        if feasible_dates and s.date not in feasible_dates:
            notes.append(f"Dropped {s.session_type} on {s.date}: not a feasible calendar window.")
            continue
        kept.append(s)
    sessions = kept

    # 2. Enforce max running sessions/week, respecting long > quality > easy priority.
    running_sessions = [s for s in sessions if s.session_type != SessionType.PADEL]
    if len(running_sessions) > context.max_runs_per_week:
        priority = {
            SessionType.LONG: 0,
            SessionType.QUALITY: 1,
            SessionType.EASY: 2,
            SessionType.OTHER: 3,
        }
        running_sessions.sort(key=lambda s: priority.get(s.session_type, 9))
        overflow = running_sessions[context.max_runs_per_week :]
        running_sessions = running_sessions[: context.max_runs_per_week]
        for s in overflow:
            notes.append(
                f"Dropped extra {s.session_type} on {s.date}: exceeds "
                f"max {context.max_runs_per_week} runs/week."
            )
        sessions = [s for s in sessions if s.session_type == SessionType.PADEL] + running_sessions

    # 3. Enforce at most one quality session.
    quality_sessions = [s for s in sessions if s.session_type == SessionType.QUALITY]
    if len(quality_sessions) > 1:
        for extra in quality_sessions[1:]:
            notes.append(
                f"Dropped extra quality session on {extra.date}: only one quality session allowed."
            )
        keep_first = quality_sessions[0]
        sessions = [s for s in sessions if s.session_type != SessionType.QUALITY] + [keep_first]

    # 4. Quality session content must be within the permitted style; unsafe to auto-repair text.
    for s in sessions:
        if s.session_type == SessionType.QUALITY and not is_permissible_quality_session(s.purpose):
            notes.append(
                f"Quality session on {s.date} ('{s.purpose}') is outside permitted quality styles "
                "(no hero workouts / maximal sprinting / aggressive VO2max programming)."
            )
            safe = False

    # 5. Long run distance must respect the block's range (with small tolerance); clamp if numeric.
    long_low = block_week.long_km_low
    long_high = block_week.long_km_conditional_high or block_week.long_km_high
    for s in sessions:
        if s.session_type == SessionType.LONG and s.distance_km is not None:
            low_bound = long_low * (1 - _LONG_RUN_TOLERANCE)
            high_bound = long_high * (1 + _LONG_RUN_TOLERANCE)
            if s.distance_km < low_bound or s.distance_km > high_bound:
                clamped = min(max(s.distance_km, long_low), long_high)
                notes.append(
                    f"Clamped long run distance from {s.distance_km}km to {clamped}km "
                    f"(block range {long_low}-{long_high}km)."
                )
                s.distance_km = round(clamped, 1)

    # 6. Pain/recovery gating: severe pain or a recovery concern must not carry a quality session.
    blocks_hard_running = (
        context.pain_0_10 is not None and context.pain_0_10 >= 6
    ) or context.recovery_status == "concern"
    if blocks_hard_running:
        remaining: list[RecommendedSession] = []
        for s in sessions:
            if s.session_type == SessionType.QUALITY:
                notes.append(
                    f"Removed quality session on {s.date}: pain/recovery gating is active."
                )
                continue
            remaining.append(s)
        sessions = remaining
        if recommendation.verdict not in (Verdict.REDUCE, Verdict.MINIMUM_VIABLE):
            notes.append("Verdict overridden toward a lighter week due to pain/recovery gating.")
            recommendation = recommendation.model_copy(update={"verdict": Verdict.REDUCE})

    # 7. Conservative alternative must genuinely be lighter than the recommended plan.
    rec_km = sum(s.distance_km or 0 for s in sessions)
    alt_km = sum(s.distance_km or 0 for s in recommendation.conservative_alternative.sessions)
    if recommendation.conservative_alternative.sessions and alt_km >= rec_km and rec_km > 0:
        notes.append(
            "Conservative alternative was not genuinely lighter than the recommended plan."
        )
        safe = False

    repaired = recommendation.model_copy(update={"recommended_plan": sessions})
    return ValidationResult(recommendation=repaired, notes=notes, safe=safe)
