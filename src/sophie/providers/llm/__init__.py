"""LLM provider abstractions. See CLAUDE.md — raw health/calendar data must
never reach this package; callers only pass already-sanitized
sophie.domain.coach_types.CoachContext / sophie.domain.chat_types.ChatContext
objects. Provider selection from settings lives in the services layer (see
sophie.services.chat_service), not here — these classes take plain api_key/
model strings, the same construction pattern as OpenAICoachProvider."""

from sophie.providers.llm.anthropic_chat_provider import AnthropicChatProvider
from sophie.providers.llm.base import CoachLLMProvider
from sophie.providers.llm.chat_base import ChatLLMProvider
from sophie.providers.llm.openai_chat_provider import OpenAIChatProvider
from sophie.providers.llm.openai_provider import OpenAICoachProvider
from sophie.providers.llm.xai_chat_provider import XAIChatProvider

CHAT_PROVIDER_LABELS = {
    "anthropic": "Claude (Anthropic)",
    "openai": "ChatGPT (OpenAI)",
    "xai": "Grok (xAI)",
}

__all__ = [
    "CoachLLMProvider",
    "OpenAICoachProvider",
    "ChatLLMProvider",
    "AnthropicChatProvider",
    "OpenAIChatProvider",
    "XAIChatProvider",
    "CHAT_PROVIDER_LABELS",
]
