"""OpenAI (ChatGPT)-backed chat provider. Never raises — any API error,
timeout, or malformed response is swallowed and reported as None, same
degrade-gracefully contract as the coach providers."""

from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI

from sophie.domain.chat_types import ChatContext, ChatTurn
from sophie.prompts.chat_prompt import SYSTEM_PROMPT, build_user_message

logger = logging.getLogger(__name__)

_TIMEOUT_S = 30.0


class OpenAIChatProvider:
    def __init__(self, api_key: str, model: str, client: Any | None = None) -> None:
        self._model = model
        self._client = client or OpenAI(api_key=api_key, timeout=_TIMEOUT_S)

    def answer_question(
        self, context: ChatContext, question: str, history: list[ChatTurn]
    ) -> str | None:
        try:
            messages: list[Any] = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.extend({"role": turn.role, "content": turn.content} for turn in history)
            messages.append({"role": "user", "content": build_user_message(context, question)})
            response = self._client.chat.completions.create(model=self._model, messages=messages)
            content = response.choices[0].message.content
            return content.strip() if content else None
        except Exception as exc:  # noqa: BLE001 - any provider failure must degrade, never crash
            logger.warning("OpenAI chat call failed: %s", exc)
            return None
