from typing import get_args

import pytest
from pydantic import ValidationError

from src.schema.triage import TriageResult

VALID = {
    "reasoning": "The traceback shows a crash on unicode input, so this is a defect.",
    "category": "bug",
    "priority": "medium",
    "summary": "CSV import crashes with UnicodeDecodeError on non-ASCII input.",
    "suggested_action": "Ask for a minimal reproducible example and the file encoding.",
    "confidence": 0.8,
}


def make(**overrides):
    return {**VALID, **overrides}


def test_valid_object_passes():
    result = TriageResult(**VALID)
    assert result.category == "bug"
    assert result.priority == "medium"
    assert result.confidence == 0.8


def test_valid_json_string_passes():
    import json

    result = TriageResult.model_validate_json(json.dumps(VALID))
    assert result.summary.startswith("CSV import")


@pytest.mark.parametrize(
    "overrides",
    [
        {"category": "bugfix"},        # not in the allowed list
        {"category": "Bug"},           # wrong case
        {"priority": "urgent"},        # not in the allowed list
        {"confidence": 1.5},           # above upper bound
        {"confidence": -0.1},          # below lower bound
        {"confidence": "high"},        # not a number
        {"summary": ""},               # empty string
        {"summary": "x" * 301},        # over max_length
        {"reasoning": ""},             # empty string
        {"suggested_action": ""},      # empty string
    ],
)
def test_invalid_values_rejected(overrides):
    with pytest.raises(ValidationError):
        TriageResult(**make(**overrides))


@pytest.mark.parametrize("field", list(VALID))
def test_missing_field_rejected(field):
    data = {k: v for k, v in VALID.items() if k != field}
    with pytest.raises(ValidationError):
        TriageResult(**data)


def test_categories_match_labels():
    from src.ingestion.labels import TYPE_TO_CATEGORY

    schema_values = set(get_args(TriageResult.model_fields["category"].annotation))
    assert schema_values == set(TYPE_TO_CATEGORY.values())