"""Anthropic (Claude)-backed chat provider. Never raises. Unlike the OpenAI
Chat Completions shape, Anthropic's Messages API takes the system prompt as
a separate top-level parameter rather than a message with role="system"."""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from sophie.domain.chat_types import ChatContext, ChatTurn
from sophie.prompts.chat_prompt import SYSTEM_PROMPT, build_user_message

logger = logging.getLogger(__name__)

_TIMEOUT_S = 30.0
_MAX_TOKENS = 1024


class AnthropicChatProvider:
    def __init__(self, api_key: str, model: str, client: Any | None = None) -> None:
        self._model = model
        self._client = client or anthropic.Anthropic(api_key=api_key, timeout=_TIMEOUT_S)

    def answer_question(
        self, context: ChatContext, question: str, history: list[ChatTurn]
    ) -> str | None:
        try:
            messages: list[Any] = [{"role": turn.role, "content": turn.content} for turn in history]
            messages.append({"role": "user", "content": build_user_message(context, question)})
            response = self._client.messages.create(
                model=self._model,
                max_tokens=_MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            content = "".join(
                getattr(block, "text", "")
                for block in response.content
                if getattr(block, "type", None) == "text"
            )
            return content.strip() or None
        except Exception as exc:  # noqa: BLE001 - any provider failure must degrade, never crash
            logger.warning("Anthropic (Claude) chat call failed: %s", exc)
            return None
