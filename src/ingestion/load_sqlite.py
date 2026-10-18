import argparse
import json
import sqlite3
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--repo", default="pytest-dev/pytest")
args = parser.parse_args()

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "data" / "processed" / args.repo.replace("/", "__")
DB_PATH = ROOT / "data" / "triagent.db"

# Children are dropped before the parent so foreign keys never block a drop.
SCHEMA = """
DROP TABLE IF EXISTS comments;
DROP TABLE IF EXISTS labels;
DROP TABLE IF EXISTS issues;

CREATE TABLE issues (
    number         INTEGER PRIMARY KEY,
    title          TEXT NOT NULL,
    body           TEXT NOT NULL,
    state          TEXT NOT NULL,
    category       TEXT,                 -- NULL = no type label; 'ambiguous' stored as text
    created_at     TEXT NOT NULL,
    closed_at      TEXT,
    url            TEXT NOT NULL,
    author_is_bot  INTEGER NOT NULL,     -- 0 / 1
    comment_count  INTEGER NOT NULL      -- GitHub's number, not rows we hold
);

CREATE TABLE comments (
    id            INTEGER PRIMARY KEY,
    issue_number  INTEGER NOT NULL REFERENCES issues(number),
    body          TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    url           TEXT NOT NULL,
    is_bot        INTEGER NOT NULL
);
CREATE INDEX idx_comments_issue ON comments(issue_number);

CREATE TABLE labels (
    issue_number  INTEGER NOT NULL REFERENCES issues(number),
    label         TEXT NOT NULL,
    PRIMARY KEY (issue_number, label)
);
CREATE INDEX idx_labels_label ON labels(label);
"""


def read_jsonl(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


issues = read_jsonl(CLEAN / "issues_clean.jsonl")
comments = read_jsonl(CLEAN / "comments_clean.jsonl")

# Tuples in the same column order as the CREATE TABLE statements above.
issue_rows = [
    (i["number"], i["title"], i["body"], i["state"], i["category"],
     i["created_at"], i["closed_at"], i["url"],
     int(i["author_is_bot"]), i["comment_count"])
    for i in issues
]

# A set removes duplicate (issue, label) pairs; sorted() makes the load deterministic.
label_rows = sorted({(i["number"], l.strip()) for i in issues for l in i["labels"]})

issue_numbers = {i["number"] for i in issues}
comment_rows = []
skipped_orphans = 0
for c in comments:
    if c["issue_number"] not in issue_numbers:
        skipped_orphans += 1
        continue
    comment_rows.append(
        (c["id"], c["issue_number"], c["body"], c["created_at"], c["url"], int(c["is_bot"]))
    )

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")   # SQLite ignores foreign keys unless this is set
conn.executescript(SCHEMA)

with conn:  # one transaction: commits if everything succeeds, rolls back on error
    conn.executemany("INSERT INTO issues VALUES (?,?,?,?,?,?,?,?,?,?)", issue_rows)
    conn.executemany("INSERT INTO labels VALUES (?,?)", label_rows)
    conn.executemany("INSERT INTO comments VALUES (?,?,?,?,?,?)", comment_rows)


def scalar(sql):
    return conn.execute(sql).fetchone()[0]


print(f"DB: {DB_PATH}")
print("issues:", scalar("SELECT COUNT(*) FROM issues"), "| expected", len(issues))
print("comments:", scalar("SELECT COUNT(*) FROM comments"), "| expected", len(comments))
print("label rows:", scalar("SELECT COUNT(*) FROM labels"))
print("comments skipped (issue not in dataset):", skipped_orphans)
print("orphan comments:", scalar(
    "SELECT COUNT(*) FROM comments c LEFT JOIN issues i ON i.number = c.issue_number "
    "WHERE i.number IS NULL"))
print("foreign key violations:", len(conn.execute("PRAGMA foreign_key_check").fetchall()))
print("issues with fewer saved comments than GitHub reports:", scalar(
    "SELECT COUNT(*) FROM issues i WHERE "
    "(SELECT COUNT(*) FROM comments c WHERE c.issue_number = i.number) < i.comment_count"))
print("usable for classifier (labeled, not ambiguous):", scalar(
    "SELECT COUNT(*) FROM issues WHERE category IS NOT NULL AND category != 'ambiguous'"))
print("\ncategory distribution:")
for cat, n in conn.execute(
    "SELECT COALESCE(category, 'NULL'), COUNT(*) FROM issues GROUP BY 1 ORDER BY 2 DESC"
):
    print(f"{n:6d}  {cat}")

conn.close()