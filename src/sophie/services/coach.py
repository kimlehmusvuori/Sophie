"""Coach orchestration: deterministic rules + optional LLM synthesis, with
the deterministic validator always having final say. See CLAUDE.md
("deterministic constraints outrank LLM recommendations") and
docs/PRODUCT_SPEC.md §46-50.
"""

from __future__ import annotations

from dataclasses import dataclass

from sophie.domain.coach_types import CoachContext, CoachRecommendation
from sophie.domain.coach_validation import validate_and_repair
from sophie.domain.planner import build_deterministic_plan
from sophie.domain.training_block import BlockWeek, block_week_for
from sophie.providers.llm.base import CoachLLMProvider


@dataclass
class CoachResult:
    recommendation: CoachRecommendation
    llm_used: bool
    validation_notes: list[str]


def get_coach_recommendation(
    context: CoachContext,
    llm_provider: CoachLLMProvider | None = None,
    block: list[BlockWeek] | None = None,
    prior_completion_ratio: float | None = None,
) -> CoachResult:
    block_week = block_week_for(context.current_block_week_number, block)

    if llm_provider is not None:
        candidate = llm_provider.generate_recommendation(context)
        if candidate is not None:
            result = validate_and_repair(candidate, context, block_week)
            if result.safe:
                return CoachResult(
                    result.recommendation, llm_used=True, validation_notes=result.notes
                )

            retry = llm_provider.generate_recommendation(context, feedback=result.notes)
            if retry is not None:
                retry_result = validate_and_repair(retry, context, block_week)
                if retry_result.safe:
                    return CoachResult(
                        retry_result.recommendation,
                        llm_used=True,
                        validation_notes=retry_result.notes,
                    )

    deterministic = build_deterministic_plan(
        context,
        block_week_number=context.current_block_week_number,
        block=block,
        prior_completion_ratio=prior_completion_ratio,
    )
    result = validate_and_repair(deterministic, context, block_week)
    return CoachResult(result.recommendation, llm_used=False, validation_notes=result.notes)
