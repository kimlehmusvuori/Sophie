"""Planner scenario tests — see docs/PRODUCT_SPEC.md and CLAUDE.md's testing
philosophy: assert invariants (what must always be true), not exact prose.
Each test is labelled with the scenario it covers from the build brief's
planner-scenario checklist.
"""

from __future__ import annotations

from datetime import date, time, timedelta

from sophie.domain.coach_types import (
    CalendarWindow,
    CoachContext,
    CoachRecommendation,
    ConservativeAlternative,
    DomainStatus,
    RecommendedSession,
    Verdict,
)
from sophie.domain.coach_validation import validate_and_repair
from sophie.domain.planner import build_deterministic_plan
from sophie.domain.training_block import SessionType, block_week_for
from sophie.services.calendar_feasibility import (
    SchedulingPreferences,
    WeatherContext,
    compute_feasible_windows,
)
from sophie.services.coach import get_coach_recommendation

_WEEK_START = date(2026, 8, 17)  # a Monday


def _windows(*weekday_names: str, rank: float = 0.8) -> list[CalendarWindow]:
    name_to_offset = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }
    return [
        CalendarWindow(
            date=_WEEK_START + timedelta(days=name_to_offset[name]),
            start=time(8, 45),
            end=time(9, 45),
            weekday_name=name,
            rank_score=rank,
        )
        for name in weekday_names
    ]


