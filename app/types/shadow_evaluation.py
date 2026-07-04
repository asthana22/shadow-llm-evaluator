from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ShadowOutcome(str, Enum):
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"
    SHED = "shed"


class ShadowEvaluationRecord(BaseModel):
    id: str
    request_id: str
    created_at: str
    request_body: Any
    primary_status: int | None = None
    primary_response: str | None = None
    candidate_status: int | None = None
    candidate_response: str | None = None
    primary_valid: bool = False
    candidate_valid: bool = False
    exact_action_match: bool = False
    primary_action: str | None = None
    candidate_action: str | None = None
    shadow_outcome: ShadowOutcome
    latency_primary_ms: int | None = None
    latency_candidate_ms: int | None = None
    error_message: str | None = None


class CreateShadowEvaluationInput(BaseModel):
    request_id: str
    request_body: Any
    primary_status: int | None = None
    primary_response: str | None = None
    candidate_status: int | None = None
    candidate_response: str | None = None
    primary_valid: bool = False
    candidate_valid: bool = False
    exact_action_match: bool = False
    primary_action: str | None = None
    candidate_action: str | None = None
    shadow_outcome: ShadowOutcome
    latency_primary_ms: int | None = None
    latency_candidate_ms: int | None = None
    error_message: str | None = None


class MetricsResponse(BaseModel):
    total_requests_processed: int = 0
    shadow_execution_errors: int = 0
    shadow_execution_timeouts: int = 0
    shadow_tasks_shed: int = 0
    comparisons_completed: int = 0
    exact_match_count: int = 0
    exact_match_rate: float = Field(default=0.0)
