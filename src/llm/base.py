import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


def normalize_finish_reason(raw) -> str:
    """Map provider-specific values ('length', 'FinishReason.MAX_TOKENS', ...) to stop/length/other."""
    value = str(raw).lower()
    if "length" in value or "max_tokens" in value:
        return "length"
    if "stop" in value:
        return "stop"
    return "other"


@dataclass
class LLMResponse:
    text: str
    finish_reason: str  # "stop", "length" or "other"
    provider: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_s: Optional[float] = None

    @property
    def truncated(self) -> bool:
        return self.finish_reason == "length"

    @property
    def usable(self) -> bool:
        return bool(self.text.strip()) and not self.truncated


class LLMProvider(ABC):
    name: str = "unknown"
    model: str = ""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant.",
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        """Generate a response from the LLM."""