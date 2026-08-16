from __future__ import annotations

from sophie.config.settings import Settings
from sophie.providers.llm import AnthropicChatProvider, OpenAIChatProvider, XAIChatProvider
from sophie.repositories import chat_repo, profile_repo
from sophie.services import chat_service


class _FakeProvider:
    def __init__(self, answer: str | None):
        self._answer = answer
        self.seen_history = None
        self.seen_question = None

    def answer_question(self, context, question, history):
        self.seen_history = history
        self.seen_question = question
        return self._answer


# --------------------------------------------------------------------------
# get_chat_llm_provider factory
# --------------------------------------------------------------------------


def test_get_chat_llm_provider_returns_none_when_unconfigured():
    settings = Settings(anthropic_api_key=None, openai_api_key=None, xai_api_key=None)
    assert chat_service.get_chat_llm_provider(settings, "anthropic") is None
    assert chat_service.get_chat_llm_provider(settings, "openai") is None
    assert chat_service.get_chat_llm_provider(settings, "xai") is None


def test_get_chat_llm_provider_returns_none_for_unknown_provider():
    settings = Settings(anthropic_api_key="key")
    assert chat_service.get_chat_llm_provider(settings, "not-a-real-provider") is None


def test_get_chat_llm_provider_returns_correct_type_when_configured():
    settings = Settings(anthropic_api_key="a-key", openai_api_key="o-key", xai_api_key="x-key")
    assert isinstance(
        chat_service.get_chat_llm_provider(settings, "anthropic"), AnthropicChatProvider
    )
    assert isinstance(chat_service.get_chat_llm_provider(settings, "openai"), OpenAIChatProvider)
    assert isinstance(chat_service.get_chat_llm_provider(settings, "xai"), XAIChatProvider)


# --------------------------------------------------------------------------
# ask() orchestration
# --------------------------------------------------------------------------


def test_ask_returns_not_configured_when_provider_missing_key(db_session):
    profile = profile_repo.get_or_create_profile(db_session)
    settings = Settings(anthropic_api_key=None)

    result = chat_service.ask(db_session, profile.id, settings, "anthropic", "How's my sleep?")

    assert result.state == "not_configured"
    messages = chat_repo.list_messages(db_session, profile.id)
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[0].content == "How's my sleep?"


def test_ask_filters_unsafe_answer(db_session, monkeypatch):
    profile = profile_repo.get_or_create_profile(db_session)
    settings = Settings(anthropic_api_key="a-key")
    fake = _FakeProvider("You have rheumatoid arthritis based on these trends.")
    monkeypatch.setattr(chat_service, "get_chat_llm_provider", lambda *_args: fake)

    result = chat_service.ask(
        db_session, profile.id, settings, "anthropic", "What's wrong with me?"
    )

    assert result.state == "unsafe_filtered"
    assert "diagnose" in result.text.lower() or "rule out" in result.text.lower()
    assert "rheumatoid" not in result.text.lower()


def test_ask_returns_answered_for_safe_response(db_session, monkeypatch):
    profile = profile_repo.get_or_create_profile(db_session)
    settings = Settings(anthropic_api_key="a-key")
    fake = _FakeProvider("Your average sleep this month is 7.1 hours, slightly above your usual.")
    monkeypatch.setattr(chat_service, "get_chat_llm_provider", lambda *_args: fake)

    result = chat_service.ask(db_session, profile.id, settings, "anthropic", "How's my sleep?")

    assert result.state == "answered"
    assert result.text == "Your average sleep this month is 7.1 hours, slightly above your usual."


def test_ask_passes_prior_turns_as_history(db_session, monkeypatch):
    profile = profile_repo.get_or_create_profile(db_session)
    settings = Settings(anthropic_api_key="a-key")

    first = _FakeProvider("First answer.")
    monkeypatch.setattr(chat_service, "get_chat_llm_provider", lambda *_args: first)
    chat_service.ask(db_session, profile.id, settings, "anthropic", "First question?")
    assert first.seen_history == []

    second = _FakeProvider("Second answer.")
    monkeypatch.setattr(chat_service, "get_chat_llm_provider", lambda *_args: second)
    chat_service.ask(db_session, profile.id, settings, "anthropic", "Second question?")

    assert [t.content for t in second.seen_history] == ["First question?", "First answer."]


def test_ask_returns_failed_state_when_provider_returns_none(db_session, monkeypatch):
    profile = profile_repo.get_or_create_profile(db_session)
    settings = Settings(anthropic_api_key="a-key")
    fake = _FakeProvider(None)
    monkeypatch.setattr(chat_service, "get_chat_llm_provider", lambda *_args: fake)

    result = chat_service.ask(db_session, profile.id, settings, "anthropic", "hi")

    assert result.state == "failed"
