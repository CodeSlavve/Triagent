# Learning log

## GitHub issue ingestion, cleaning and SQLite

The initial data source was the `pallets/flask` repository, but fetching its
issues showed that more than 80% of the issue data was unlabeled. That label
distribution would make supervised classifier training unreliable, so the
source was changed to `pytest-dev/pytest`.

The ingestion pipeline separates raw API records from derived data: issues and
comments are fetched as JSONL, cleaned into separate JSONL files, and then
loaded into SQLite. The fetchers use pagination, persistent checkpoints and
duplicate-ID checks so work can resume after interruption; the issue fetcher
also filters pull requests from the issues endpoint. Cleaning normalizes
whitespace and selected HTML/Markdown noise while preserving fenced code,
because code and tracebacks can be important issue evidence. Labels are mapped
to a compact category taxonomy, with missing and conflicting type labels kept
distinct rather than guessed.

SQLite provides relational joins and integrity checks for issues, comments
and labels without adding a hosted database. The loader enables foreign keys,
skips comments whose issue is not in the loaded dataset, and performs inserts
in a transaction. A deliberate tradeoff is that raw collection is append and
resume oriented, while cleaning regenerates derived files and loading rebuilds
the shared tables in `data/triagent.db`. This makes the transformation repeatable
but means loading another repository replaces the current issue/comment/label
dataset; raw and processed files are also local, gitignored data rather than a
shared dataset.

## LLM provider abstraction, failover and retry

The initial model plan was to use open models such as Llama through Groq. The
planned Llama models were later found to be discontinued on Groq, so the model
choice switched to the currently available OpenAI `gpt-oss-20b` model through
Groq.

Groq and Gemini have different SDK request and response shapes, so the
`LLMProvider` interface and shared `LLMResponse` provide a common call shape
and normalize finish reasons, usage metadata and latency where available.
`FallbackProvider` accepts providers in priority order and reports the provider
that produced the usable response. This keeps callers independent of the
provider-specific SDKs and gives a path to continue when a hosted service is
temporarily unavailable.

Retries are bounded and reserved for recognizable transient conditions such
as rate limits, network/timeouts and server errors; configuration or
authentication errors go directly to failover instead of repeating a request
that is unlikely to succeed. The default policy uses up to two retries with
exponential backoff capped at four seconds. A truncated result can separately
be retried once on the same provider with a larger token limit before moving
on. These safeguards trade some latency and duplicate request cost for
resilience; neither retries nor failover guarantee success, and live provider
availability and free-tier limits remain external constraints. Unit tests use
scripted providers to cover these paths without requiring network access, while
real provider calls are kept opt-in.
