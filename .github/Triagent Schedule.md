# Triagent — AI-Powered GitHub Engineering Copilot — 8-Week Build Schedule (+ Week 9 Extended Extension)

A zero-cost, learning-by-building project: **LLMs → Prompt Engineering → Embeddings → RAG → Tool Calling → AI Agents (LangGraph) → AI Automation → FastAPI/Docker → Chrome Extension**.

**Goal:** a portfolio-quality GenAI/Agentic AI project that lets you confidently discuss and demo Generative AI, open-weight LLMs (gpt-oss), Prompt Engineering, RAG, AI Agents, AI automation workflows, and AI-based solutions in internship interviews.

---

## 1. Time Budget

| Slot | Hours/day | Days/week | Hours/week |
|---|---|---|---|
| Weekdays (Day 1-5) | 3-4 | 5 | 15-20 |
| Weekends (Day 6-7) | 5-6 | 2 | 10-12 |
| **Total** | | | **~25-32 (planned at ~28)** |

- **Core plan:** 8 weeks x ~28 h = ~224 h (project estimate: 170-230 h).
- **Week 9:** first absorbs any slipped work, then adds the **extended Chrome extension features** (~12-18 h). The project is complete and portfolio-ready after Week 8 (extension MVP); Week 9 is a bonus tier.
- **Weekday blocks** = one focused learn-or-build task. **Weekend blocks** = bigger integration work, evaluation, and catch-up.
- Each week ends with a **checkpoint**. If a checkpoint is missed, cut scope (see Section 9) instead of extending the schedule.

---

## 2. Architecture (Target State)

```text
GitHub Issue (new / existing)
        ↓
   AI Triage Agent (LangGraph)
        ↓
┌───────────────┬───────────────┬──────────────────┐
│ ML Classifier │  RAG Search   │  GitHub Tools    │
└───────────────┴───────────────┴──────────────────┘
        ↓
  LLM (gpt-oss via Groq, Gemini fallback)
        ↓
  Structured Analysis (Pydantic JSON)
        ↓
  Diagnosis + Priority + Suggested Action
        ↓
  Human Approval
        ↓
  Optional GitHub Action (label / link duplicate / comment)
```

Interfaces: **FastAPI** backend (`/health`, `/triage`, `/search`, `/issues/{id}`, `/chat`, `/webhook`, `/triage/{id}/approve`, `/triage/{id}/reject`, plus `/stats` for the extended popup) → consumed by a **Chrome extension** on GitHub.

### Extension Scope: MVP vs Extended

The extension is the final product layer, not the main focus. It is built in two tiers so the core project is never blocked by UI work.

| Feature | Tier | Built in | Backend dependency |
|---|---|---|---|
| Sidebar on issue pages (shadow DOM), re-injected on GitHub page navigation | MVP | Week 8 | none |
| Issue type, classification confidence, priority | MVP | Week 8 | `/triage` |
| Similar/duplicate issues + relevant docs | MVP | Week 8 | `/triage`, `/search` |
| Diagnosis + recommended action with cited evidence | MVP | Week 8 | `/triage` |
| Approve / Reject buttons | MVP | Week 8 | approve/reject endpoints |
| Settings (API URL + token via `chrome.storage.local`), loading + error states | MVP | Week 8 | none |
| Live triage banner on the new-issue form (debounced, as you type) | Extended | Week 9 | `/triage` in draft mode (no GitHub actions) |
| RAG card: how similar past issues were resolved | Extended | Week 9 | existing RAG pipeline |
| Popup with repo stats + settings + API key | Extended | Week 9 | new `/stats` endpoint |
| Time-to-close estimate card | Extended (stretch) | Week 9, only if estimator is built | small regression model |
| Service-worker token handling + UI polish | Extended | Week 9 | none |

---

## 3. Zero-Cost Stack Reference

