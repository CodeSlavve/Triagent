import os
import time

from google import genai
from google.genai import types

from src.llm.base import LLMProvider, LLMResponse, normalize_finish_reason


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, model: str):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing")

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant.",
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> LLMResponse:
        start = time.perf_counter()
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        latency = time.perf_counter() - start

        candidate = response.candidates[0] if response.candidates else None
        usage = response.usage_metadata
        return LLMResponse(
            text=response.text or "",
            finish_reason=normalize_finish_reason(getattr(candidate, "finish_reason", None)),
            provider=self.name,
            model=self.model,
            prompt_tokens=getattr(usage, "prompt_token_count", None),
            completion_tokens=getattr(usage, "candidates_token_count", None),
            latency_s=round(latency, 2),
        )
        return response.text or ""