def _context(**overrides: object) -> CoachContext:
    defaults: dict[str, object] = dict(
        week_start=_WEEK_START,
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
        domain_statuses=[
            DomainStatus(domain="cardiovascular", status="stable", data_quality="sufficient")
        ],
        calendar_windows=_windows("Monday", "Wednesday", "Saturday"),
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


# 1. Normal 3-run week: all clear, 3 windows available -> 3 sessions, BUILD.
def test_scenario_normal_three_run_week():
    context = _context()
    plan = build_deterministic_plan(context, block_week_number=1, prior_completion_ratio=0.95)
    assert plan.verdict == Verdict.BUILD
    assert len(plan.recommended_plan) == 3


# 2. Only 2 feasible windows -> at most 2 sessions even though max is 3.
def test_scenario_only_two_feasible_windows():
    context = _context(calendar_windows=_windows("Wednesday", "Saturday"))
    plan = build_deterministic_plan(context, block_week_number=1, prior_completion_ratio=0.95)
    assert len(plan.recommended_plan) <= 2


# 3. Highly constrained week -> only 1 window -> at most 1 session, priority to long run.
def test_scenario_highly_constrained_week():
    context = _context(calendar_windows=_windows("Saturday"))
    plan = build_deterministic_plan(context, block_week_number=1, prior_completion_ratio=0.95)
    assert len(plan.recommended_plan) <= 1
    if plan.recommended_plan:
        assert plan.recommended_plan[0].session_type == SessionType.LONG


# 4. Thursday padel + Friday conflict: hard efforts the day after padel score
# lower than an equivalent day, but are never hard-rejected (soft constraint).
def test_scenario_padel_friday_soft_conflict_not_a_rejection():
    preferences = SchedulingPreferences(
        dropoff_start="08:00",
        dropoff_end="08:30",
        earliest_weekday_session="08:45",
        latest_session="20:00",
        long_run_weekday_preference=["Saturday", "Sunday", "Friday"],
        padel_weekday=3,
        preserve_rest_day=True,
    )
    feasible, rejected = compute_feasible_windows(
        _WEEK_START,
        [],
        60,
        15,
        preferences,
        "typical",
        "normal",
        None,
        session_type=SessionType.QUALITY,
    )
    friday = _WEEK_START + timedelta(days=4)
    assert not any(
        w.date == friday and w.reason_code == "busy_calendar"
        for w in rejected
        if hasattr(w, "reason_code")
    )
    friday_windows = [w for w in feasible if w.date == friday]
    other_windows = [
        w for w in feasible if w.date != friday and w.weekday_name not in ("Saturday", "Sunday")
    ]
    if friday_windows and other_windows:
        assert min(w.rank_score for w in friday_windows) <= max(w.rank_score for w in other_windows)


# 5. Saturday long run available -> Saturday chosen over other days.
def test_scenario_saturday_long_run_available():
    context = _context(calendar_windows=_windows("Monday", "Saturday", "Sunday"))
    plan = build_deterministic_plan(context, block_week_number=1, prior_completion_ratio=0.95)
    long_sessions = [s for s in plan.recommended_plan if s.session_type == SessionType.LONG]
    assert long_sessions and long_sessions[0].date == _WEEK_START + timedelta(days=5)


# 6. Sunday backup: Saturday unavailable -> Sunday used for the long run.
def test_scenario_sunday_backup_for_long_run():
    context = _context(calendar_windows=_windows("Monday", "Sunday"))
    plan = build_deterministic_plan(context, block_week_number=1, prior_completion_ratio=0.95)
    long_sessions = [s for s in plan.recommended_plan if s.session_type == SessionType.LONG]
    assert long_sessions and long_sessions[0].date == _WEEK_START + timedelta(days=6)


# 7. Poor prior completion -> REPEAT, not BUILD.
def test_scenario_poor_prior_completion():
    context = _context()
    plan = build_deterministic_plan(context, block_week_number=1, prior_completion_ratio=0.3)
    assert plan.verdict == Verdict.REPEAT


# 8. Pain signal -> REDUCE (moderate) or MINIMUM_VIABLE (severe), fewer sessions.
def test_scenario_pain_signal():
    moderate = _context(pain_0_10=5)
    plan = build_deterministic_plan(moderate, block_week_number=1, prior_completion_ratio=0.95)
    assert plan.verdict == Verdict.REDUCE

    severe = _context(pain_0_10=8)
    plan2 = build_deterministic_plan(severe, block_week_number=1, prior_completion_ratio=0.95)
    assert plan2.verdict == Verdict.MINIMUM_VIABLE
    assert len(plan2.recommended_plan) <= 1


# 9. Elevated training load -> do not progress (REPEAT or REDUCE).
def test_scenario_elevated_training_load():
    context = _context(training_load_status="elevated")
    plan = build_deterministic_plan(context, block_week_number=1, prior_completion_ratio=0.95)
    assert plan.verdict in (Verdict.REPEAT, Verdict.REDUCE)


# 10. Recovery concern -> REDUCE and no quality session in the final
# (post-validation) plan — the pain/recovery quality gate is enforced by
# coach_validation for every recommendation source, deterministic included,
# so this goes through the full get_coach_recommendation pipeline.
def test_scenario_recovery_concern():
    context = _context(recovery_status="concern")
    result = get_coach_recommendation(context, llm_provider=None, prior_completion_ratio=0.95)
    assert result.recommendation.verdict == Verdict.REDUCE
    assert all(
        s.session_type != SessionType.QUALITY for s in result.recommendation.recommended_plan
    )


# 11. Missing health information -> system still produces a valid plan, no crash.
def test_scenario_missing_health_information():
    context = _context(training_load_status="typical", recovery_status="normal", domain_statuses=[])
    plan = build_deterministic_plan(context, block_week_number=1, prior_completion_ratio=None)
    assert plan.verdict in (Verdict.BUILD, Verdict.REPEAT, Verdict.REDUCE, Verdict.MINIMUM_VIABLE)


# 12. Week 3 progression inappropriate (recovery/load not supportive) ->
# held steady, not progressed.
def test_scenario_week3_progression_inappropriate():
    context = _context(recovery_status="watch")
    plan = build_deterministic_plan(context, block_week_number=3, prior_completion_ratio=0.95)
    assert plan.verdict == Verdict.REPEAT
    week = block_week_for(3)
    long_sessions = [s for s in plan.recommended_plan if s.session_type == SessionType.LONG]
    if long_sessions and long_sessions[0].distance_km is not None:
        assert long_sessions[0].distance_km <= week.long_km_conditional_high


# 13. Week 3 progression appropriate (all clear) -> long run may use the conditional upper range.
def test_scenario_week3_progression_appropriate():
    context = _context()
    plan = build_deterministic_plan(context, block_week_number=3, prior_completion_ratio=0.95)
    assert plan.verdict == Verdict.BUILD
    week = block_week_for(3)
    long_sessions = [s for s in plan.recommended_plan if s.session_type == SessionType.LONG]
    if long_sessions and long_sessions[0].distance_km is not None:
        assert week.long_km_low <= long_sessions[0].distance_km <= week.long_km_conditional_high


# 14. Week 4 down week -> long run distance within the lower week-4 band.
def test_scenario_week4_down_week():
    context = _context()
    plan = build_deterministic_plan(context, block_week_number=4, prior_completion_ratio=0.95)
    week = block_week_for(4)
    assert week.long_km_high < block_week_for(2).long_km_high  # genuinely a down week
    long_sessions = [s for s in plan.recommended_plan if s.session_type == SessionType.LONG]
    if long_sessions and long_sessions[0].distance_km is not None:
        assert long_sessions[0].distance_km <= week.long_km_high * 1.1


# 15. Bad weather Saturday / better weather Sunday -> Sunday ranks at least as well.
def test_scenario_bad_weather_saturday_better_sunday():
    preferences = SchedulingPreferences(
        dropoff_start="08:00",
        dropoff_end="08:30",
        earliest_weekday_session="08:45",
        latest_session="20:00",
        long_run_weekday_preference=["Saturday", "Sunday", "Friday"],
        padel_weekday=3,
        preserve_rest_day=True,
    )
    saturday = _WEEK_START + timedelta(days=5)
    sunday = _WEEK_START + timedelta(days=6)
    weather = {
        saturday: WeatherContext(temp_c=32.0, precip_mm=20.0, wind_kph=40.0),
        sunday: WeatherContext(temp_c=16.0, precip_mm=0.0, wind_kph=8.0),
    }
    feasible, _ = compute_feasible_windows(
        _WEEK_START,
        [],
        60,
        15,
        preferences,
        "typical",
        "normal",
        weather,
        session_type=SessionType.LONG,
    )
    sat_best = max((w.rank_score for w in feasible if w.date == saturday), default=0.0)
    sun_best = max((w.rank_score for w in feasible if w.date == sunday), default=0.0)
    assert sun_best >= sat_best


# 16. LLM proposes four runs -> validator caps to max_runs_per_week.
def test_scenario_llm_proposes_four_runs():
    context = _context(
        max_runs_per_week=3, calendar_windows=_windows("Monday", "Wednesday", "Saturday", "Sunday")
    )
    week = block_week_for(1)
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
        reasons=["llm"],
        recommended_plan=sessions,
        conservative_alternative=ConservativeAlternative(summary="lighter", sessions=[]),
    )
    result = validate_and_repair(rec, context, week)
    assert len(result.recommendation.recommended_plan) <= 3