> Free-tier limits change often. Verify current limits when you sign up, and keep the provider abstraction so you can swap providers.
>
> **LLM provider decisions (2026-10-18):** Llama models are no longer served on Groq (llama-3.1-8b-instant and llama-3.3-70b-versatile deprecated 2026-08-16), so gpt-oss via Groq is used instead. Ollama / local Llama is skipped (8GB RAM, poor results in an earlier trial); hosted providers only, so retry and failover matter. Hugging Face Inference Providers is dropped because free accounts need purchased credits.

| Layer | Tool | Cost |
|---|---|---|
| Data source | GitHub REST API (personal access token) | Free |
| Storage | JSONL (raw) + SQLite (cleaned) | Free |
| Embeddings | `sentence-transformers` (e.g. MiniLM / BGE-small), run locally or on Colab | Free |
| Vector DB | Chroma (persistent, local); optional swap to Qdrant in Docker | Free |
| LLM (primary) | gpt-oss (openai/gpt-oss-20b, 120b as fallback) via Groq free tier | Free |
| LLM (fallback) | Gemini free tier | Free |
| Structured output | Pydantic + JSON mode / schema-constrained output | Free |
| Classic ML | scikit-learn (TF-IDF + Logistic Regression) | Free |
| Agent framework | LangGraph (+ LangChain core utilities) | Free |
| RAG evaluation | Custom metrics (hit@k, MRR) + LLM-as-judge; optional RAGAS | Free |
| Tracing / logging | Python logging + JSONL traces; optional Langfuse/LangSmith free tier | Free |
| Backend | FastAPI + Uvicorn | Free |
| Containers | Docker + Docker Compose | Free |
| Webhook testing | smee.io or ngrok free tier | Free |
| CI | GitHub Actions | Free |
| Deployment | Hugging Face Spaces (Docker) or Render free tier | Free |
| Frontend | Chrome Extension, Manifest V3 (Load Unpacked) | Free |

---

## 4. Suggested Repo Structure

```text
triagent/
├── data/                  # raw JSONL, cleaned SQLite, eval sets (gitignored if large)
├── src/
│   ├── ingestion/         # GitHub API extraction + cleaning
│   ├── llm/               # provider abstraction (groq, gemini)
│   ├── prompts/           # versioned prompt files (v1, v2, ...)
│   ├── schemas/           # Pydantic models (TriageResult, etc.)
│   ├── classifier/        # TF-IDF + LogReg
│   ├── rag/               # chunking, embeddings, retriever, pipeline
│   ├── tools/             # get_issue, search_issues, ... tool functions
│   ├── agent/             # LangGraph graph, state, nodes
│   ├── automation/        # webhook handler, approval queue, actions
│   └── api/               # FastAPI app
├── eval/                  # eval datasets + scripts + results
├── extension/             # Chrome extension (MV3): MVP + extended
├── notebooks/             # experiments
├── docs/                  # architecture, prompt experiments, failure cases
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── README.md
```

---

## 5. Learning Method (Applies Every Week)

For each new technology, follow this loop:

1. **Learn (30-60 min):** read the official docs/quickstart, run the minimal example.
2. **Build:** implement it in the project, not in a throwaway notebook.
3. **Break it:** find at least one failure case and log it in `docs/failure-cases.md`.
4. **Explain:** write 3-5 sentences in `docs/learning-log.md` on what it is, why you used it, and its trade-offs. These become your interview answers.

---

# 6. Week-by-Week Schedule

## Week 1 — Setup, GitHub Data & LLM Basics (~28 h)

**Learn:** GitHub REST API, pagination, rate limits; LLM API basics (chat completions, system vs user messages, temperature, tokens).

