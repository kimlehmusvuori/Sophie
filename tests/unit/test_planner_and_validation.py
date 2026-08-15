from __future__ import annotations

from datetime import date, time

from sophie.domain.coach_types import CalendarWindow, CoachContext, RecommendedSession, Verdict
from sophie.domain.coach_validation import validate_and_repair
from sophie.domain.planner import build_deterministic_plan, decide_verdict
from sophie.domain.training_block import SessionType, block_week_for


def _base_context(**overrides: object) -> CoachContext:
    defaults = dict(
        week_start=date(2026, 8, 17),
        current_block_week_number=1,
        max_runs_per_week=3,
        padel_weekday=3,
        race_name="Half marathon",
        race_date=date(2027, 5, 1),
        weight_goal_kg=79.0,
        current_weight_kg=90.0,
        last_week_planned_km=25.0,
        last_week_actual_km=24.0,
        last_week_completion_note=None,
        training_load_status="typical",
        recovery_status="normal",
        domain_statuses=[],
        calendar_windows=[
            CalendarWindow(
                date=date(2026, 8, 17 + i),
                start=time(8, 45),
                end=time(9, 45),
                weekday_name=name,
                rank_score=0.8,
            )
            for i, name in enumerate(["Monday", "Wednesday", "Saturday"])
        ],
        rejected_windows=[],
        pain_0_10=None,
        pain_location=None,
        stress_1_5=2,
        fasting_quality="good",
        weekly_note=None,
        sophie_memory=None,
    )
    defaults.update(overrides)
    return CoachContext(**defaults)


def test_verdict_build_when_all_clear():
    context = _base_context()
    verdict, reasons = decide_verdict(context, prior_completion_ratio=0.95)
    assert verdict == Verdict.BUILD
    assert 1 <= len(reasons) <= 3


def test_verdict_reduce_on_high_pain():
    context = _base_context(pain_0_10=5)
    verdict, _ = decide_verdict(context, prior_completion_ratio=0.9)
    assert verdict == Verdict.REDUCE


def test_verdict_minimum_viable_on_severe_pain():
    context = _base_context(pain_0_10=7)
    verdict, _ = decide_verdict(context, prior_completion_ratio=0.9)
    assert verdict == Verdict.MINIMUM_VIABLE


def test_verdict_reduce_on_recovery_concern():
    context = _base_context(recovery_status="concern")
    verdict, _ = decide_verdict(context, prior_completion_ratio=0.9)
    assert verdict == Verdict.REDUCE


def test_verdict_repeat_on_poor_completion():
    context = _base_context()
    verdict, _ = decide_verdict(context, prior_completion_ratio=0.4)
    assert verdict == Verdict.REPEAT


def test_deterministic_plan_never_exceeds_max_runs():
    context = _base_context()
    plan = build_deterministic_plan(context, block_week_number=1)
    assert len(plan.recommended_plan) <= context.max_runs_per_week
    quality_sessions = [s for s in plan.recommended_plan if s.session_type == SessionType.QUALITY]
    assert len(quality_sessions) <= 1


def test_deterministic_plan_conservative_alternative_is_lighter():
    context = _base_context()
    plan = build_deterministic_plan(context, block_week_number=1)
    rec_km = sum(s.distance_km or 0 for s in plan.recommended_plan)
    alt_km = sum(s.distance_km or 0 for s in plan.conservative_alternative.sessions)
    assert alt_km <= rec_km


def test_validation_drops_infeasible_dates():
    context = _base_context()
    week = block_week_for(1)
    bogus_session = RecommendedSession(
        date=date(2026, 9, 1),
        start_time=time(9, 0),
        session_type=SessionType.EASY,
        purpose="Easy run",
        distance_km=8,
    )
    from sophie.domain.coach_types import CoachRecommendation, ConservativeAlternative

    rec = CoachRecommendation(
        verdict=Verdict.BUILD,
        reasons=["test"],
        recommended_plan=[bogus_session],
        conservative_alternative=ConservativeAlternative(summary="lighter", sessions=[]),
    )
    result = validate_and_repair(rec, context, week)
    assert result.recommendation.recommended_plan == []
    assert any("infeasible" in n.lower() or "not a feasible" in n.lower() for n in result.notes)


def test_validation_rejects_disallowed_quality_style():
    context = _base_context()
    week = block_week_for(1)
    from sophie.domain.coach_types import CoachRecommendation, ConservativeAlternative

    bad_session = RecommendedSession(
        date=context.calendar_windows[0].date,
        start_time=time(9, 0),
        session_type=SessionType.QUALITY,
        purpose="All-out maximal sprint intervals",
        distance_km=None,
    )
    rec = CoachRecommendation(
        verdict=Verdict.BUILD,
        reasons=["test"],
        recommended_plan=[bad_session],
        conservative_alternative=ConservativeAlternative(summary="lighter", sessions=[]),
    )
    result = validate_and_repair(rec, context, week)
    assert result.safe is False


def test_validation_enforces_max_runs_per_week():
    context = _base_context(max_runs_per_week=2)
    week = block_week_for(1)
    from sophie.domain.coach_types import CoachRecommendation, ConservativeAlternative

    sessions = [
        RecommendedSession(
            date=w.date,
            start_time=w.start,
            session_type=SessionType.EASY,
            purpose="Easy run",
            distance_km=8,
        )
        for w in context.calendar_windows
    ]
    rec = CoachRecommendation(
        verdict=Verdict.BUILD,
        reasons=["test"],
        recommended_plan=sessions,
        conservative_alternative=ConservativeAlternative(summary="lighter", sessions=[]),
    )
    result = validate_and_repair(rec, context, week)
    assert len(result.recommendation.recommended_plan) <= 2


def test_validation_removes_quality_on_severe_pain():
    context = _base_context(pain_0_10=6)
    week = block_week_for(1)
    from sophie.domain.coach_types import CoachRecommendation, ConservativeAlternative

    quality_session = RecommendedSession(
        date=context.calendar_windows[0].date,
        start_time=time(9, 0),
        session_type=SessionType.QUALITY,
        purpose="Controlled threshold intervals",
        distance_km=None,
    )
    rec = CoachRecommendation(
        verdict=Verdict.BUILD,
        reasons=["test"],
        recommended_plan=[quality_session],
        conservative_alternative=ConservativeAlternative(summary="lighter", sessions=[]),
    )
    result = validate_and_repair(rec, context, week)
    assert all(
        s.session_type != SessionType.QUALITY for s in result.recommendation.recommended_plan
    )
    assert result.recommendation.verdict in (Verdict.REDUCE, Verdict.MINIMUM_VIABLE)


def test_block_week_wraps_after_four_weeks():
    week5 = block_week_for(5)
    week1 = block_week_for(1)
    assert week5.quality.description == week1.quality.description
