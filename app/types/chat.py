from typing import Any

from pydantic import BaseModel, Field


class PrimaryProxyResult(BaseModel):
    status_code: int
    body: str
    headers: dict[str, str] = Field(default_factory=dict)
    latency_ms: int


class SaveProxyRequestInput(BaseModel):
    request_id: str
    request_body: Any
    primary_status: int
    primary_response: str
    latency_primary_ms: int


class SaveShadowResultInput(BaseModel):
    request_id: str
    candidate_status: int | None
    candidate_response: str | None
    latency_candidate_ms: int | None
    primary_valid: bool
    candidate_valid: bool
    exact_action_match: bool
    primary_action: str | None
    candidate_action: str | None
    shadow_status: str
    shadow_error: str | None = None


class ProxyRequestRecord(BaseModel):
    request_id: str
    request_body: Any
    primary_status: int
    primary_response: str
    latency_primary_ms: int
    shadow_status: str
    created_at: str
    candidate_status: int | None = None
    candidate_response: str | None = None
    latency_candidate_ms: int | None = None
    primary_valid: bool | None = None
    candidate_valid: bool | None = None
    exact_action_match: bool | None = None
    primary_action: str | None = None
    candidate_action: str | None = None
    shadow_error: str | None = None