- [x] **Day 1 (Mon, 3-4 h)** — Create repo + folder structure, `.env.example`, virtual env. Create GitHub token. Test API calls on 1 primary repo (suggested: a smaller, well-documented repo such as `pallets/flask`) and note one larger stretch repo. Create a **sandbox repo of your own** for safe automation testing later.
- [x] **Day 2 (Tue, 3-4 h)** — Write extraction script: issues + comments (paginated, rate-limit aware) into raw JSONL. Target ~2,000-5,000 issues.
- [x] **Day 3 (Wed, 3-4 h)** — Cleaning: strip HTML/markdown noise, handle code blocks and stack traces (keep them, mark them), normalize labels into a small taxonomy (bug / feature / docs / question / other).
- [x] **Day 4 (Thu, 3-4 h)** — Load cleaned data into SQLite (issues, comments, labels tables). Also pull README + docs pages for the repo into a `docs` table.
- [x] **Day 5 (Fri, 3-4 h)** — Get a Groq API key (and Gemini key as backup). Make your first LLM calls from Python. Experiment with system prompts, temperature, and token limits. Use `openai/gpt-oss-20b`; check the `/models` list for what is live.
- [x] **Day 6 (Sat, 5-6 h)** — Build the **provider abstraction** (`llm/` module): one interface, Groq + Gemini implementations. Add retry with backoff and Groq-to-Gemini failover; log which provider answered.
- [x] **Day 7 (Sun, 5-6 h)** — Buffer / catch-up: fix data quality problems, backfill more issues. Write README skeleton and first `learning-log.md` entries.

**Checkpoint:** cleaned issue data in SQLite; same prompt runs against Groq and Gemini through one interface.

---

## Week 2 — Milestone 1: LLM App + Prompt Engineering + Classifier (~28 h)

**Learn:** structured outputs, prompt engineering patterns (instructions, constraints, few-shot, output formatting), prompt evaluation, hallucination reduction.

- [ ] **Day 1 (Mon, 3-4 h)** — Define Pydantic `TriageResult` schema (category, priority, summary, suggested_action, confidence, reasoning). Write prompt **v1** and get valid JSON back.
- [ ] **Day 2 (Tue, 3-4 h)** — Add validation + retry-on-invalid-JSON logic. Handle malformed output and refusals.
- [ ] **Day 3 (Wed, 3-4 h)** — Build the **eval set**: hand-label 40-60 representative issues (category, priority, ideal action). Store in `eval/triage_eval.jsonl`.
- [ ] **Day 4 (Thu, 3-4 h)** — Write the prompt eval script: run a prompt version over the eval set, report accuracy / schema-validity / latency per provider.
- [ ] **Day 5 (Fri, 3-4 h)** — Write prompt **v2** (few-shot examples, explicit constraints, "say unknown if unsure"). Compare v1 vs v2.
- [ ] **Day 6 (Sat, 5-6 h)** — Prompt **v3** focused on hallucination reduction. Compare all versions across providers. Record results in `docs/prompt-experiments.md`. Version prompts as files in `prompts/`.
- [ ] **Day 7 (Sun, 5-6 h)** — Lightweight classifier: TF-IDF + Logistic Regression for the same categories. Compare to the LLM on the eval set (accuracy, latency, cost). Expose both behind a `classify_issue()` function.

**Checkpoint:** `GitHub Issue → LLM → Structured Triage` works with measured prompt versions; classifier baseline exists.

---

## Week 3 — Milestone 2 (Part 1): Embeddings, Vector DB & Basic RAG (~28 h)

**Learn:** embeddings, cosine similarity, chunking strategies, vector databases, metadata filtering.

- [ ] **Day 1 (Mon, 3-4 h)** — Embeddings fundamentals: embed sample issues with `sentence-transformers`, inspect similarity scores. Test the Unicode example ("CSV import crashes on Unicode" vs `UnicodeDecodeError` issues).
- [ ] **Day 2 (Tue, 3-4 h)** — Set up Chroma (persistent). Design collections: `issues`, `docs`, `discussions`. Decide metadata (issue number, state, labels, URL, created_at).
- [ ] **Day 3 (Wed, 3-4 h)** — Chunking: issue title+body as one unit, comments as separate chunks, docs by heading/paragraph with overlap. Index everything.
- [ ] **Day 4 (Thu, 3-4 h)** — Semantic search function `search_similar(issue_text, k)`. Add metadata filters (e.g. closed only, exclude the issue itself).
- [ ] **Day 5 (Fri, 3-4 h)** — Duplicate detection: similarity threshold + borderline handling. Manually test on 15-20 known duplicates.
- [ ] **Day 6 (Sat, 5-6 h)** — Build **RAG v1**: issue → embed → retrieve top-k → build context → LLM → grounded answer. Context template with source IDs.
- [ ] **Day 7 (Sun, 5-6 h)** — Make answers **cite sources** (issue numbers / doc URLs). Compare RAG vs no-RAG outputs on 10 issues; note where RAG helps and where it hurts.

