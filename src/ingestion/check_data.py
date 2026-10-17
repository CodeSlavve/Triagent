import json
from collections import Counter
from pathlib import Path

RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / "pytest-dev__pytest"

issues = [json.loads(l) for l in open(RAW / "issues.jsonl", encoding="utf-8") if l.strip()]
comments = [json.loads(l) for l in open(RAW / "comments.jsonl", encoding="utf-8") if l.strip()]

print("issues:", len(issues))
print("comments:", len(comments), "| sum of issue 'comments' fields:", sum(i["comments"] for i in issues))

labels = Counter()
unlabeled = 0
for i in issues:
    names = [l["name"] for l in i["labels"]]
    if not names:
        unlabeled += 1
    labels.update(names)
print("unlabeled issues:", unlabeled)
print("top labels:", labels.most_common(20))

print("null/empty issue bodies:", sum(1 for i in issues if not i["body"]))
print("bot-authored issues:", sum(1 for i in issues if i["user"]["type"] == "Bot"))
print("bot comments:", sum(1 for c in comments if c["user"]["type"] == "Bot"))
print("empty comment bodies:", sum(1 for c in comments if not c["body"]))

from collections import Counter
got = Counter(int(c["issue_url"].rsplit("/", 1)[-1]) for c in comments)
short = [(i["number"], i["created_at"][:10], i["comments"], got.get(i["number"], 0))
         for i in issues if got.get(i["number"], 0) < i["comments"]]
print("issues missing comments:", len(short))
print("first 5:", short[:5])
print("last 5:", short[-5:])
print("latest comment saved:", max(c["created_at"] for c in comments))