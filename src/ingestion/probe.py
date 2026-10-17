import os

import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise RuntimeError(
        "GITHUB_TOKEN is missing. Add it to your root .env file."
    )

url = "https://api.github.com/repos/pallets/flask/issues"

params = {
    "state" : "all",
    "per_page" : 5,
}

headers = {
    "Authorization" : f"Bearer {GITHUB_TOKEN}",
    "Accept" : "application/vnd.github+json",
}

resp = requests.get(
    url,
    params = params,
    headers=headers,
    timeout=30,
)

resp.raise_for_status()

issues = resp.json()

for issue in issues:
    labels = [label["name"] for label in issue['labels']]

    print(f"Number: {issue['number']}")
    print(f"Title: {issue['title']}")
    print(f"State: {issue['state']}")
    print(f"Labels: {', '.join(labels) if labels else 'None'}")
    print("-" * 50)

print(
    "X-RateLimit-Remaining:",
    resp.headers.get("X-RateLimit-Remaining", "Unavailable"),
)