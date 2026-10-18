import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.llm import GeminiProvider, GroqProvider, LLMResponse
from src.llm.base import normalize_finish_reason

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)


# ---- unit tests: no network ----
def test_normalize_finish_reason():
    assert normalize_finish_reason("stop") == "stop"
    assert normalize_finish_reason("length") == "length"
    assert normalize_finish_reason("FinishReason.MAX_TOKENS") == "length"
    assert normalize_finish_reason("FinishReason.STOP") == "stop"
    assert normalize_finish_reason(None) == "other"


def test_empty_or_truncated_is_not_usable():
    assert not LLMResponse("", "length", "x", "y").usable
    assert not LLMResponse("cut off mid-sen", "length", "x", "y").usable
    assert LLMResponse("ok", "stop", "x", "y").usable


def test_missing_keys_raise(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        GroqProvider(model="m")
    with pytest.raises(ValueError):
        GeminiProvider(model="m")


# ---- live tests: real API calls, run with: python -m pytest -m live ----
PROVIDERS = [
    ("groq", GroqProvider, "GROQ_API_KEY", "GROQ_MODEL"),
    ("gemini", GeminiProvider, "GEMINI_API_KEY", "GEMINI_MODEL"),
]


@pytest.mark.live
@pytest.mark.parametrize("name,cls,key_var,model_var", PROVIDERS)
def test_live_provider(name, cls, key_var, model_var):
    if not os.getenv(key_var) or not os.getenv(model_var):
        pytest.skip(f"{key_var} or {model_var} missing")
    provider = cls(model=os.getenv(model_var))
    r = provider.generate(
        prompt="Reply with the single word: ok",
        system_prompt="You are terse.",
        max_tokens=1000,
    )
    assert r.usable, f"{name}: finish={r.finish_reason}, text={r.text!r}"