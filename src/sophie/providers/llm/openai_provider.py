"""OpenAI-backed coach LLM provider. Never raises — any API error, timeout,
or malformed response is swallowed and reported as None so the caller
(sophie.services.coach) falls back to the deterministic planner. See
CLAUDE.md: "never make the product unusable because the LLM API is
unavailable"."""

from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from sophie.domain.coach_types import CoachContext, CoachRecommendation
from sophie.prompts.coach_prompt import SYSTEM_PROMPT, build_user_message

logger = logging.getLogger(__name__)

_TIMEOUT_S = 20.0


class OpenAICoachProvider:
    def __init__(self, api_key: str, model: str, client: Any | None = None) -> None:
        self._model = model
        self._client = client or OpenAI(api_key=api_key, timeout=_TIMEOUT_S)

    def generate_recommendation(
        self, context: CoachContext, feedback: list[str] | None = None
    ) -> CoachRecommendation | None:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_message(context, feedback)},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not content:
                return None
            return CoachRecommendation.model_validate_json(content)
        except ValidationError as exc:
            logger.warning("LLM coach response failed schema validation: %s", exc)
            return None
        except Exception as exc:  # noqa: BLE001 - any provider failure must degrade, never crash
            logger.warning("LLM coach call failed: %s", exc)
            return None
