"""LLM coach provider abstraction + OpenAI implementation. See CLAUDE.md —
raw health/calendar data must never reach this package; callers only pass
already-sanitized sophie.domain.coach_types.CoachContext objects."""

from sophie.providers.llm.base import CoachLLMProvider
from sophie.providers.llm.openai_provider import OpenAICoachProvider

__all__ = ["CoachLLMProvider", "OpenAICoachProvider"]
