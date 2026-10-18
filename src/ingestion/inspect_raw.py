import json
import random
import re
from collections import Counter
from pathlib import Path

RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / "pytest-dev__pytest"

issues = [json.loads(l) for l in open(RAW / "issues.jsonl", encoding="utf-8") if l.strip()]
by_number = {i["number"]: i for i in issues}

SHOW_SAMPLES = False  # you've already seen 8 samples; set True to see more


def body_of(issue):
    """Body with Windows line endings normalized; empty string if None."""
    return (issue["body"] or "").replace("\r\n", "\n")


# 1. Every distinct label
labels = Counter(l["name"] for i in issues for l in i["labels"])
print(f"{len(labels)} distinct labels")
for name, n in sorted(labels.items()):
    print(f"{n:5d}  {name!r}")

# 2. How many "type:" labels does each issue carry?
combo_counts = Counter()
for issue in issues:
    types = sorted(l["name"] for l in issue["labels"] if l["name"].startswith("type: "))
    combo_counts[tuple(types)] += 1

print("\n--- type: label combinations ---")
print("0 type labels:", combo_counts[()])
print("exactly 1:", sum(n for c, n in combo_counts.items() if len(c) == 1))
print("2 or more:", sum(n for c, n in combo_counts.items() if len(c) >= 2))
for combo, n in combo_counts.most_common(25):
    print(f"{n:5d}  {combo}")

# 3. Noise frequency
patterns = {
    "html comment <!--": r"<!--",
    "code fence ```": r"```",
    "traceback": r"Traceback \(most recent call last\)",
    "markdown image ![": r"!\[",
    "checkbox - [ ]": r"- \[[ xX]\]",
    "html tag": r"<[a-zA-Z/][^>]*>",
    "url": r"https?://",
    "\\r\\n line endings": r"\r\n",
}
print("\n--- Noise frequency (issues containing pattern) ---")
for name, pat in patterns.items():
    n = sum(1 for i in issues if i["body"] and re.search(pat, i["body"]))
    print(f"{n:5d}  {name}")

# 4. Bitbucket migration wrapper
header = sum(1 for i in issues if (i["body"] or "").startswith("Originally reported by"))
footer = sum(1 for i in issues if "- Bitbucket: https://bitbucket.org" in (i["body"] or ""))
print("\n--- Bitbucket wrapper ---")
print("header:", header, "| footer:", footer)

# 5. Are the glued words ("facilityI", "notthe") really in the data?
print("\n--- repr of issue 4234 (hidden characters visible) ---")
print(repr(by_number[4234]["body"][:250]))

# 6. One checkbox example, with context
print("\n--- Checkbox example ---")
for i in issues:
    body = body_of(i)
    m = re.search(r"- \[[ xX]\]", body)
    if m:
        print("issue", i["number"])
        print(body[max(0, m.start() - 200): m.start() + 400])
        break

# 7. Optional random samples
if SHOW_SAMPLES:
    random.seed(7)
    for i in random.sample(issues, 8):
        print("=" * 70)
        print(i["number"], "|", i["title"])
        print("labels:", [l["name"] for l in i["labels"]])
        print(body_of(i)[:700])


# 8. Proposal-only issues: feature request or something else?
proposal_only = [
    i for i in issues
    if sorted(l["name"] for l in i["labels"] if l["name"].startswith("type: ")) == ["type: proposal"]
]
print(f"\n--- {len(proposal_only)} proposal-only issues; random 15 ---")
random.seed(11)
for i in random.sample(proposal_only, 15):
    print(i["number"], "|", i["title"])
    print("   ", body_of(i)[:250].replace("\n", " "))


# 9. Category distribution using labels.py
from labels import category_from_labels

cat_counts = Counter(
    category_from_labels([l["name"] for l in i["labels"]]) for i in issues
)
print("\n--- Category distribution ---")
for cat, n in cat_counts.most_common():
    print(f"{n:5d}  {cat}")


# 10. Raw Bitbucket wrapper text (repr shows hidden characters)
print("\n--- Bitbucket wrapper, raw ---")
for n in (396, 594):
    body = by_number[n]["body"]
    print(n, "HEADER:", repr(body[:230]))
    print(n, "FOOTER:", repr(body[-130:]))

# Header/footer variants: do they all look the same?
hdr = Counter()
ftr = Counter()
for i in issues:
    b = body_of(i)
    if b.startswith("Originally reported by"):
        hdr[re.sub(r"\[[^\]]*\]\([^)]*\)", "[X](url)", b.split("\n")[0])] += 1
    if "- Bitbucket: https://bitbucket.org" in b:
        ftr[re.sub(r"\d+$", "N", b.rstrip().split("\n")[-1])] += 1
print("header first-line shapes:", hdr.most_common(5))
print("footer last-line shapes:", ftr.most_common(5))


# 11. Before/after on real issues
from clean_text import clean_body

random.seed(3)
for i in random.sample(issues, 3):
    print("=" * 70, i["number"])
    print("BEFORE:", repr((i["body"] or "")[:400]))
    print("AFTER: ", repr(clean_body(i["body"])[:400]))

# The 4 odd Bitbucket footers
for i in issues:
    b = body_of(i)
    if "- Bitbucket: https://bitbucket.org" in b and not b.rstrip().endswith(b.rstrip().split("\n")[-1]) or (
        "- Bitbucket: https://bitbucket.org" in b and "Bitbucket: https://bitbucket.org" in clean_body(i["body"])
    ):
        print("FOOTER SURVIVED in", i["number"])


# 12. Footers that survived cleaning
for n in (456, 519, 611):
    raw = body_of(by_number[n])
    print("=" * 70, n)
    print("fence count (``` occurrences):", raw.count("```"))
    print("RAW TAIL:    ", repr(raw[-300:]))
    print("CLEANED TAIL:", repr(clean_body(by_number[n]["body"])[-300:]))

# 13. Targeted before/after: issues that contain a traceback or code
picked = [i for i in issues if "```" in (i["body"] or "") and "Traceback" in (i["body"] or "")][:2]
for i in picked:
    print("=" * 70, i["number"])
    print("BEFORE:", repr(body_of(i)[:500]))
    print("AFTER: ", repr(clean_body(i["body"])[:500]))


# 14. Day 3 follow-ups
from clean_text import CODE_FENCE, clean_body, mark_block, normalize_newlines

# 14a. Issue 9201: which block went missing, and why?
raw = normalize_newlines(by_number[9201]["body"] or "")
cleaned = clean_body(by_number[9201]["body"])
print("\n--- 9201 ---")
print("'@@CODE' appears in raw body:", "@@CODE" in raw)
for block in CODE_FENCE.findall(raw):
    marked = mark_block(block)
    if marked not in cleaned:
        print("MISSING BLOCK:", repr(marked[:300]))

# 14b. The 31 empty bodies
empty = [i for i in issues if not clean_body(i["body"])]
raw_blank = [i for i in empty if not (i["body"] or "").strip()]
print(f"\n--- {len(empty)} empty after cleaning; {len(raw_blank)} were already blank in raw ---")
for i in empty:
    if i not in raw_blank:
        print(i["number"], repr((i["body"] or "")[:200]))

# 14c. Odd-fence issues: what does the stray fence look like?
odd = [i for i in issues if body_of(i).count("```") % 2]
print("\n--- odd fences, first 3 ---")
for i in odd[:3]:
    print(i["number"], [ln[:80] for ln in body_of(i).split("\n") if "```" in ln])