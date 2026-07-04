from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.proxy.primary_proxy_service import PrimaryProxyService
from app.types.chat import PrimaryProxyResult


@pytest.mark.asyncio
async def test_handle_chat_returns_primary_immediately():
    mock_client = AsyncMock()
    mock_client.forward.return_value = PrimaryProxyResult(
        status_code=200,
        body='{"action":"search"}',
        headers={"content-type": "application/json"},
        latency_ms=42,
    )

    service = PrimaryProxyService(
        mock_client,
        Settings(primary_llm_model="llama3.3-70b-instruct"),
        session_factory=AsyncMock(),
    )

    with patch("app.proxy.primary_proxy_service.asyncio.create_task") as create_task:
        create_task.return_value = MagicMock()
        result = await service.handle_chat(
            request_id="req-1",
            body=b'{"prompt":"hello"}',
            headers={"content-type": "application/json"},
        )

    assert result.status_code == 200
    assert result.body == '{"action":"search"}'
    create_task.assert_called_once()


@pytest.mark.asyncio
async def test_run_side_effects_persists_and_enqueues():
    mock_client = AsyncMock()
    session = AsyncMock()

    class SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *_args):
            return None

    session_factory = MagicMock(return_value=SessionContext())

    service = PrimaryProxyService(
        mock_client,
        Settings(primary_llm_model="llama3.3-70b-instruct"),
        session_factory=session_factory,
    )

    result = PrimaryProxyResult(
        status_code=200,
        body='{"action":"search"}',
        headers={"content-type": "application/json"},
        latency_ms=42,
    )

    with patch(
        "app.proxy.primary_proxy_service.ProxyRequestService.save_primary_response",
        new=AsyncMock(),
    ) as save:
        with patch(
            "app.proxy.primary_proxy_service.MetricsService.record_primary_processed",
            new=AsyncMock(),
        ) as record_metric:
            with patch(
                "app.proxy.primary_proxy_service.ShadowQueue.try_enqueue",
                new=AsyncMock(return_value=True),
            ) as enqueue:
                with patch(
                    "app.proxy.primary_proxy_service.create_redis",
                    new=AsyncMock(return_value=AsyncMock(aclose=AsyncMock())),
                ):
                    await service._run_side_effects(
                        request_id="req-1",
                        body=b'{"prompt":"hello"}',
                        result=result,
                    )

    save.assert_awaited_once()
    record_metric.assert_awaited_once()
    enqueue.assert_awaited_once_with("req-1")


@pytest.mark.asyncio
async def test_handle_chat_does_not_await_side_effects():
    mock_client = AsyncMock()
    mock_client.forward.return_value = PrimaryProxyResult(
        status_code=200,
        body='{"action":"search"}',
        headers={"content-type": "application/json"},
        latency_ms=42,
    )

    service = PrimaryProxyService(
        mock_client,
        Settings(primary_llm_model="llama3.3-70b-instruct"),
        session_factory=AsyncMock(),
    )

    with patch("app.proxy.primary_proxy_service.asyncio.create_task") as create_task:
        create_task.return_value = MagicMock()
        result = await service.handle_chat(
            request_id="req-1",
            body=b'{"prompt":"hello"}',
            headers={"content-type": "application/json"},
        )

    assert result.status_code == 200
    create_task.assert_called_once()
