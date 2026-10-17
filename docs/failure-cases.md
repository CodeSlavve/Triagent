## 2026-10-17 - Flask labels unusable for classification
- What happened: 2,403 of 2,766 issues (87%) had no label; no feature/enhancement/question labels existed.
- Impact: TF-IDF classifier had no usable training target.
- Action: switched primary repo to pytest-dev/pytest (77% labeled, 760 question / 1,418 bug).

## 2026-10-17 - Comments endpoint stops at 30,000 items
- What happened: repo-wide comments stream ended at 2019 with 18,665 saved + 11,335 PR comments skipped = exactly 30,000; sanity check showed 33,564 expected vs 18,665.
- Action: re-fetched in windows using `since`; final 33,558 vs 33,564.

## 2026-10-17 - Inconsistent label names
- plugin:logging vs plugin: warnings. Normalize in Day 3 cleaning.
- there are spaces after `label: ` but the `pluggin:logging` doesn't have it