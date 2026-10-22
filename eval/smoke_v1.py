import argparse
import os
import time
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

from src.llm import FallbackProvider, GeminiProvider, GroqProvider, AllProvidersFailedError
from src.triage.core import triage_issue

parser = argparse.ArgumentParser()
parser.add_argument("--provider", choices=["groq", "gemini"], default="groq")
parser.add_argument("--per-category", type=int, default=2)
args = parser.parse_args()

if args.provider == "groq":
    provider = FallbackProvider([GroqProvider(model=os.environ["GROQ_MODEL"])])
else:
    provider = FallbackProvider([GeminiProvider(model=os.environ["GEMINI_MODEL"])])

conn = sqlite3.connect(ROOT / "data" / "triagent.db")
issues = []
for cat in ("bug", "feature", "docs", "question", "other"):
    issues += conn.execute(
        "SELECT number, title, body, category FROM issues "
        "WHERE category = ? AND length(body) BETWEEN 200 AND 3000 "
        "ORDER BY number DESC LIMIT ?",
        (cat, args.per_category),
    ).fetchall()
conn.close()

valid = 0
failed = 0
for number, title, body, db_category in issues:
    try:
        result, info = triage_issue(provider, title, body)
    except AllProvidersFailedError as exc:
        print(f"\n#{number} | PROVIDER FAILED: {exc}")
        failed += 1
        time.sleep(8)
        continue
    print(f"\n#{number} | db label: {db_category} | {info['latency_s']}s "
          f"| tokens={info['completion_tokens']} | finish={info['finish_reason']}")
    if result:
        valid += 1
        note = " (had to strip fences/preamble)" if info["cleaned"] else ""
        print(f"  VALID{note}: {result.category} / {result.priority} / conf={result.confidence}")
        print(f"  summary: {result.summary}")
    else:
        print(f"  INVALID: {info['error'][:300]}")
        print(f"  raw: {info['raw'][:300]!r}")

    time.sleep(8)

answered = len(issues) - failed
print(f"\n{valid}/{answered} valid on {args.provider} | provider failures: {failed}")