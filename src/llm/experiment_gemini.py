"""
Day 5 experiments on Gemini: system prompts, temperature, token limits.
Same structure and output as experiments.py (Groq) so the results can be compared.

Save as src/llm/experiments_gemini.py (a NEW file; experiment_gemini.py stays untouched)
and run from the project root:
    python src/llm/experiment_gemini.py --experiment system
    python src/llm/experiment_gemini.py --experiment temperature
    python src/llm/experiment_gemini.py --experiment tokens
    python src/llm/experiment_gemini.py --experiment all --issue 4234

Every call is appended to data/experiments/day5_gemini.jsonl (data/ is gitignored).
"""
import argparse
import json
import os
import sqlite3
import time
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=True)

api_key = os.getenv("GEMINI_API_KEY", "").strip()
if not api_key:
    raise ValueError("GEMINI_API_KEY is missing or empty in .env")

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
client = genai.Client(api_key=api_key)

LOG_FILE = ROOT / "data" / "experiments" / "day5_gemini.jsonl"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

parser = argparse.ArgumentParser()
parser.add_argument("--experiment", choices=["system", "temperature", "tokens", "all"], default="all")
parser.add_argument("--issue", type=int, default=None, help="issue number from the SQLite DB")
parser.add_argument("--runs", type=int, default=5, help="repeats per setting in the temperature test")
args = parser.parse_args()


def load_issue(number):
    conn = sqlite3.connect(ROOT / "data" / "triagent.db")
    if number is None:
        # Same deterministic pick as the Groq script so results are comparable.
        row = conn.execute(
            "SELECT number, title, body, category FROM issues "
            "WHERE category = 'bug' AND length(body) BETWEEN 400 AND 1500 "
            "ORDER BY number LIMIT 1 OFFSET 50"
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT number, title, body, category FROM issues WHERE number = ?", (number,)
        ).fetchone()
    conn.close()
    if row is None:
        raise SystemExit("Issue not found. Check the number or the DB path.")
    return row


NUMBER, TITLE, BODY, TRUE_CATEGORY = load_issue(args.issue)
ISSUE_TEXT = f"Title: {TITLE}\n\n{BODY[:1500]}"
print(f"Model: {MODEL}")
print(f"Issue #{NUMBER} (true category: {TRUE_CATEGORY}): {TITLE}\n")


def ask(system, user, temperature=0.3, max_tokens=500, tag=""):
    start = time.perf_counter()
    response = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=user,  # Gemini: only the user text goes here
                config=types.GenerateContentConfig(
                    system_instruction=system,  # Gemini: system prompt lives in the config
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            break
        except Exception as exc:
            msg = str(exc)
            if attempt < 2 and ("429" in msg or "RESOURCE_EXHAUSTED" in msg):
                print(f"  rate limited, waiting 20s (attempt {attempt + 1}/3)")
                time.sleep(20)
                continue
            raise
    latency = time.perf_counter() - start

    candidate = response.candidates[0] if response.candidates else None
    usage = response.usage_metadata
    result = {
        "tag": tag,
        "model": MODEL,
        "issue": NUMBER,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "text": (response.text or "").strip(),
        "finish_reason": str(getattr(candidate, "finish_reason", None)),
        "completion_tokens": getattr(usage, "candidates_token_count", None),
        "reasoning_tokens": getattr(usage, "thoughts_token_count", None),
        "latency_s": round(latency, 2),
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    time.sleep(2)  # be gentle with free-tier rate limits
    return result


def words(text):
    return len(text.split())


# ---------------------------------------------------------------- experiment 1
def experiment_system():
    print("=== EXPERIMENT 1: same issue, three system prompts (temperature 0.3) ===")
    prompts = {
        "A generic": "You are a helpful assistant.",
        "B role": "You are a senior maintainer of the pytest project triaging GitHub issues. Be concise and factual.",
        "C constrained": (
            "Summarize the issue in exactly one sentence of at most 25 words. "
            "Do not add information that is not in the issue. If unsure, say 'unknown'."
        ),
    }
    user = f"Summarize this GitHub issue.\n\n{ISSUE_TEXT}"
    for name, system in prompts.items():
        r = ask(system, user, temperature=0.3, max_tokens=800, tag=f"system:{name}")
        print(f"\n[{name}] words={words(r['text'])} finish={r['finish_reason']} "
              f"tokens={r['completion_tokens']} reasoning={r['reasoning_tokens']}")
        print(r["text"] or "(EMPTY REPLY)")


# ---------------------------------------------------------------- experiment 2
def experiment_temperature():
    print(f"\n=== EXPERIMENT 2: temperature 0 vs 1.0, {args.runs} runs each ===")
    tasks = {
        "classify": (
            "Classify the GitHub issue as exactly one of: bug, feature, docs, question, other. "
            "Reply with only the label.",
            f"{ISSUE_TEXT}",
        ),
        "summary": (
            "Summarize the issue in one sentence.",
            f"{ISSUE_TEXT}",
        ),
    }
    for task, (system, user) in tasks.items():
        for temp in (0.0, 1.0):
            outs = [ask(system, user, temperature=temp, max_tokens=800,
                        tag=f"temp:{task}")["text"] for _ in range(args.runs)]
            lengths = [words(o) for o in outs]
            print(f"\n[{task}] temperature={temp}")
            print(f"  distinct outputs: {len(set(outs))}/{len(outs)}")
            print(f"  word count range: {min(lengths)}-{max(lengths)}")
            if task == "classify":
                print(f"  answers: {dict(Counter(o.lower() for o in outs))}  (true: {TRUE_CATEGORY})")
            else:
                for o in outs:
                    print(f"  - {o[:140]}")


# ---------------------------------------------------------------- experiment 3
def experiment_tokens():
    print("\n=== EXPERIMENT 3: max_output_tokens (same prompt) ===")
    system = "You are a concise assistant for GitHub issue triage."
    user = f"Explain what this issue is about in 3-5 sentences.\n\n{ISSUE_TEXT}"
    for cap in (30, 100, 300, 1000):
        r = ask(system, user, temperature=0.3, max_tokens=cap, tag="tokens")
        print(f"\ncap={cap}: finish={r['finish_reason']} completion_tokens={r['completion_tokens']} "
              f"reasoning={r['reasoning_tokens']} words={words(r['text'])}")
        print(r["text"] or "(EMPTY REPLY: cap too low, possibly used up by thinking tokens)")


if __name__ == "__main__":
    if args.experiment in ("system", "all"):
        experiment_system()
    if args.experiment in ("temperature", "all"):
        experiment_temperature()
    if args.experiment in ("tokens", "all"):
        experiment_tokens()
    print(f"\nAll calls logged to {LOG_FILE}")