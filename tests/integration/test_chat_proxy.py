import asyncio

import pytest
import httpx
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.db.repositories.proxy_request_repository import ProxyRequestRepository
from app.dependencies import get_primary_llm_client
from app.proxy.primary_llm import PrimaryLlmClient


@pytest.fixture
def mock_primary_transport():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text='{"action":"search"}',
            headers={"content-type": "application/json"},
        )

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_chat_proxy_returns_primary_and_persists(
    chat_app,
    mock_primary_transport,
):
    settings = get_settings().model_copy(update={"primary_llm_url": "http://mock-llm/v1/chat"})
    mock_client = PrimaryLlmClient(
        settings,
        http_client=httpx.AsyncClient(transport=mock_primary_transport),
    )
    chat_app.dependency_overrides[get_primary_llm_client] = lambda: mock_client

    transport = ASGITransport(app=chat_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/chat", json={"prompt": "hello"})

    assert response.status_code == 200
    assert response.json() == {"action": "search"}
    request_id = response.headers["x-request-id"]
    assert request_id

    await asyncio.sleep(0.05)

    session_factory = chat_app.state.session_factory
    async with session_factory() as session:
        repo = ProxyRequestRepository(session)
        record = await repo.get_by_request_id(request_id)

    assert record is not None
    assert record.primary_response == '{"action":"search"}'
    assert record.request_body == {"prompt": "hello"}
    assert record.shadow_status == "pending"


@pytest.mark.asyncio
async def test_chat_proxy_primary_timeout_returns_504(chat_app):
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    settings = get_settings().model_copy(update={"primary_llm_url": "http://mock-llm/v1/chat"})
    mock_client = PrimaryLlmClient(
        settings,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    chat_app.dependency_overrides[get_primary_llm_client] = lambda: mock_client

    transport = ASGITransport(app=chat_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/chat", json={"prompt": "hello"})

    assert response.status_code == 504
    assert response.json()["code"] == "PRIMARY_TIMEOUT"
