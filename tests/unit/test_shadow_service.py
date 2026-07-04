from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.db.repositories.proxy_request_repository import ProxyRequestRepository
from app.metrics.metrics_service import MetricsService
from app.shadow.shadow_service import ShadowService
from app.types.chat import ProxyRequestRecord, SaveProxyRequestInput


@pytest.mark.asyncio
async def test_shadow_service_processes_and_evaluates(db_session):
    repo = ProxyRequestRepository(db_session)
    await repo.save(
        SaveProxyRequestInput(
            request_id="req-shadow-1",
            request_body={"prompt": "hi"},
            primary_status=200,
            primary_response='{"choices":[{"message":{"content":"{\\"action\\":\\"search\\"}"}}]}',
            latency_primary_ms=50,
        )
    )

    mock_candidate = AsyncMock()
    mock_candidate.complete.return_value = (
        200,
        '{"choices":[{"message":{"content":"{\\"action\\":\\"search\\"}"}}]}',
        80,
    )

    mock_metrics = AsyncMock(spec=MetricsService)
    service = ShadowService(
        settings=Settings(),
        repository=repo,
        candidate_client=mock_candidate,
        metrics=mock_metrics,
    )

    await service.process("req-shadow-1")

    record = await repo.get_by_request_id("req-shadow-1")
    assert record is not None
    assert record.shadow_status == "completed"
    assert record.candidate_response is not None
    assert record.exact_action_match is True
    assert record.primary_action == "search"
    assert record.candidate_action == "search"
    mock_metrics.record_comparison.assert_awaited_once_with(True)
