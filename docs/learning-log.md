## 2026-10-17 — GitHub API: Pagination and Rate Limits

- **What it is:** Pagination is a technique for retrieving API results in smaller batches instead of fetching everything in one request. GitHub's REST API supports parameters such as `per_page` and `page`. Rate limits restrict how many API requests can be made within a given time window. Authenticated requests generally have a higher primary rate limit than unauthenticated requests.
Rate limit is not: 1 issue = 1 limit
Rate limit is: 1 API hit = 1 limit [now one can ask 100 or 200 issues in one page/hit (called pagination) and only 1 limit will be consumed]

- **Why I used it:** I used the GitHub REST API to fetch the latest five results from the Flask repository's issues endpoint using `per_page=5` and `state=all`. I loaded my GitHub personal access token using `python-dotenv`, sent it through the `Authorization` header, checked the response with `raise_for_status()`, and printed each issue's number, title, state, and labels. I also inspected `X-RateLimit-Remaining` to verify the remaining API quota. This establishes the foundation for retrieving and processing GitHub issues in Triagent.

- **Trade-offs / what surprised me:** Fetching a small batch makes testing easier and reduces unnecessary data transfer, but retrieving all issues requires pagination and multiple requests. Authentication increases the primary rate limit, but it does not eliminate rate limits. I also learned that an API request can succeed while returning only a subset of the available results. Therefore, I need to handle pagination, HTTP errors, and rate-limit headers when building a reliable ingestion pipeline.

- **Stretch repo**: facebook/react - far more issues and labels; would stress-test rate limits and duplicate detection. Not fetched.

## 2026-10-17 — Fetched Repo Exploration and Switching

- Flask looked good (small, well documented) but was 87% unlabeled. I checked label coverage with the Postman before committing and switched to pytest.

- Pytest had substantially more issues and well documented and labelled issue hence the switch. (Correction, 2026-10-18: 77% of pytest issues have some label, but only 65% have a `type:` label, which is what the classifier actually needs.)

- **Why I used it:** to download 6,421 pytest issues and their comments reliably, following the `next` link, sleeping when the limit is low, and checkpointing so a crash resumes instead of restarting.

- **Trade-offs / what surprised me:** the issues endpoint also returns PRs, so they must be filtered. The repo-wide comments endpoint silently capped at 30,000 items, and I only caught it by comparing totals against the issues' comment counts.

## 2026-10-18 — Cleaning GitHub issue data and building the label ground truth

- **What it is:** Data cleaning turns raw issue text into something models can use: removing template boilerplate (Bitbucket migration header/footer, HTML comments), keeping code and tracebacks but marking them [CODE]/[TRACEBACK], and mapping GitHub labels to a small category set (bug / feature / docs / question / other).

- **Why I did it this way:** I inspected the data before writing rules (label list, noise counts, random samples). Code blocks are swapped for placeholders before cleaning and restored afterwards, so no regex can damage code. Only `type:` labels define the category; plugin/topic/status labels describe something else. Issues with no type label get None and conflicting ones get "ambiguous", so I never invent ground truth. Every later metric (classifier accuracy, prompt comparison) is scored against these categories, so this mapping is the base of the project's evaluation.

- **Trade-offs / what surprised me:** 35% of issues have no type label, so my earlier "77% labeled" figure was misleading. The class split is bug 37%, feature 28%, question 18%, other 10%, docs 8%, so a classifier that always says "bug" scores about 37%; that is the baseline to beat. Some label choices are judgement calls (proposal as feature, based on a 15-issue sample). A generic HTML-tag stripper would have deleted pytest output like `<Module test_x.py>`, so I only remove specific tags. A check that every raw code block survives cleaning found 1 failure in 6,421 issues. I also learned not to trust pasted terminal output for whitespace.

- **Python concepts practiced:** set operations (`&`, `discard`), regex (non-greedy, `DOTALL`, `re.sub` with a function), writing assert tests for each rule, and the bug where `and` is not the same as `&`.

## 2026-10-18 — SQLite storage for issues, comments, labels and docs

- **What it is:** SQLite is a database stored in a single file. Tables are linked by keys: each comment stores the number of the issue it belongs to (a foreign key), and labels sit in their own table with one row per issue-label pair.
- **Why I used it:** later stages (embeddings, RAG, tools) need queries like "all comments for issue X" or "all closed issues with label Y", which are one `SELECT` in SQLite but a full file scan in JSONL. The load runs in one transaction, and the row counts, orphan check, foreign key check and category counts all matched the Day 3 numbers, so I know the load is correct.
- **Trade-offs / what surprised me:** SQLite ignores foreign keys unless `PRAGMA foreign_keys = ON` is set on each connection. Keys use the issue number alone, so a second repo later would need a `repo` column and a migration. I got the docs from one zip download instead of hundreds of API calls. Two docs files (plugin list, changelog) make up about 65% of the docs text and will need excluding from retrieval.

## Reminders
- Create the sandbox repo (with realistic dummy issues) before Week 6 Day 6.