## 2026-10-17 — GitHub API: Pagination and Rate Limits

- **What it is:** Pagination is a technique for retrieving API results in smaller batches instead of fetching everything in one request. GitHub's REST API supports parameters such as `per_page` and `page`. Rate limits restrict how many API requests can be made within a given time window. Authenticated requests generally have a higher primary rate limit than unauthenticated requests.
Rate limit is not: 1 issue = 1 limit
Rate limit is: 1 API hit = 1 limit [now one can ask 100 or 200 issues in one page/hit (called pagination) and only 1 limit will be consumed]

- **Why I used it:** I used the GitHub REST API to fetch the latest five results from the Flask repository's issues endpoint using `per_page=5` and `state=all`. I loaded my GitHub personal access token using `python-dotenv`, sent it through the `Authorization` header, checked the response with `raise_for_status()`, and printed each issue's number, title, state, and labels. I also inspected `X-RateLimit-Remaining` to verify the remaining API quota. This establishes the foundation for retrieving and processing GitHub issues in Triagent.

- **Trade-offs / what surprised me:** Fetching a small batch makes testing easier and reduces unnecessary data transfer, but retrieving all issues requires pagination and multiple requests. Authentication increases the primary rate limit, but it does not eliminate rate limits. I also learned that an API request can succeed while returning only a subset of the available results. Therefore, I need to handle pagination, HTTP errors, and rate-limit headers when building a reliable ingestion pipeline.

- **Stretch repo**: facebook/react - far more issues and labels; would stress-test rate limits and duplicate detection. Not fetched.

## 2026-10-17 — Fetched Repo Exploratiion and Switching

- Flask looked good (small, well documented) but was 87% unlabeled. I checked label coverage with the Postman before committing and switched to pytest.

- Pytest had substantially more issues and well documented and labelled issue hence the switch

- **Why I used it:** to download 6,421 pytest issues and their comments reliably, following the `next` link, sleeping when the limit is low, and checkpointing so a crash resumes instead of restarting.

- **Trade-offs / what surprised me:** the issues endpoint also returns PRs, so they must be filtered. The repo-wide comments endpoint silently capped at 30,000 items, and I only caught it by comparing totals against the issues' comment counts.

## Reminders
- Create the sandbox repo (with realistic dummy issues) before Week 6 Day 6.