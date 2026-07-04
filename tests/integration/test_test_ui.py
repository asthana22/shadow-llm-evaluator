import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_ui_page(chat_app):
    transport = ASGITransport(app=chat_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test")

    assert response.status_code == 200
    assert "Primary LLM Test" in response.text
    assert "/v1/chat" in response.text


@pytest.mark.asyncio
async def test_ui_config(chat_app):
    transport = ASGITransport(app=chat_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test/config")

    assert response.status_code == 200
    data = response.json()
    assert "default_model" in data
    assert data["chat_endpoint"] == "/v1/chat"