**Checkpoint:** `Issue → Retrieval → Context → LLM` works and returns cited answers.

---

## Week 4 — Milestone 2 (Part 2): RAG Hardening & Evaluation (~28 h)

**Learn:** retrieval metrics, re-ranking, faithfulness/hallucination evaluation, LLM-as-judge, latency profiling.

- [ ] **Day 1 (Mon, 3-4 h)** — Build the **RAG eval dataset**: 30-50 queries, each with the known relevant issues/docs (ground truth) and a reference answer.
- [ ] **Day 2 (Tue, 3-4 h)** — Retrieval metrics: implement hit@k and MRR. Run baseline and record.
- [ ] **Day 3 (Wed, 3-4 h)** — Improve retrieval: try different chunk sizes, top-k, hybrid keyword + vector search, or a re-ranker. Re-measure each change.
- [ ] **Day 4 (Thu, 3-4 h)** — Answer-quality eval: LLM-as-judge for answer relevance and **faithfulness** (is every claim supported by retrieved context?). Optionally try RAGAS.
- [ ] **Day 5 (Fri, 3-4 h)** — Hallucination reduction in the RAG prompt: "answer only from context", abstain when evidence is weak, require citations. Re-measure.
- [ ] **Day 6 (Sat, 5-6 h)** — Latency + failure analysis: time each stage (embed / retrieve / generate), log slow and wrong cases in `docs/failure-cases.md`.
- [ ] **Day 7 (Sun, 5-6 h)** — Write `docs/rag-evaluation.md` with tables (before/after for each change). Buffer / catch-up.

**Checkpoint:** measured RAG pipeline with documented metrics, failure cases, and improvements.

---

## Week 5 — Milestone 3 (Part 1): Tool Calling & Agent Loop From Scratch (~28 h)

**Learn:** function/tool calling, JSON schemas for tools, the ReAct-style agent loop, tool errors, guardrails.

- [ ] **Day 1 (Mon, 3-4 h)** — Tool calling basics: a toy tool call with Groq (gpt-oss; basic tool calling confirmed working 2026-10-18) (model requests a tool → you execute → return result → final answer).
- [ ] **Day 2 (Tue, 3-4 h)** — Implement GitHub tools: `get_issue()`, `get_issue_comments()`, `get_pull_request()` (read-only, with caching to save rate limit).
- [ ] **Day 3 (Wed, 3-4 h)** — Implement retrieval tools: `search_issues()` (vector), `search_documentation()`, `classify_issue()`. Write clear tool descriptions and schemas.
- [ ] **Day 4 (Thu, 3-4 h)** — Optional: `search_code()` via GitHub code search (skip if rate limits or time are an issue). Add input validation and error handling for all tools.
- [ ] **Day 5 (Fri, 3-4 h)** — Wire tools into the LLM: let the model choose which tool to call for a given issue question. Test tool selection accuracy on 10 queries.
- [ ] **Day 6 (Sat, 5-6 h)** — Build a **plain Python agent loop** (no framework): loop until the model returns a final answer, with a max-steps limit and a trace log of every step.
- [ ] **Day 7 (Sun, 5-6 h)** — Run the agent on 15-20 issues. Record where it loops, picks wrong tools, or hallucinates. Update `docs/failure-cases.md`.

**Checkpoint:** `LLM → Tools → RAG → GitHub API` works in a hand-written agent loop.

---

## Week 6 — Milestone 3 (Part 2) + Milestone 4 (Start): LangGraph Agent & Webhook (~28 h)

**Learn:** LangGraph (state, nodes, edges, conditional routing, checkpointing), webhooks, event-driven workflows.

