import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

import httpx

from app.config import get_settings
from app.db.repositories.proxy_request_repository import ProxyRequestRepository
from app.dependencies import get_metrics_service, get_primary_llm_client, get_shadow_queue
from app.metrics.metrics_service import MetricsService
from app.metrics.metrics_store import MetricsStore
from app.proxy.candidate_llm import CandidateLlmClient
from app.proxy.primary_llm import PrimaryLlmClient
from app.queue.shadow_queue import ShadowQueue
from app.shadow.shadow_service import ShadowService


@pytest.mark.asyncio
async def test_primary_returns_before_shadow_completes(chat_app):
    chat_completion = (
        '{"choices":[{"message":{"content":"{\\"action\\":\\"search\\"}"}}],'
        '"model":"test"}'
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=chat_completion)

    settings = get_settings().model_copy(update={"primary_llm_url": "http://mock/v1/chat"})
    chat_app.dependency_overrides[get_primary_llm_client] = lambda: PrimaryLlmClient(
        settings, httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )

    transport = ASGITransport(app=chat_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/chat", json={"prompt": "find flights"})

    assert response.status_code == 200
    request_id = response.headers["x-request-id"]

    await asyncio.sleep(0.05)

    session_factory = chat_app.state.session_factory
    async with session_factory() as session:
        repo = ProxyRequestRepository(session)
        record = await repo.get_by_request_id(request_id)
        assert record.shadow_status == "pending"

        mock_candidate = AsyncMock(spec=CandidateLlmClient)
        mock_candidate.complete.return_value = (200, chat_completion, 30)
        metrics = MetricsService(MetricsStore(chat_app.state.redis))
        service = ShadowService(get_settings(), repo, mock_candidate, metrics)
        await service.process(request_id)

        updated = await repo.get_by_request_id(request_id)
        assert updated.shadow_status == "completed"
        assert updated.exact_action_match is True
        assert updated.candidate_response == chat_completion
