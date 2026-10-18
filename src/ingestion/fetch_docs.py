import argparse
import io
import sqlite3
import zipfile
from pathlib import Path

import requests

parser = argparse.ArgumentParser()
parser.add_argument("--repo", default="pytest-dev/pytest")
parser.add_argument("--branch", default="main")
args = parser.parse_args()

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "triagent.db"
ARCHIVE_URL = f"https://github.com/{args.repo}/archive/refs/heads/{args.branch}.zip"
BLOB_URL = f"https://github.com/{args.repo}/blob/{args.branch}/"

SCHEMA = """
DROP TABLE IF EXISTS docs;
CREATE TABLE docs (
    path     TEXT PRIMARY KEY,
    url      TEXT NOT NULL,
    title    TEXT,
    content  TEXT NOT NULL
);
"""

PUNCT = set("=-~^\"'`#*+._:")


def is_rule(s):
    """True for a reStructuredText heading underline such as ======"""
    return len(s) >= 3 and set(s) <= PUNCT


def extract_title(text):
    """First reST heading: a text line followed by an underline at least as long."""
    lines = text.split("\n")
    for i in range(len(lines) - 1):
        line = lines[i].strip()
        nxt = lines[i + 1].strip()
        if not line or set(line) <= PUNCT:   # skip blanks and overlines
            continue
        if is_rule(nxt) and len(nxt) >= len(line):
            return line
    return None


def wanted(path):
    if path in ("README.rst", "CONTRIBUTING.rst"):
        return True
    return path.startswith("doc/en/") and path.endswith(".rst")


print("Downloading", ARCHIVE_URL)
resp = requests.get(ARCHIVE_URL, timeout=120)
resp.raise_for_status()

rows = []
with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
    for name in zf.namelist():
        parts = name.split("/", 1)          # first folder is "<repo>-<branch>/"
        if len(parts) < 2:
            continue
        path = parts[1]
        if not wanted(path):
            continue
        text = zf.read(name).decode("utf-8", errors="replace").replace("\r\n", "\n").strip()
        if not text:
            continue
        rows.append((path, BLOB_URL + path, extract_title(text), text))

conn = sqlite3.connect(DB_PATH)
conn.executescript(SCHEMA)
with conn:
    conn.executemany("INSERT INTO docs VALUES (?,?,?,?)", rows)

print("docs pages loaded:", len(rows))
print("total characters:", sum(len(r[3]) for r in rows))
print("pages with no title found:", sum(1 for r in rows if r[2] is None))
print("\nlargest pages:")
for path, n in conn.execute(
    "SELECT path, LENGTH(content) FROM docs ORDER BY 2 DESC LIMIT 5"
):
    print(f"{n:8d}  {path}")
print("\nsample:")
for path, title in conn.execute(
    "SELECT path, title FROM docs WHERE path LIKE 'doc/en/how-to/%' LIMIT 5"
):
    print(f"  {path} | {title}")
conn.close()