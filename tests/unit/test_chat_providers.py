from __future__ import annotations

from sophie.domain.chat_types import ChatContext
from sophie.providers.llm.anthropic_chat_provider import AnthropicChatProvider
from sophie.providers.llm.openai_chat_provider import OpenAIChatProvider
from sophie.providers.llm.xai_chat_provider import XAIChatProvider


def _context() -> ChatContext:
    return ChatContext(
        domain_statuses=[],
        metric_averages=[],
        race_name=None,
        race_date=None,
        weight_goal_kg=None,
        current_weight_kg=None,
        max_runs_per_week=3,
        sophie_memory=None,
    )


# --------------------------------------------------------------------------
# OpenAI / xAI share the Chat Completions shape
# --------------------------------------------------------------------------


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content, raise_error=None):
        self._content = content
        self._raise_error = raise_error

    def create(self, **kwargs):
        if self._raise_error:
            raise self._raise_error
        return _FakeResponse(self._content)


class _FakeChat:
    def __init__(self, content, raise_error=None):
        self.completions = _FakeCompletions(content, raise_error)


class _FakeOpenAIClient:
    def __init__(self, content=None, raise_error=None):
        self.chat = _FakeChat(content, raise_error)


def test_openai_chat_provider_returns_answer_text():
    provider = OpenAIChatProvider(
        api_key="unused",
        model="gpt-4o-mini",
        client=_FakeOpenAIClient("You slept 7.2h on average."),
    )
    result = provider.answer_question(_context(), "How's my sleep?", [])
    assert result == "You slept 7.2h on average."


def test_openai_chat_provider_returns_none_on_error():
    provider = OpenAIChatProvider(
        api_key="unused",
        model="gpt-4o-mini",
        client=_FakeOpenAIClient(raise_error=RuntimeError("boom")),
    )
    assert provider.answer_question(_context(), "hi", []) is None


def test_openai_chat_provider_returns_none_on_empty_content():
    provider = OpenAIChatProvider(
        api_key="unused", model="gpt-4o-mini", client=_FakeOpenAIClient("")
    )
    assert provider.answer_question(_context(), "hi", []) is None


def test_xai_chat_provider_returns_answer_text():
    provider = XAIChatProvider(
        api_key="unused", model="grok-4", client=_FakeOpenAIClient("Your training load is typical.")
    )
    result = provider.answer_question(_context(), "How's my training?", [])
    assert result == "Your training load is typical."


def test_xai_chat_provider_returns_none_on_error():
    provider = XAIChatProvider(
        api_key="unused", model="grok-4", client=_FakeOpenAIClient(raise_error=RuntimeError("boom"))
    )
    assert provider.answer_question(_context(), "hi", []) is None


# --------------------------------------------------------------------------
# Anthropic has a different response shape (content blocks, not choices)
# --------------------------------------------------------------------------


class _FakeTextBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _FakeAnthropicResponse:
    def __init__(self, text):
        self.content = [_FakeTextBlock(text)]


class _FakeMessages:
    def __init__(self, text, raise_error=None):
        self._text = text
        self._raise_error = raise_error

    def create(self, **kwargs):
        if self._raise_error:
            raise self._raise_error
        return _FakeAnthropicResponse(self._text)


class _FakeAnthropicClient:
    def __init__(self, text=None, raise_error=None):
        self.messages = _FakeMessages(text, raise_error)


def test_anthropic_chat_provider_returns_answer_text():
    provider = AnthropicChatProvider(
        api_key="unused",
        model="claude-sonnet-4-5",
        client=_FakeAnthropicClient("Your resting HR has been stable."),
    )
    result = provider.answer_question(_context(), "How's my heart rate?", [])
    assert result == "Your resting HR has been stable."


def test_anthropic_chat_provider_returns_none_on_error():
    provider = AnthropicChatProvider(
        api_key="unused",
        model="claude-sonnet-4-5",
        client=_FakeAnthropicClient(raise_error=RuntimeError("boom")),
    )
    assert provider.answer_question(_context(), "hi", []) is None


def test_anthropic_chat_provider_returns_none_on_empty_content():
    provider = AnthropicChatProvider(
        api_key="unused", model="claude-sonnet-4-5", client=_FakeAnthropicClient("")
    )
    assert provider.answer_question(_context(), "hi", []) is None
