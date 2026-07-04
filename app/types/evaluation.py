from typing import Any

from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    primary_valid: bool = False
    candidate_valid: bool = False
    exact_action_match: bool = False
    primary_action: str | None = None
    candidate_action: str | None = None
