import pytest

from src.llm.base import LLMProvider, LLMResponse
from src.llm.fallback import AllProvidersFailedError, FallbackProvider


class FakeProvider(LLMProvider):
    """Plays back scripted outcomes: each item is an LLMResponse or an Exception to raise."""

    def __init__(self, name, outcomes):
        self.name = name
        self.model = f"{name}-model"
        self.outcomes = list(outcomes)
        self.calls = []  # max_tokens of every call

    def generate(self, prompt, system_prompt="x", temperature=0.3, max_tokens=1500):
        self.calls.append(max_tokens)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def good(provider, text="ok"):
    return LLMResponse(text=text, finish_reason="stop", provider=provider, model="m")


def truncated(provider):
    return LLMResponse(text="cut off mid-sen", finish_reason="length", provider=provider, model="m")


def empty(provider):
    return LLMResponse(text="", finish_reason="stop", provider=provider, model="m")


def test_first_provider_good_second_never_called():
    a = FakeProvider("groq", [good("groq")])
    b = FakeProvider("gemini", [good("gemini")])
    r = FallbackProvider([a, b]).generate("hi")
    assert r.provider == "groq"
    assert b.calls == []


def test_first_transient_error_retries_then_second_answers(monkeypatch):
    sleeps = []
    monkeypatch.setattr("src.llm.fallback.time.sleep", sleeps.append)
    a = FakeProvider("groq", [RuntimeError("429 rate limit")] * 3)
    b = FakeProvider("gemini", [good("gemini")])
    fb = FallbackProvider([a, b])
    r = fb.generate("hi")
    assert r.provider == "gemini"
    assert "429" in fb.last_failures[0][1]
    assert len(a.calls) == 3
    assert sleeps == [0.5, 1.0]


def test_transient_error_can_recover_on_same_provider(monkeypatch):
    sleeps = []
    monkeypatch.setattr("src.llm.fallback.time.sleep", sleeps.append)
    a = FakeProvider("groq", [RuntimeError("temporary provider failure"), good("groq")])
    b = FakeProvider("gemini", [good("gemini")])

    response = FallbackProvider([a, b]).generate("hi")

    assert response.provider == "groq"
    assert a.calls == [1500, 1500]
    assert b.calls == []
    assert sleeps == [0.5]


def test_retry_backoff_is_exponential_and_capped(monkeypatch):
    sleeps = []
    monkeypatch.setattr("src.llm.fallback.time.sleep", sleeps.append)
    provider = FakeProvider("groq", [RuntimeError("503 unavailable")] * 5)

    with pytest.raises(AllProvidersFailedError):
        FallbackProvider(
            [provider],
            max_retries=4,
            retry_backoff_seconds=0.5,
            max_retry_backoff_seconds=1.2,
        ).generate("hi")

    assert len(provider.calls) == 5
    assert sleeps == [0.5, 1.0, 1.2, 1.2]


def test_permanent_configuration_error_is_not_retried(monkeypatch):
    sleeps = []
    monkeypatch.setattr("src.llm.fallback.time.sleep", sleeps.append)
    a = FakeProvider("groq", [ValueError("invalid model configuration")])
    b = FakeProvider("gemini", [good("gemini")])

    response = FallbackProvider([a, b]).generate("hi")

    assert response.provider == "gemini"
    assert a.calls == [1500]
    assert sleeps == []


def test_first_returns_empty_second_answers():
    a = FakeProvider("groq", [empty("groq")])
    b = FakeProvider("gemini", [good("gemini")])
    r = FallbackProvider([a, b]).generate("hi")
    assert r.provider == "gemini"


def test_truncated_then_retry_with_bigger_cap_succeeds():
    a = FakeProvider("groq", [truncated("groq"), good("groq")])
    b = FakeProvider("gemini", [good("gemini")])
    r = FallbackProvider([a, b]).generate("hi", max_tokens=500)
    assert r.provider == "groq"
    assert a.calls == [500, 1000]
    assert b.calls == []


def test_truncated_retry_still_truncated_falls_to_second():
    a = FakeProvider("groq", [truncated("groq"), truncated("groq")])
    b = FakeProvider("gemini", [good("gemini")])
    r = FallbackProvider([a, b]).generate("hi", max_tokens=500)
    assert r.provider == "gemini"
    assert a.calls == [500, 1000]


def test_retry_can_be_disabled():
    a = FakeProvider("groq", [truncated("groq")])
    b = FakeProvider("gemini", [good("gemini")])
    r = FallbackProvider([a, b], retry_on_truncation=False).generate("hi", max_tokens=500)
    assert r.provider == "gemini"
    assert a.calls == [500]


def test_all_fail_raises_clear_error():
    a = FakeProvider("groq", [RuntimeError("boom")])
    b = FakeProvider("gemini", [empty("gemini")])
    with pytest.raises(AllProvidersFailedError) as info:
        FallbackProvider([a, b]).generate("hi")
    message = str(info.value)
    assert "groq" in message and "gemini" in message and "boom" in message


def test_no_providers_is_an_error():
    with pytest.raises(ValueError):
        FallbackProvider([])