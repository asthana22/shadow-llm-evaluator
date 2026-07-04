import time
from typing import Any

import httpx

from app.config import Settings
from app.proxy.errors import PrimaryTimeoutError, PrimaryUnavailableError
from app.types.chat import PrimaryProxyResult

FORWARDED_REQUEST_HEADERS = frozenset(
    {"content-type", "authorization", "accept", "accept-language"}
)


def forwardable_headers(headers: dict[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower() in FORWARDED_REQUEST_HEADERS
    }


def parse_request_body(body: bytes) -> Any:
    if not body:
        return {}
    try:
        import json

        return json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"_raw": body.decode("utf-8", errors="replace")}


def prepare_upstream_body(body: bytes, default_model: str) -> bytes:
    """Ensure DigitalOcean/OpenAI-compatible chat completion payload."""
    import json

    if not body:
        payload = {
            "model": default_model,
            "messages": [{"role": "user", "content": "Hello"}],
        }
        return json.dumps(payload).encode()

    data = json.loads(body)
    if "messages" not in data:
        if "prompt" in data:
            content = data.pop("prompt")
            data.setdefault("model", default_model)
            data["messages"] = [{"role": "user", "content": content}]
        else:
            data.setdefault("model", default_model)
    else:
        data.setdefault("model", default_model)

    return json.dumps(data).encode()


class PrimaryLlmClient:
    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._url = settings.primary_llm_url
        self._api_key = settings.primary_llm_api_key
        self._timeout = settings.primary_timeout_ms / 1000
        self._http_client = http_client

    def _build_headers(self, incoming: dict[str, str]) -> dict[str, str]:
        headers = forwardable_headers(incoming)
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        if "content-type" not in {k.lower() for k in headers}:
            headers["Content-Type"] = "application/json"
        return headers

    async def forward(self, body: bytes, headers: dict[str, str]) -> PrimaryProxyResult:
        started = time.monotonic()
        client = self._http_client or httpx.AsyncClient()
        owns_client = self._http_client is None
        outbound_headers = self._build_headers(headers)

        try:
            response = await client.post(
                self._url,
                content=body,
                headers=outbound_headers,
                timeout=self._timeout,
            )
            latency_ms = int((time.monotonic() - started) * 1000)
            return PrimaryProxyResult(
                status_code=response.status_code,
                body=response.text,
                headers=dict(response.headers),
                latency_ms=latency_ms,
            )
        except httpx.TimeoutException as exc:
            raise PrimaryTimeoutError("Primary LLM request timed out") from exc
        except httpx.HTTPError as exc:
            raise PrimaryUnavailableError("Primary LLM is unavailable") from exc
        finally:
            if owns_client:
                await client.aclose()
