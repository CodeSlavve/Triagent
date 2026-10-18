import os
from pathlib import Path

from dotenv import load_dotenv

from src.llm import LLMProvider, GroqProvider, GeminiProvider

# Load .env from the Triagent project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=True)


def test_provider(name: str, provider: LLMProvider) -> None:
    print(f"\nTesting {name}...")

    try:
        response = provider.generate(
            prompt="Explain what an API is in two sentences.",
            system_prompt="You are a concise programming tutor.",
            max_tokens=150,
        )

        assert isinstance(response, str), "Response is not a string"
        assert response.strip(), "Response is empty"

        print(f"PASS: {name} returned a valid string")
        print(f"Response: {response}")

    except Exception as exc:
        print(f"FAIL: {name}: {type(exc).__name__}: {exc}")


providers: list[tuple[str, LLMProvider]] = []

# Initialize each provider independently so one failure
# doesn't prevent the other provider from being tested.
for name, provider_class, env_var in [
    ("Groq", GroqProvider, "GROQ_MODEL"),
    ("Gemini", GeminiProvider, "GEMINI_MODEL"),
]:
    model = os.getenv(env_var)

    if not model:
        print(f"SKIP: {name} — {env_var} is missing from .env")
        continue

    try:
        providers.append((name, provider_class(model=model)))
    except Exception as exc:
        print(f"INIT FAIL: {name}: {type(exc).__name__}: {exc}")

for name, provider in providers:
    test_provider(name, provider)
