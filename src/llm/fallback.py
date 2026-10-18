import logging

from src.llm.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class AllProvidersFailedError(RuntimeError):
    """Raised when every provider failed or returned an unusable response."""


class FallbackProvider(LLMProvider):
    """
    Tries providers in order (e.g. Groq, then Gemini) and returns the first usable response.

    For each provider:
      1. Call it. If it raises, record the error and move on.
      2. If the response is usable (non-empty and not truncated), return it.
      3. If it was cut off (finish_reason == "length"), retry ONCE on the same provider
         with a larger token cap before moving on.
      4. Otherwise record why it was unusable and move on.

    The returned LLMResponse keeps the real provider's name, so callers can see who answered.
    """

    name = "fallback"
    model = "fallback"

    def __init__(
        self,
        providers: list[LLMProvider],
        retry_on_truncation: bool = True,
        max_retry_tokens: int = 4000,
    ):
        if not providers:
            raise ValueError("FallbackProvider needs at least one provider")
        self.providers = providers
        self.retry_on_truncation = retry_on_truncation
        self.max_retry_tokens = max_retry_tokens
        self.last_failures: list[tuple[str, str]] = []

    def generate(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant.",
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        failures: list[tuple[str, str]] = []

        for provider in self.providers:
            response = self._try(provider, failures, prompt, system_prompt, temperature, max_tokens)
            if response is None:
                continue

            if response.usable:
                return self._done(response, failures)

            # Cut off: retry once on the same provider with a bigger cap.
            retry_tokens = min(max_tokens * 2, self.max_retry_tokens)
            if self.retry_on_truncation and response.truncated and retry_tokens > max_tokens:
                logger.info(
                    "%s truncated at %d tokens, retrying with %d",
                    provider.name, max_tokens, retry_tokens,
                )
                retry = self._try(provider, failures, prompt, system_prompt, temperature, retry_tokens)
                if retry is not None and retry.usable:
                    return self._done(retry, failures)
                if retry is not None:
                    response = retry

            reason = f"unusable response (finish_reason={response.finish_reason}, empty={not response.text.strip()})"
            failures.append((provider.name, reason))
            logger.warning("%s skipped: %s", provider.name, reason)

        self.last_failures = failures
        details = "; ".join(f"{name}: {reason}" for name, reason in failures)
        raise AllProvidersFailedError(f"All providers failed. {details}")

    def _try(self, provider, failures, prompt, system_prompt, temperature, max_tokens):
        """Call one provider. Return its response, or None if it raised."""
        try:
            return provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:  # any provider error triggers failover
            reason = f"{type(exc).__name__}: {exc}"
            failures.append((provider.name, reason))
            logger.warning("%s failed: %s", provider.name, reason)
            return None

    def _done(self, response: LLMResponse, failures: list[tuple[str, str]]) -> LLMResponse:
        self.last_failures = failures
        if failures:
            logger.info("answered by %s after earlier failures: %s", response.provider, failures)
        else:
            logger.info("answered by %s", response.provider)
        return response