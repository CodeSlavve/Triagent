
import argparse
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

parser = argparse.ArgumentParser()
parser.add_argument("--repo", default="pytest-dev/pytest")
parser.add_argument("--limit", type=int, default=None)
args = parser.parse_args()

REPO = args.repo

# 1. Configuration
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "raw" / REPO.replace("/", "__")
OUTPUT_FILE = DATA_DIR / "issues.jsonl"
CHECKPOINT_FILE = OUTPUT_FILE.with_suffix(".checkpoint.json")

API_URL = f"https://api.github.com/repos/{REPO}/issues"

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
    "state": "all",
    "per_page": 100,
    "sort": "created",
    "direction": "asc",
}


def load_saved_issues():
    """Load existing issue numbers to prevent duplicates."""
    saved_numbers = set()

    if OUTPUT_FILE.exists():
        with OUTPUT_FILE.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue

                issue = json.loads(line)
                saved_numbers.add(issue["number"])

    return saved_numbers


def load_checkpoint():
    """Return the next page URL saved from the previous run."""
    if CHECKPOINT_FILE.exists():
        with CHECKPOINT_FILE.open("r", encoding="utf-8") as file:
            return json.load(file).get("next_url")

    # Build the initial URL with its query parameters included.
    request = requests.Request(
        "GET",
        API_URL,
        params=PARAMS,
    ).prepare()

    return request.url


def save_checkpoint(next_url):
    """Persist the next page URL safely."""
    temp_file = CHECKPOINT_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as file:
        json.dump({"next_url": next_url}, file)

    temp_file.replace(CHECKPOINT_FILE)


def fetch_issues(limit):
    """Fetch issues and append new records until the target is reached."""
    limit = limit if limit else float("inf")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    saved_numbers = load_saved_issues()
    saved_count = len(saved_numbers)

    print(f"Existing issues: {saved_count}")
    print(f"Target dataset size: {limit}")

    if saved_count >= limit:
        print("Target already reached. Nothing to fetch.")
        return

    next_url = load_checkpoint()
    new_count = 0
    skipped_prs = 0

    # Append instead of deleting existing data.
    with OUTPUT_FILE.open("a", encoding="utf-8") as file:
        with requests.Session() as session:
            while next_url and saved_count < limit:
                current_url = next_url

                response = session.get(
                    current_url,
                    headers=HEADERS,
                    timeout=30,
                )

                response.raise_for_status()

                page_next_url = response.links.get("next", {}).get("url")

                items = response.json()

                for issue in items:
                    # The endpoint includes pull requests too.
                    if "pull_request" in issue:
                        skipped_prs += 1
                        continue

                    issue_number = issue["number"]

                    # Avoid writing an issue we already have.
                    if issue_number in saved_numbers:
                        continue

                    file.write(
                        json.dumps(issue, ensure_ascii=False) + "\n"
                    )
                    file.flush()

                    saved_numbers.add(issue_number)
                    saved_count += 1
                    new_count += 1

                # If we hit the target mid-page, revisit this page on resume.
                # Existing issue numbers will be skipped.
                if saved_count >= limit:
                    save_checkpoint(current_url)
                    next_url = current_url
                    break

                # The current page was processed completely.
                next_url = page_next_url
                save_checkpoint(next_url)

                if next_url is None:
                    print("No more pages available.")
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
                    f"PRs skipped: {skipped_prs} | "
                    f"Rate limit remaining: {remaining}"
                )

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
    print(f"Total unique issues saved: {saved_count}")
    print(f"New issues this run: {new_count}")
    print(f"Output file: {OUTPUT_FILE}")


if __name__ == "__main__":
    if args.limit is not None and args.limit < 1:
       parser.error("--limit must be at least 1")
    fetch_issues(args.limit)