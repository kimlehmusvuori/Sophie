from __future__ import annotations

import json
from datetime import date, time

from sophie.domain.coach_types import CalendarWindow, CoachContext
from sophie.providers.llm.openai_provider import OpenAICoachProvider

VALID_JSON = json.dumps(
    {
        "verdict": "build",
        "reasons": ["all clear"],
        "recommended_plan": [
            {
                "date": "2026-08-22",
                "start_time": "09:00",
                "session_type": "easy",
                "purpose": "Easy run",
                "distance_km": 8,
                "estimated_duration_min": 50,
                "note": None,
            }
        ],
        "conservative_alternative": {"summary": "lighter", "sessions": []},
        "coach_note": None,
    }
)


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content, raise_error=None):
        self._content = content
        self._raise_error = raise_error

    def create(self, **kwargs):
        if self._raise_error:
            raise self._raise_error
        return _FakeResponse(self._content)


class _FakeChat:
    def __init__(self, content, raise_error=None):
        self.completions = _FakeCompletions(content, raise_error)


class _FakeClient:
    def __init__(self, content=None, raise_error=None):
        self.chat = _FakeChat(content, raise_error)


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


def test_valid_response_parses_into_recommendation():
    provider = OpenAICoachProvider(
        api_key="unused", model="gpt-4o-mini", client=_FakeClient(VALID_JSON)
    )
    result = provider.generate_recommendation(_context())
    assert result is not None
    assert result.verdict == "build"
    assert len(result.recommended_plan) == 1


def test_malformed_json_returns_none():
    provider = OpenAICoachProvider(
        api_key="unused", model="gpt-4o-mini", client=_FakeClient("not json")
    )
    result = provider.generate_recommendation(_context())
    assert result is None


def test_api_error_returns_none_not_raises():
    provider = OpenAICoachProvider(
        api_key="unused", model="gpt-4o-mini", client=_FakeClient(raise_error=RuntimeError("boom"))
    )
    result = provider.generate_recommendation(_context())
    assert result is None


def test_empty_content_returns_none():
    provider = OpenAICoachProvider(api_key="unused", model="gpt-4o-mini", client=_FakeClient(""))
    result = provider.generate_recommendation(_context())
    assert result is None
