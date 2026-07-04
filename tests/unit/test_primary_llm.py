import pytest
import httpx

from app.config import Settings
from app.proxy.errors import PrimaryTimeoutError, PrimaryUnavailableError
from app.proxy.primary_llm import PrimaryLlmClient, forwardable_headers, parse_request_body


def test_forwardable_headers_filters_hop_by_hop():
    headers = {
        "content-type": "application/json",
        "host": "localhost",
        "authorization": "Bearer token",
    }
    assert forwardable_headers(headers) == {
        "content-type": "application/json",
        "authorization": "Bearer token",
    }


def test_parse_request_body_json():
    assert parse_request_body(b'{"prompt":"hi"}') == {"prompt": "hi"}


def test_parse_request_body_non_json():
    result = parse_request_body(b"plain text")
    assert result == {"_raw": "plain text"}


@pytest.mark.asyncio
async def test_primary_llm_client_forwards_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat"
        assert request.content == b'{"prompt":"hello"}'
        return httpx.Response(200, text='{"action":"search"}')

    transport = httpx.MockTransport(handler)
    settings = Settings(primary_llm_url="http://mock-llm/v1/chat")
    client = PrimaryLlmClient(settings, http_client=httpx.AsyncClient(transport=transport))

    result = await client.forward(
        b'{"prompt":"hello"}',
        {"content-type": "application/json"},
    )

    assert result.status_code == 200
    assert result.body == '{"action":"search"}'
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_primary_llm_client_timeout():
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    transport = httpx.MockTransport(handler)
    settings = Settings(primary_llm_url="http://mock-llm/v1/chat", primary_timeout_ms=1000)
    client = PrimaryLlmClient(settings, http_client=httpx.AsyncClient(transport=transport))

    with pytest.raises(PrimaryTimeoutError):
        await client.forward(b"{}", {"content-type": "application/json"})


@pytest.mark.asyncio
async def test_primary_llm_client_unavailable():
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    transport = httpx.MockTransport(handler)
    settings = Settings(primary_llm_url="http://mock-llm/v1/chat")
    client = PrimaryLlmClient(settings, http_client=httpx.AsyncClient(transport=transport))

    with pytest.raises(PrimaryUnavailableError):
        await client.forward(b"{}", {"content-type": "application/json"})
