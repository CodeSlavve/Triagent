from typing import Literal
from pydantic import BaseModel, Field

class TriageResult(BaseModel):
    reasoning: str = Field(
        min_length=1,
        description="Brief step-by-step justification, written before category is chosen.",
    )
    category: Literal["bug", "feature", "docs", "question", "other"] = Field(
        description="The issue type"
    )
    priority: Literal["low", "medium", "high"] = Field(
        description="How urgetly maintainers should look at this."
    )
    summary: str = Field(
        min_length=1,
        max_length=300,
        description="One or two sentences describing the issue."
    )
    suggested_action: str = Field(
        min_length=1,
        description="The single most useful next step for a maintainer.",
    )
    confidence: float = Field(
        ge=0,
        le=1,
        description="Number between 0 and 1. Use lower values when the issue is unclear."
    )