# 17. Impossible calendar slot -> dropped, not silently passed through.
def test_scenario_impossible_calendar_slot():
    context = _context()
    week = block_week_for(1)
    bogus = RecommendedSession(
        date=_WEEK_START + timedelta(days=10),
        start_time=time(9, 0),
        session_type=SessionType.EASY,
        purpose="Easy run",
        distance_km=8,
    )
    rec = CoachRecommendation(
        verdict=Verdict.BUILD,
        reasons=["llm"],
        recommended_plan=[bogus],
        conservative_alternative=ConservativeAlternative(summary="lighter", sessions=[]),
    )
    result = validate_and_repair(rec, context, week)
    assert bogus not in result.recommendation.recommended_plan


# 18. Aggressive long run -> clamped into the block's range.
def test_scenario_aggressive_long_run_clamped():
    context = _context()
    week = block_week_for(1)
    aggressive = RecommendedSession(
        date=context.calendar_windows[0].date,
        start_time=time(9, 0),
        session_type=SessionType.LONG,
        purpose="Long run",
        distance_km=30.0,
    )
    rec = CoachRecommendation(
        verdict=Verdict.BUILD,
        reasons=["llm"],
        recommended_plan=[aggressive],
        conservative_alternative=ConservativeAlternative(summary="lighter", sessions=[]),
    )
    result = validate_and_repair(rec, context, week)
    clamped = result.recommendation.recommended_plan[0]
    upper_bound = week.long_km_conditional_high or week.long_km_high
    assert clamped.distance_km <= upper_bound


# 19. LLM unavailable -> deterministic fallback still produces a valid plan.
def test_scenario_llm_unavailable():
    class _UnavailableProvider:
        def generate_recommendation(self, context, feedback=None):
            return None

    context = _context()
    result = get_coach_recommendation(
        context, llm_provider=_UnavailableProvider(), prior_completion_ratio=0.95
    )
    assert result.llm_used is False
    assert result.recommendation.verdict is not None
