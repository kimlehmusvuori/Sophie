"""LLM coach provider interface. Implementations must accept only an
already-sanitized CoachContext (see docs/PRIVACY.md) and return either a
validated CoachRecommendation or None on any failure — never raise up to the
caller. The product must remain fully usable with no provider configured."""

from __future__ import annotations

from typing import Protocol

from sophie.domain.coach_types import CoachContext, CoachRecommendation


class CoachLLMProvider(Protocol):
    def generate_recommendation(
        self, context: CoachContext, feedback: list[str] | None = None
    ) -> CoachRecommendation | None:
        """`feedback` carries deterministic-validator notes from a prior
        rejected attempt, for the single allowed regeneration attempt."""
        ...