- [ ] **Day 1 (Mon, 3-4 h)** — LangGraph basics: tutorial graph, understand `State`, nodes, edges, conditional edges.
- [ ] **Day 2 (Tue, 3-4 h)** — Port the triage workflow to LangGraph with explicit nodes: `classify → search_similar → retrieve_docs → inspect_github → analyze → recommend`.
- [ ] **Day 3 (Wed, 3-4 h)** — Add conditional routing (e.g. high-similarity duplicate → short-circuit to duplicate recommendation; low confidence → gather more evidence).
- [ ] **Day 4 (Thu, 3-4 h)** — Final node produces the structured `TriageRecommendation` (diagnosis, priority, suggested action, evidence with citations). Add max-step and timeout guards.
- [ ] **Day 5 (Fri, 3-4 h)** — Compare LangGraph agent vs plain loop vs RAG-only on your eval set. Document the differences.
- [ ] **Day 6 (Sat, 5-6 h)** — FastAPI `/webhook` endpoint: receive GitHub `issues.opened` events, verify the webhook secret signature, and trigger the agent. Test locally with smee.io or ngrok against your **sandbox repo**.
- [ ] **Day 7 (Sun, 5-6 h)** — Make the webhook handler async (queue/background task) so GitHub gets a fast response. Store each triage result in SQLite with status `pending_approval`.

**Checkpoint (resume-ready):** an agent that triages issues with RAG + tools and is triggered by real GitHub events. **This is a good point to start applying to internships**, while you finish the remaining weeks.

---

## Week 7 — Milestone 4 (Finish) + Milestone 5: Human Approval, API & Production (~28 h)

**Learn:** human-in-the-loop design, FastAPI patterns, Docker, logging, CI, free-tier deployment.

- [ ] **Day 1 (Mon, 3-4 h)** — Human approval flow: `pending → approved / rejected` states, endpoints `POST /triage/{id}/approve` and `/reject`.
- [ ] **Day 2 (Tue, 3-4 h)** — GitHub actions behind approval: apply labels, post a suggested comment, link a duplicate. **No action runs without approval.** Test only on your sandbox repo.
- [ ] **Day 3 (Wed, 3-4 h)** — Clean up the FastAPI surface: `/health`, `/triage`, `/search`, `/issues/{id}`, `/chat`. Pydantic request/response models, error handling, CORS (needed for the extension).
- [ ] **Day 4 (Thu, 3-4 h)** — Logging and tracing: structured logs per request (latency, tool calls, token use, errors). Environment-based secrets only.
- [ ] **Day 5 (Fri, 3-4 h)** — Dockerfile + `docker-compose.yml` (API + vector DB). Verify a clean build from scratch.
- [ ] **Day 6 (Sat, 5-6 h)** — Deploy the backend (Hugging Face Spaces Docker or Render free tier). Verify endpoints work remotely; handle cold starts and free-tier limits.
- [ ] **Day 7 (Sun, 5-6 h)** — GitHub Actions CI: run tests + the small prompt/RAG eval suite on pull requests. Add basic unit tests for tools and schemas.

**Checkpoint:** deployed, containerized, logged API with an approval-gated automation workflow and CI evals.

---

## Week 8 — Milestone 6 + 7: Chrome Extension (MVP), Documentation & Demo (~28 h)

**Learn:** Manifest V3, content scripts, shadow DOM, service workers, `chrome.storage`; technical writing for portfolios.

**Extension MVP scope (this week):** sidebar on issue pages showing issue type, confidence and priority; similar issues and docs; diagnosis + recommended action with citations; Approve / Reject; settings (API URL + token); loading and error states.

**Deferred to Week 9 (extended):** new-issue live banner, RAG resolution card, repo-stats popup, time-to-close card.

> Budget: ~16-18 h for the MVP extension (weekdays) and ~10-12 h for docs and demo (weekend). If behind, finish Days 1-4 only and move the end-to-end polish to Week 9 Day 1.

