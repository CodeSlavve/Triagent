## 2026-10-17 - Flask labels unusable for classification
- What happened: 2,403 of 2,766 issues (87%) had no label; no feature/enhancement/question labels existed.
- Impact: TF-IDF classifier had no usable training target.
- Action: switched primary repo to pytest-dev/pytest (77% have some label, 760 question / 1,418 bug).
- Correction (2026-10-18): the 77% counts any label (plugin/topic/status included). Only 65% of pytest issues have a `type:` label; see the entry below.

## 2026-10-17 - Comments endpoint stops at 30,000 items
- What happened: repo-wide comments stream ended at 2019 with 18,665 saved + 11,335 PR comments skipped = exactly 30,000; sanity check showed 33,564 expected vs 18,665.
- Action: re-fetched in windows using `since`; final 33,558 vs 33,564.

## 2026-10-17 - Inconsistent label names (not reproduced)
- What I suspected: `plugin:logging` vs `plugin: warnings` formatting differences.
- What I found (2026-10-18): listing all 59 labels with `repr()` showed every `plugin:` label is written `plugin: x` with a space. The difference came from how the labels were displayed, not from the data.
- Action: none needed. `labels.py` still applies `.strip().lower()` as a cheap safeguard.

## 2026-10-18 - 35% of pytest issues have no type label
- What happened: 2,260 of 6,421 issues have no `type:` label.
- Impact: only 4,161 issues have a usable category; after removing 122 ambiguous ones, 4,039 remain for classifier training and eval.
- Action: category = None for these; kept in the cleaned file, excluded at training time.
- Class balance of the usable set: bug 1,481 / feature 1,126 / question 722 / other 386 / docs 324. Majority-class baseline is about 37%.

## 2026-10-18 - Multi-label and mixed-purpose labels
- What happened: 555 issues carry 2+ type labels. Most collapse to one category (bug+regression, enhancement+proposal), but 122 conflict (e.g. bug+docs, docs+enhancement) and are marked "ambiguous".
- Known noise: `type: proposal` was mapped to feature after reading 15 samples (about 3 of 15 were internal/maintainer work, not feature requests). `type: performance` mapped to other.

## 2026-10-18 - Unbalanced or unusual code fences
- What happened: 27 issue bodies have an odd number of ``` fences (inline fences, "``` python" with a space, six-backtick lines, fences inside quoted replies).
- Impact: fence pairing can misalign within those issues; the rest of the dataset is unaffected.
- Action: not fixed (0.4% of issues).

## 2026-10-18 - Issue 9201 lost two code blocks during cleaning
- What happened: the invariant check (every raw code block must survive in the cleaned text) fails for 1 of 6,421 issues. Cause not investigated; suspect HTML comment removal interacting with code placeholders.
- Action: kept the invariant check in clean_issues.py so a regression would show up as a higher count.

## 2026-10-18 - Empty bodies after cleaning
- What happened: 31 issues have an empty body after cleaning: 25 were blank in raw, 6 were Bitbucket-migrated stubs with only the wrapper.
- Action: keep the rows; downstream code should treat an issue as empty only if title and body are both empty.

## 2026-10-18 - Few labeled duplicates
- What happened: only 5 issues carry `closed as duplicate`.
- Impact: not enough for the Week 3 Day 5 duplicate-detection test (15-20 known duplicates).
- Action: mine comments for "duplicate of #N" phrasing in Week 3.