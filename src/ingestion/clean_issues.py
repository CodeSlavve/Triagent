import argparse
import json
from pathlib import Path

from clean_text import CODE_FENCE, clean_body, mark_block, normalize_newlines
from labels import category_from_labels

parser = argparse.ArgumentParser()
parser.add_argument("--repo", default="pytest-dev/pytest")
args = parser.parse_args()

ROOT = Path(__file__).resolve().parents[2]
SLUG = args.repo.replace("/", "__")
RAW = ROOT / "data" / "raw" / SLUG
OUT = ROOT / "data" / "processed" / SLUG
OUT.mkdir(parents=True, exist_ok=True)


def read_jsonl(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    # "w" overwrites: the script is re-runnable from scratch, raw data is never touched.
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def is_bot(obj):
    # user can be null for deleted accounts
    return (obj.get("user") or {}).get("type") == "Bot"


def clean_issue(issue):
    label_names = [l["name"] for l in issue["labels"]]
    return {
        "number": issue["number"],
        "title": (issue["title"] or "").strip(),
        "body": clean_body(issue["body"]),
        "state": issue["state"],
        "labels": label_names,
        "category": category_from_labels(label_names),
        "created_at": issue["created_at"],
        "closed_at": issue["closed_at"],
        "url": issue["html_url"],
        "author_is_bot": is_bot(issue),
        "comment_count": issue["comments"],
    }


def clean_comment(comment):
    return {
        "id": comment["id"],
        "issue_number": int(comment["issue_url"].rsplit("/", 1)[-1]),
        "body": clean_body(comment["body"]),
        "created_at": comment["created_at"],
        "url": comment["html_url"],
        "is_bot": is_bot(comment),
    }


raw_issues = read_jsonl(RAW / "issues.jsonl")
raw_comments = read_jsonl(RAW / "comments.jsonl")

issues = [clean_issue(i) for i in raw_issues]
comments = [clean_comment(c) for c in raw_comments]

write_jsonl(OUT / "issues_clean.jsonl", issues)
write_jsonl(OUT / "comments_clean.jsonl", comments)

# ---- Checks ----
print(f"issues written: {len(issues)} | comments written: {len(comments)}")
print("empty issue bodies after cleaning:", sum(1 for r in issues if not r["body"]))
print("empty comment bodies after cleaning:", sum(1 for r in comments if not r["body"]))

odd_fences = sum(
    1 for i in raw_issues if normalize_newlines(i["body"] or "").count("```") % 2
)
print("issue bodies with an odd number of ``` fences:", odd_fences)

# Invariant: every code block in the raw text must survive, intact, in the cleaned text.
lost = []
for raw, clean in zip(raw_issues, issues):
    text = normalize_newlines(raw["body"] or "")
    for block in CODE_FENCE.findall(text):
        if mark_block(block) not in clean["body"]:
            lost.append(raw["number"])
            break
print("issues where a code block was altered or lost:", len(lost), lost[:10])