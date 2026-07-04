import pytest
from httpx import ASGITransport, AsyncClient

from app.metrics.metrics_service import MetricsService
from app.metrics.metrics_store import MetricsStore


@pytest.mark.asyncio
async def test_metrics_endpoint(chat_app):
    store = MetricsStore(chat_app.state.redis)
    service = MetricsService(store)
    await service.record_primary_processed()
    await service.record_comparison(True)

    # Use real metrics service for this test
    from app.dependencies import get_metrics_service

    chat_app.dependency_overrides[get_metrics_service] = lambda: service

    transport = ASGITransport(app=chat_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")

    assert response.status_code == 200
    data = response.json()
    assert data["total_requests_processed"] == 1
    assert data["comparisons_completed"] == 1
    assert data["exact_match_count"] == 1
    assert data["exact_match_rate"] == 1.0
