import argparse
import requests
import os
import json
import time

from pathlib import Path
from dotenv import load_dotenv

parser = argparse.ArgumentParser()
parser.add_argument("--repo", default="pytest-dev/pytest")
parser.add_argument("--since", default=None)
parser.add_argument("--limit", type=int, default=None)
args = parser.parse_args()

REPO = args.repo

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "raw" / REPO.replace("/", "__")
ISSUES_FILE = DATA_DIR / "issues.jsonl"
OUTPUT_FILE = DATA_DIR / "comments.jsonl"
CHECKPOINT_FILE = OUTPUT_FILE.with_suffix(".checkpoint.json")

API_URL = f"https://api.github.com/repos/{REPO}/issues/comments"

load_dotenv(PROJECT_ROOT / ".env")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError(
        "GITHUB_TOKEN is missing. Add it to the project root .env file."
    )

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

PARAMS = {
    "per_page": 100,
    "sort": "created",
    "direction": "asc",
}


def oldest_issue_date():
    oldest = None
    with ISSUES_FILE.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d = json.loads(line)["created_at"]
                if oldest is None or d < oldest:
                    oldest = d
    return oldest

PARAMS["since"] = args.since or oldest_issue_date()


def load_issue_numbers():
    """Numbers of the real issues we saved (PRs are not in this set)."""
    if not ISSUES_FILE.exists():
        raise FileNotFoundError(
            f"{ISSUES_FILE} not found. Run fetch_issues.py first."
        )

    numbers = set()
    with ISSUES_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            try:
                numbers.add(json.loads(line)["number"])
            except json.JSONDecodeError:
                continue
    return numbers


def load_saved_comment_ids():
    """Load existing comment ids to prevent duplicates."""
    saved_ids = set()

    if OUTPUT_FILE.exists():
        with OUTPUT_FILE.open("r", encoding = "utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                try:
                    saved_ids.add(json.loads(line)["id"])
                except json.JSONDecodeError:
                    # Partial last line from an interrupted run.
                    continue

    return saved_ids


def load_checkpoint():
    """Return the next page URL saved from previous run."""
    if CHECKPOINT_FILE.exists():
        with CHECKPOINT_FILE.open("r", encoding="utf-8") as file:
            return json.load(file).get("next_url")

    request = requests.Request(
        "GET",
        API_URL,
        params= PARAMS,
    ).prepare()

    return request.url


def save_checkpoint(next_url):
    """Persist the next page URL safely."""
    temp_file = CHECKPOINT_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as file:
        json.dump({"next_url": next_url}, file)

    temp_file.replace(CHECKPOINT_FILE)


def fetch_comments(limit):
    """Fetch comments and append new records until the target is reached."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    issue_numbers = load_issue_numbers()
    saved_ids = load_saved_comment_ids()
    saved_count = len(saved_ids)

    print(f"Issues in dataset: {len(issue_numbers)}")
    print(f"Existing comments: {saved_count}")
    print(f"Limit: {limit if limit else 'none'}")

    if limit and saved_count >= limit:
        print("Limit already reached. Nothing to fetch.")
        return

    next_url = load_checkpoint()
    new_count = 0
    skipped_pr_comments = 0

    # Append instead of deleting existing data.
    with OUTPUT_FILE.open("a", encoding="utf-8") as file:
        with requests.Session() as session:
            while next_url and not (limit and saved_count >= limit):
                current_url = next_url

                response = session.get(
                    current_url,
                    headers=HEADERS,
                    timeout=30,
                )

                response.raise_for_status()

                page_next_url = response.links.get("next", {}).get("url")

                items = response.json()

                for comment in items:
                    # issue_url ends with the issue/PR number.
                    issue_number = int(
                        comment["issue_url"].rsplit("/", 1)[-1]
                    )

                    # Comments on PRs (or unsaved issues) are skipped.
                    if issue_number not in issue_numbers:
                        skipped_pr_comments += 1
                        continue

                    if comment["id"] in saved_ids:
                        continue

                    file.write(
                        json.dumps(comment, ensure_ascii=False) + "\n"
                    )
                    file.flush()

                    saved_ids.add(comment["id"])
                    saved_count += 1
                    new_count += 1

                    if limit and saved_count >= limit:
                        break

                remaining = int(
                    response.headers.get("X-RateLimit-Remaining", 0)
                )
                reset_at = int(
                    response.headers.get("X-RateLimit-Reset", 0)
                )

                print(
                    f"Total saved: {saved_count}/{limit} | "
                    f"New this run: {new_count} | "
                    f"PR comments skipped: {skipped_pr_comments} | "
                    f"Rate limit remaining: {remaining}"
                )

                # Hit the limit mid-page: revisit this page on resume.
                # Saved comment ids are skipped, so this is safe.
                if limit and saved_count >= limit:
                    save_checkpoint(current_url)
                    break

                # Page fully processed.
                next_url = page_next_url
                save_checkpoint(next_url)

                if next_url is None:
                    print("No more pages available.")
                    break

                # Sleep until GitHub's primary rate-limit reset.
                if remaining < 50:
                    wait_seconds = max(
                        0, reset_at - int(time.time())
                    )

                    if wait_seconds > 0:
                        print(
                            f"Rate limit low. "
                            f"Sleeping for {wait_seconds + 1} seconds."
                        )
                        time.sleep(wait_seconds + 1)

    print("\nFetch finished.")
    print(f"Total comments saved: {saved_count}")
    print(f"New comments this run: {new_count}")
    print(f"Output file: {OUTPUT_FILE}")


if __name__ == "__main__":
    if args.limit is not None and args.limit < 1:
       parser.error("--limit must be at least 1")
    fetch_comments(args.limit)