"""Chat LLM provider interface. Implementations must accept only an
already-sanitized ChatContext (see docs/PRIVACY.md) plus prior turns, and
return plain answer text or None on any failure — never raise. The product
must remain fully usable with no provider configured."""

from __future__ import annotations

from typing import Protocol

from sophie.domain.chat_types import ChatContext, ChatTurn


class ChatLLMProvider(Protocol):
    def answer_question(
        self, context: ChatContext, question: str, history: list[ChatTurn]
    ) -> str | None:
        """`history` is prior turns in this conversation, oldest first."""
        ...
