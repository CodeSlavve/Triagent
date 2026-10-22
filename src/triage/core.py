import json
import logging
from pathlib import Path

from pydantic import ValidationError

from src.llm.base import LLMProvider
from src.schema.triage import TriageResult

logger = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
MAX_BODY_CHARS = 1500


def build_system_prompt(version: str = "v1") -> str:
    template = (PROMPT_DIR / f"triage_{version}.txt").read_text(encoding="utf-8")
    schema = json.dumps(TriageResult.model_json_schema(), indent=2)
    return template.replace("{schema}", schema)


def build_user_prompt(title: str, body: str) -> str:
    return f"Title: {title}\n\n{body[:MAX_BODY_CHARS]}"


def extract_json(text: str) -> tuple[str, bool]:
    """Return (json_text, was_cleaned). Strips fences/preamble if present."""
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped, False
    start, end = stripped.find("{"), stripped.rfind("}")
    if start == -1 or end <= start:
        return stripped, True
    return stripped[start : end + 1], True


def triage_issue(provider: LLMProvider, title: str, body: str,
                 version: str = "v1", max_tokens: int = 2000):
    """Returns (TriageResult | None, info dict). Never raises on bad model output."""
    response = provider.generate(
        prompt=build_user_prompt(title, body),
        system_prompt=build_system_prompt(version),
        temperature=0.1,
        max_tokens=max_tokens,
    )
    info = {
        "provider": response.provider,
        "finish_reason": response.finish_reason,
        "latency_s": response.latency_s,
        "completion_tokens": response.completion_tokens,
        "raw": response.text,
        "cleaned": False,
        "error": None,
    }
    if not response.usable:
        info["error"] = f"unusable response (finish={response.finish_reason})"
        return None, info

    json_text, info["cleaned"] = extract_json(response.text)
    try:
        return TriageResult.model_validate_json(json_text), info
    except ValidationError as exc:
        info["error"] = str(exc)
        return None, info