- [ ] **Day 1 (Mon, 3-4 h)** — Manifest V3, permissions (GitHub host + your backend), content script skeleton. Inject a sidebar container on issue pages using **shadow DOM**.
- [ ] **Day 2 (Tue, 3-4 h)** — Call `/triage` and `/search` from the extension (via the service worker). Show issue type, confidence, priority.
- [ ] **Day 3 (Wed, 3-4 h)** — Show similar issues, relevant docs, diagnosis, and recommended action with citations, plus **Approve / Reject** buttons wired to the approval endpoints.
- [ ] **Day 4 (Thu, 3-4 h)** — Loading/error states, API URL + token settings via `chrome.storage.local`, handle GitHub's SPA navigation (re-inject on page change).
- [ ] **Day 5 (Fri, 3-4 h)** — End-to-end walkthrough on your sandbox repo and one real repo (read-only). Fix rough edges.
- [ ] **Day 6 (Sat, 5-6 h)** — Documentation: README (architecture diagram, setup, demo GIF), `docs/architecture.md`, design decisions, prompt experiments, RAG evaluation, agent workflow, failure cases, performance, limitations.
- [ ] **Day 7 (Sun, 5-6 h)** — Record a 2-3 minute demo video of the MVP. Final cleanup: remove secrets from history, add `.env.example`, pin dependencies, tag a release `v1.0`.

**Checkpoint:** complete portfolio-ready project with extension MVP and demo.

---

## Week 9 — Extension Extended Version + Overflow Buffer (~28 h)

**Learn:** content scripts on form pages, debouncing and request cancellation, popup UI, reusing backend pipelines in new UI surfaces.

> Day 1 comes first for any slipped work from Weeks 6-8. The extended features below are the lowest priority in the whole project and are the first things to cut (see Section 9). Budget ~12-18 h for extended features; the rest of the week is buffer.

- [ ] **Day 1 (Mon, 3-4 h)** — Overflow triage: finish slipped MVP, docs, or eval items in priority order (extension MVP → docs/demo → extra eval runs).
- [ ] **Day 2 (Tue, 3-4 h)** — **Live triage banner** on the new-issue form: content script on the new-issue page, debounced calls to `/triage` in draft mode (no GitHub actions), banner showing predicted category and likely duplicates.
- [ ] **Day 3 (Wed, 3-4 h)** — Banner hardening: request cancellation, minimum text length, rate-limit handling, graceful failure when the backend is asleep (free-tier cold start).
- [ ] **Day 4 (Thu, 3-4 h)** — **RAG resolution card** in the sidebar: how similar past (closed) issues were resolved, with citations, reusing the existing RAG pipeline.
- [ ] **Day 5 (Fri, 3-4 h)** — **Repo stats popup**: add a small `/stats` endpoint (issue counts by category, indexed issues, recent triage outcomes) and a popup UI with stats, settings, and API key.
- [ ] **Day 6 (Sat, 5-6 h)** — **Stretch (optional):** time-to-close estimator (simple regression on issue metadata + text length features), exposed via `/triage` and shown as a sidebar card. If you skip it, use this slot for service-worker token handling and UI polish.
- [ ] **Day 7 (Sun, 5-6 h)** — Regression test the full extension (MVP + extended) on the sandbox repo, update the README and demo video with the extended features, tag `v1.1`.

**Checkpoint:** complete extension experience: MVP plus extended features, documented and demoed.

---

## 7. Milestone Summary

| Week | Milestone | What exists at the end |
|---|---|---|
| 1 | Setup + data + LLM basics | Cleaned data, multi-provider LLM layer |
| 2 | M1: LLM app + prompts | Structured triage, prompt experiments, classifier baseline |
| 3 | M2a: Embeddings + RAG | Vector search, duplicate finder, cited RAG answers |
| 4 | M2b: RAG evaluation | Metrics, failure analysis, improved retrieval |
| 5 | M3a: Tool calling | Tools + plain agent loop |
| 6 | M3b + M4a: LangGraph + webhook | Agent workflow triggered by GitHub events |
| 7 | M4b + M5: Approval + production | Approval-gated actions, Docker, deployment, CI |
| 8 | M6 + M7: Extension MVP + docs | Chrome extension MVP, documentation, demo |
| 9 | Extended extension + overflow | New-issue banner, resolution card, stats popup, optional time-to-close card |

