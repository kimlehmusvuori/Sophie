from __future__ import annotations

from datetime import date, time

from sophie.domain.coach_types import (
    CalendarWindow,
    CoachContext,
    CoachRecommendation,
    ConservativeAlternative,
    RecommendedSession,
    Verdict,
)
from sophie.domain.training_block import SessionType
from sophie.services.coach import get_coach_recommendation


def _context() -> CoachContext:
    return CoachContext(
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
                date=date(2026, 8, 22),
                start=time(9, 0),
                end=time(10, 0),
                weekday_name="Saturday",
                rank_score=0.9,
            )
        ],
        rejected_windows=[],
        pain_0_10=None,
        pain_location=None,
        stress_1_5=2,
        fasting_quality="good",
        weekly_note=None,
        sophie_memory=None,
    )


class _AlwaysUnavailableProvider:
    def generate_recommendation(self, context, feedback=None):
        return None


class _ValidFirstTryProvider:
    def generate_recommendation(self, context, feedback=None):
        return CoachRecommendation(
            verdict=Verdict.BUILD,
            reasons=["looks good"],
            recommended_plan=[
                RecommendedSession(
                    date=date(2026, 8, 22),
                    start_time=time(9, 0),
                    session_type=SessionType.EASY,
                    purpose="Easy run",
                    distance_km=8,
                )
            ],
            conservative_alternative=ConservativeAlternative(summary="lighter", sessions=[]),
        )


class _InvalidThenValidProvider:
    def __init__(self):
        self.calls = 0

    def generate_recommendation(self, context, feedback=None):
        self.calls += 1
        if self.calls == 1:
            return CoachRecommendation(
                verdict=Verdict.BUILD,
                reasons=["bad"],
                recommended_plan=[
                    RecommendedSession(
                        date=date(2026, 8, 22),
                        start_time=time(9, 0),
                        session_type=SessionType.QUALITY,
                        purpose="All-out maximal sprint intervals",
                        distance_km=None,
                    )
                ],
                conservative_alternative=ConservativeAlternative(summary="lighter", sessions=[]),
            )
        return _ValidFirstTryProvider().generate_recommendation(context)


def test_no_provider_falls_back_to_deterministic():
    result = get_coach_recommendation(_context(), llm_provider=None, prior_completion_ratio=0.9)
    assert result.llm_used is False
    assert result.recommendation.verdict in (Verdict.BUILD, Verdict.REPEAT)


def test_unavailable_provider_falls_back_to_deterministic():
    result = get_coach_recommendation(
        _context(), llm_provider=_AlwaysUnavailableProvider(), prior_completion_ratio=0.9
    )
    assert result.llm_used is False


def test_valid_llm_response_used_directly():
    result = get_coach_recommendation(
        _context(), llm_provider=_ValidFirstTryProvider(), prior_completion_ratio=0.9
    )
    assert result.llm_used is True
    assert result.recommendation.verdict == Verdict.BUILD


def test_invalid_llm_response_triggers_one_regeneration_then_succeeds():
    provider = _InvalidThenValidProvider()
    result = get_coach_recommendation(_context(), llm_provider=provider, prior_completion_ratio=0.9)
    assert provider.calls == 2
    assert result.llm_used is True


def test_persistently_invalid_llm_response_falls_back_to_deterministic():
    class _AlwaysInvalidProvider:
        def generate_recommendation(self, context, feedback=None):
            return CoachRecommendation(
                verdict=Verdict.BUILD,
                reasons=["bad"],
                recommended_plan=[
                    RecommendedSession(
                        date=date(2026, 8, 22),
                        start_time=time(9, 0),
                        session_type=SessionType.QUALITY,
                        purpose="Maximal sprint time trial",
                        distance_km=None,
                    )
                ],
                conservative_alternative=ConservativeAlternative(summary="lighter", sessions=[]),
            )

    result = get_coach_recommendation(
        _context(), llm_provider=_AlwaysInvalidProvider(), prior_completion_ratio=0.9
    )
    assert result.llm_used is False
