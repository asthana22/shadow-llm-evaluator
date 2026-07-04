import json

from app.config import Settings
from app.proxy.primary_llm import PrimaryLlmClient, prepare_upstream_body


class CandidateLlmClient:
    """HTTP client for the candidate LLM — uses CANDIDATE_* settings only."""

    def __init__(self, settings: Settings, http_client=None) -> None:
        api_key = settings.candidate_llm_api_key or settings.primary_llm_api_key
        candidate_settings = settings.model_copy(
            update={
                "primary_llm_url": settings.candidate_llm_url,
                "primary_llm_api_key": api_key,
                "primary_timeout_ms": settings.shadow_job_timeout_ms,
            }
        )
        self._inner = PrimaryLlmClient(candidate_settings, http_client=http_client)
        self._model = settings.candidate_llm_model

    async def complete(self, request_body: dict) -> tuple[int, str, int]:
        body = json.dumps(request_body).encode() if isinstance(request_body, dict) else b"{}"
        upstream = prepare_upstream_body(body, self._model)
        result = await self._inner.forward(upstream, {"content-type": "application/json"})
        return result.status_code, result.body, result.latency_ms