---

## 8. Skills-to-Evidence Map (Interview Talking Points)

| Skill internships ask for | Where you demonstrate it | Evidence in repo |
|---|---|---|
| Generative AI / LLM apps | Weeks 1-2 | Structured triage, provider abstraction |
| Open-weight LLMs | Weeks 1-2, 5 | gpt-oss via Groq, Gemini fallback, model comparison table |
| Prompt Engineering | Week 2, 4 | Versioned prompts, `prompt-experiments.md` |
| RAG | Weeks 3-4 | Pipeline, citations, retrieval + faithfulness metrics |
| Embeddings / vector DBs | Week 3 | Chroma index, duplicate detection |
| Tool calling | Week 5 | Tool schemas, tool-selection tests |
| AI Agents | Weeks 5-6 | Plain loop vs LangGraph comparison |
| AI automation workflows | Weeks 6-7 | Webhook → agent → approval → action |
| AI-based solutions (end to end) | Weeks 7-8 | Deployed API + extension + demo |
| Evaluation / reliability | Weeks 2, 4, 7 | Eval sets, CI evals, failure cases |

---

## 9. Scope Control

**If you fall behind, cut in this order:**

1. Extended extension features (Week 9): time-to-close card first, then stats popup, then resolution card, then new-issue banner
2. `search_code()` tool
3. Qdrant swap (stay on Chroma)
4. Re-ranking / hybrid search experiments
5. Extension MVP polish (keep the minimal sidebar)
6. Second repo / stretch data

**Never cut:** prompt experiments, RAG evaluation, the human-approval gate, and documentation. These are what make the project credible.

**Optional stretch goals (only after Week 8):**

- Fine-tune a small classifier (e.g. DistilBERT) and compare to TF-IDF and the LLM
- Multi-repo support
- Time-to-close estimator (also feeds the optional extended extension card)
- Simple feedback loop: store approve/reject decisions and use them to improve prompts

**Explicitly out of scope:** multi-agent systems, paid infrastructure, large local models.

---

## 10. Definition of Done

- [ ] Triage works end-to-end: issue → structured recommendation with cited evidence
- [ ] RAG evaluated with retrieval and faithfulness metrics, documented
- [ ] Agent uses tools and runs in LangGraph, with step limits
- [ ] Webhook-triggered automation, with **no repository action without human approval**
- [ ] API containerized, deployed, and logged
- [ ] CI runs tests and a small eval suite
- [ ] Chrome extension **MVP** shows triage results with Approve / Reject on GitHub issue pages
- [ ] (Extended, optional) New-issue banner, resolution card, and stats popup working
- [ ] README with architecture diagram, setup steps, and demo video
- [ ] `docs/` includes design decisions, prompt experiments, RAG evaluation, failure cases, limitations
- [ ] No secrets committed; `.env.example` provided

---

## 11. Weekly Routine

- **Start of each weekday:** read that day's task, define "done" in one line.
- **End of each weekday:** commit, write 2-3 lines in `learning-log.md`.
- **Every Sunday (last 30 min):** review the checkpoint, update this file's checkboxes, and decide whether any scope needs to be cut.

---

## 12. Resume Bullets (Draft These at the End of Week 8)

- Built an AI-powered GitHub issue triage copilot using open-weight LLMs (gpt-oss via Groq, Gemini fallback), RAG over issues/docs, and a LangGraph tool-calling agent, with human-in-the-loop approval before any repository action.
- Evaluated RAG with retrieval (hit@k, MRR) and faithfulness metrics; improved retrieval and reduced hallucinations through prompt and chunking experiments.
- Automated issue triage via GitHub webhooks, FastAPI, and Docker; shipped a Chrome extension that surfaces classification, similar issues, and recommended actions inside GitHub.