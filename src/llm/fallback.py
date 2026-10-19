import logging
import re
import time
from typing import Optional

from src.llm.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

_TRANSIENT_STATUS_CODES = {408, 409, 425, 429}
_TRANSIENT_EXCEPTION_NAMES = {
    "apiconnectionerror",
    "apitimeouterror",
    "connectionerror",
    "connecterror",
    "connecttimeout",
    "deadlineexceeded",
    "internalservererror",
    "networkerror",
    "readtimeout",
    "ratelimiterror",
    "remoteprotocolerror",
    "resourceexhausted",
    "servererror",
    "serviceunavailable",
    "timeout",
    "timeoutexception",
    "too many requests",
    "toomanyrequests",
}
_PERMANENT_EXCEPTION_NAMES = {
    "authenticationerror",
    "badrequesterror",
    "forbiddenerror",
    "invalidargument",
    "invalidargumenterror",
    "permissiondenied",
    "typeerror",
    "unauthorized",
    "valueerror",
}
_TRANSIENT_MESSAGE = re.compile(
    r"\b(rate.?limit|temporar(?:y|ily)|timed? ?out|timeout|connection reset|"
    r"service unavailable|overloaded|try again|http\s*5\d\d|5\d\d)\b",
    re.IGNORECASE,
)


class AllProvidersFailedError(RuntimeError):
    """Raised when every provider failed or returned an unusable response."""


class FallbackProvider(LLMProvider):
    """
    Tries providers in order (e.g. Groq, then Gemini) and returns the first usable response.

    For each provider:
      1. Call it. If it raises, record the error and move on.
         Transient errors are retried with bounded exponential backoff first.
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
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.5,
        max_retry_backoff_seconds: float = 4.0,
    ):
        if not providers:
            raise ValueError("FallbackProvider needs at least one provider")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if retry_backoff_seconds < 0 or max_retry_backoff_seconds < 0:
            raise ValueError("retry backoff values must be non-negative")
        self.providers = providers
        self.retry_on_truncation = retry_on_truncation
        self.max_retry_tokens = max_retry_tokens
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.max_retry_backoff_seconds = max_retry_backoff_seconds
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
        """Call one provider, retrying identifiable transient errors before failover."""
        retries = 0
        while True:
            try:
                return provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as exc:  # preserve provider failover for provider errors
                if not _is_transient_provider_error(exc) or retries >= self.max_retries:
                    reason = f"{type(exc).__name__}: {exc}"
                    if retries:
                        reason = f"{reason} (after {retries} retries)"
                    failures.append((provider.name, reason))
                    logger.warning("%s failed: %s", provider.name, reason)
                    return None

                delay = min(
                    self.retry_backoff_seconds * (2 ** retries),
                    self.max_retry_backoff_seconds,
                )
                retries += 1
                logger.warning(
                    "%s transient failure (%s); retrying (%d/%d) in %.2f seconds",
                    provider.name, exc, retries, self.max_retries, delay,
                )
                time.sleep(delay)

    def _done(self, response: LLMResponse, failures: list[tuple[str, str]]) -> LLMResponse:
        self.last_failures = failures
        if failures:
            logger.info("answered by %s after earlier failures: %s", response.provider, failures)
        else:
            logger.info("answered by %s", response.provider)
        return response


def _is_transient_provider_error(exc: Exception) -> bool:
    """Conservatively identify provider throttling, network, and server-side errors."""
    names = {cls.__name__.lower() for cls in type(exc).__mro__}
    if names & _PERMANENT_EXCEPTION_NAMES:
        return False

    status = _http_status_code(exc)
    if status is not None:
        return status in _TRANSIENT_STATUS_CODES or 500 <= status <= 599
    if names & _TRANSIENT_EXCEPTION_NAMES:
        return True

    # SDKs don't expose a shared exception hierarchy; explicitly recognizable
    # transient messages cover common rate-limit and transport failures.
    return bool(_TRANSIENT_MESSAGE.search(str(exc)))


def _http_status_code(exc: Exception) -> Optional[int]:
    """Read an HTTP status exposed by common provider SDK exception shapes."""
    candidates = [getattr(exc, "status_code", None), getattr(exc, "code", None)]
    response = getattr(exc, "response", None)
    candidates.append(getattr(response, "status_code", None))

    for value in candidates:
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None