# Triagent

Triagent is a learning-by-building project exploring an AI assistant for GitHub
engineering issues. The longer-term goal is to help triage issues using
classification, retrieval and an LLM, while keeping any GitHub write action
behind human approval.

## Current status

The repository currently contains an initial GitHub issue-data pipeline and an
LLM provider layer:

- Fetch GitHub issues and comments to raw JSONL, clean the records, and load
  issues, comments and labels into SQLite.
- Call Groq and Gemini through a shared provider interface. The fallback
  provider retries recognizable transient errors with bounded exponential
  backoff, moves to the next provider when needed, and records which provider
  answered.
- Unit tests cover provider response handling and fallback behavior. Live
  provider tests are opt-in and use real API quota.

This is an early backend/data project, not a finished triage application. There
is not yet a FastAPI service, triage endpoint, classifier, RAG pipeline, agent,
approval workflow, or Chrome extension in the current implementation.

## Architecture in the repository

```text
GitHub REST API
    │
    ├── src/ingestion/fetch_issues.py ──> data/raw/<owner>__<repo>/issues.jsonl
    ├── src/ingestion/fetch_comments.py ──> data/raw/<owner>__<repo>/comments.jsonl
    │
    └── src/ingestion/clean_issues.py ─> data/processed/<owner>__<repo>/*_clean.jsonl
                                              │
                              src/ingestion/load_sqlite.py
                                              ▼
                                      data/triagent.db

Application code ──> LLMProvider interface
                      ├── GroqProvider
                      ├── GeminiProvider
                      └── FallbackProvider (ordered providers, retries, failover)
```

The ingestion scripts keep raw responses separate from cleaned records. The
cleaning step normalizes issue and comment bodies, preserves fenced code and
maps labels to a small category set. SQLite stores issues, comments and labels
with foreign keys and indexes. The LLM providers return a shared `LLMResponse`
with text, normalized finish reason, provider/model names and available usage
and latency metadata. `FallbackProvider` retries transient provider errors
before failover, and can retry a truncated response once with a larger token
cap.

## Setup

Use Python 3.10 or newer and Git. From the repository root:

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in only the credentials you need:

```dotenv
GITHUB_TOKEN=your_github_token
GITHUB_SANDBOX_REPO=your-username/triagent-sandbox
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
GROQ_MODEL=openai/gpt-oss-20b
GEMINI_MODEL=your-available-gemini-model
```

The GitHub extraction scripts load `.env` from the project root. Provider
constructors read `GROQ_API_KEY` and `GEMINI_API_KEY` from the process
environment; load `.env` in your application (for example with
`python-dotenv`) before constructing a provider. Model names are supplied when
constructing providers. Do not commit `.env` or put real credentials in source
control. The current `.env.example` also lists optional later-stage settings;
those do not imply that their corresponding features are implemented.

## GitHub data pipeline

Run from the repository root. The scripts default to `pytest-dev/pytest`;
pass `--repo owner/name` to select another repository.

```bash
python src/ingestion/fetch_issues.py --repo pytest-dev/pytest --limit 2000
python src/ingestion/fetch_comments.py --repo pytest-dev/pytest
python src/ingestion/clean_issues.py --repo pytest-dev/pytest
python src/ingestion/load_sqlite.py --repo pytest-dev/pytest
```

`--limit` on the issue fetcher limits the total number of unique issues
collected. The comment fetcher accepts `--limit` and `--since` as well. The
fetchers append new records, skip already-saved IDs, and save pagination
checkpoints so an interrupted fetch can resume. Cleaning rewrites the derived
JSONL files without altering raw input. The SQLite loader rebuilds
`data/triagent.db` from those cleaned files; its issue, comment and label tables
are shared across repositories, so loading a different repository replaces
those tables' data. The `data/` directory is gitignored and is not included in
the repository.

To inspect raw-data counts and category distributions, run:

```bash
python src/ingestion/check_data.py
```

`check_data.py` currently targets the default `pytest-dev/pytest` raw-data
directory. `src/ingestion/fetch_docs.py` is also present for loading a
repository's documentation into the SQLite `docs` table; it downloads the
selected GitHub branch archive, and currently accepts `--repo` and `--branch`.

## LLM providers

The provider classes are exported from `src.llm`. For example, after setting
the API keys in the environment:

```python
import os
from dotenv import load_dotenv
from src.llm import FallbackProvider, GeminiProvider, GroqProvider

load_dotenv()
primary = GroqProvider(model=os.environ["GROQ_MODEL"])
backup = GeminiProvider(model=os.environ["GEMINI_MODEL"])
llm = FallbackProvider([primary, backup])

response = llm.generate("Summarize this issue.")
print(response.provider, response.text)
```

The default fallback policy allows two retries per provider for recognized
transient errors, with bounded exponential backoff, before trying the next
provider. Authentication/configuration errors are not treated as transient.
Live tests are excluded from the default test run; they can make external API
calls and consume free-tier quota.

## Tests

Run the offline test suite from the repository root:

```bash
python -m pytest
```

To opt in to the live provider tests, configure the relevant API key and model
environment variables and run:

```bash
python -m pytest -m live
```

Live tests call the provider APIs and may use free-tier quota. The default
pytest configuration excludes them.

## Next milestone

The next planned milestone is structured issue triage: define and validate a
Pydantic triage-result schema, build and evaluate a first prompt against both
providers, and then establish a labeled evaluation set and classifier baseline.
The planned retrieval, agent, API, approval and extension work remains future
work; none of it is claimed as implemented here.
