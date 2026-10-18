TYPE_TO_CATEGORY = {
    "type: bug": "bug",
    "type: regression": "bug",
    "type: enhancement": "feature",
    "type: proposal": "feature",
    "type: docs": "docs",
    "type: question": "question",
    "type: infrastructure": "other",
    "type: refactoring": "other",
    "type: selftests": "other",
    "type: deprecation": "other",
    "type: removal": "other",
    "type: backward compatibility": "other",
    "type: feature-branch": "other",
    "type: performance": "other",
}

REAL_CATEGORIES = {"bug", "feature", "docs", "question"}


def category_from_labels(label_names):
    """
    label_names: list of label strings, e.g. ["type: bug", "plugin: xdist"]
    Returns "bug" / "feature" / "docs" / "question" / "other",
    None if there is no type label, or "ambiguous" if categories conflict.
    """
    # TODO 1: normalize each name (strip whitespace, lowercase)
    cleaned = [name.strip().lower() for name in label_names]

    # TODO 2: build a set of categories from names found in TYPE_TO_CATEGORY
    categories = set(TYPE_TO_CATEGORY[name] for name in cleaned if name in TYPE_TO_CATEGORY)

    # TODO 3: empty set -> return None
    if not categories:
        return None

    # TODO 4: if the set contains a real category, remove "other"
    if categories & REAL_CATEGORIES:
        categories.discard("other")

    # TODO 5: one category left -> return it; more than one -> "ambiguous"
    if len(categories) == 1:
        return next(iter(categories))
    return "ambiguous"


if __name__ == "__main__":
    # Tests: run `python src/ingestion/labels.py`. An error means a rule is wrong.
    assert category_from_labels([]) is None
    assert category_from_labels(["plugin: xdist", "status: help wanted"]) is None
    assert category_from_labels(["type: bug"]) == "bug"
    assert category_from_labels(["type: bug", "type: regression"]) == "bug"
    assert category_from_labels(["type: enhancement", "type: proposal"]) == "feature"
    assert category_from_labels(["type: bug", "type: infrastructure"]) == "bug"
    assert category_from_labels(["type: infrastructure"]) == "other"
    assert category_from_labels(["type: bug", "type: docs"]) == "ambiguous"
    assert category_from_labels([" Type: Bug "]) == "bug"
    print("all tests passed")