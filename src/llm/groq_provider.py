import os
import time

from groq import Groq

from src.llm.base import LLMProvider, LLMResponse, normalize_finish_reason


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, model: str):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError("GROQ_API_KEY is missing")

        self.client = Groq(api_key=api_key)
        self.model = model

    def generate(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant.",
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        start = time.perf_counter()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_completion_tokens=max_tokens,
        )
        latency = time.perf_counter() - start

        choice = response.choices[0]
        return LLMResponse(
            text=choice.message.content or "",
            finish_reason=normalize_finish_reason(choice.finish_reason),
            provider=self.name,
            model=self.model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            latency_s=round(latency, 2),
        )