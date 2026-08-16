"""Orchestrates one Chat turn: build sanitized context, call the selected
provider, apply the same forbidden-language safety filter the clinical
domain uses (see sophie.domain.clinical_safety — "deterministic constraints
outrank LLM recommendations", CLAUDE.md), and persist the transcript.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from sophie.config.settings import Settings
from sophie.domain.chat_types import ChatTurn
from sophie.domain.clinical_safety import clinician_discussion_note, contains_forbidden_language
from sophie.providers.llm import (
    AnthropicChatProvider,
    ChatLLMProvider,
    OpenAIChatProvider,
    XAIChatProvider,
)
from sophie.repositories import chat_repo
from sophie.services.chat_context import build_chat_context

_HISTORY_TURNS = 20

_UNSAFE_FALLBACK = (
    "I can't answer that directly — I'm not able to diagnose, rule out, or make claims about "
    "medical conditions. I can surface trends and deviations from your own baseline instead. "
    + clinician_discussion_note()
)


@dataclass
class ChatTurnResult:
    state: str  # answered/unsafe_filtered/not_configured/failed
    text: str


def get_chat_llm_provider(settings: Settings, provider: str) -> ChatLLMProvider | None:
    """Returns None if `provider` is unknown or has no API key configured —
    callers must treat that as "chat unavailable for this provider", never
    crash. Mirrors how sophie.ui.streamlit.pages.sunday_review_page
    constructs OpenAICoachProvider from plain settings values."""
    if provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicChatProvider(settings.anthropic_api_key, settings.anthropic_model)
    if provider == "openai" and settings.openai_api_key:
        return OpenAIChatProvider(settings.openai_api_key, settings.openai_model)
    if provider == "xai" and settings.xai_api_key:
        return XAIChatProvider(settings.xai_api_key, settings.xai_model)
    return None


def ask(
    session: Session, profile_id: str, settings: Settings, provider_name: str, question: str
) -> ChatTurnResult:
    history_rows = chat_repo.list_messages(session, profile_id, limit=_HISTORY_TURNS)
    history = [ChatTurn(role=row.role, content=row.content) for row in history_rows]

    chat_repo.add_message(session, profile_id, role="user", content=question)

    provider = get_chat_llm_provider(settings, provider_name)
    if provider is None:
        result = ChatTurnResult(
            state="not_configured",
            text=(
                f"The '{provider_name}' provider isn't configured yet — add its API key in "
                "your .env file, then restart Sophie."
            ),
        )
    else:
        context = build_chat_context(session, profile_id)
        raw_answer = provider.answer_question(context, question, history)
        if raw_answer is None:
            result = ChatTurnResult(
                state="failed",
                text=(
                    f"I couldn't reach {provider_name} right now — check the API key and try "
                    "again, or switch providers."
                ),
            )
        elif contains_forbidden_language(raw_answer):
            result = ChatTurnResult(state="unsafe_filtered", text=_UNSAFE_FALLBACK)
        else:
            result = ChatTurnResult(state="answered", text=raw_answer)

    chat_repo.add_message(
        session, profile_id, role="assistant", content=result.text, provider=provider_name
    )
    return result
