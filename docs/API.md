# API Reference

Base URL (local): `http://localhost:8080`  
Base URL (production): `https://sea-lion-app-l24ve.ondigitalocean.app`

---

## POST /v1/chat

Proxy to primary LLM. Response returns immediately; primary result is saved to `proxy_requests` by `request_id` for shadow worker lookup.

**Request:** OpenAI-compatible chat completion JSON forwarded to `PRIMARY_LLM_URL`.

```json
{
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "temperature": 0.7
}
```

**Response headers:**

| Header | Description |
|--------|-------------|
| `X-Request-ID` | Server-generated UUID (for tracing) |

**Response:** Primary LLM status + body (passthrough).

**Proxy errors:**

| Status | Code | When |
|--------|------|------|
| 502 | `PRIMARY_UNAVAILABLE` | Cannot reach primary |
| 504 | `PRIMARY_TIMEOUT` | Primary exceeded timeout |

**Upstream errors** (401, 403, etc.) are returned as-is from the LLM provider.

**Shadow behavior:**

- Primary **2xx** → job enqueued for candidate evaluation  
- Primary **non-2xx** → no shadow job  

---

## GET /metrics

Real-time shadow evaluation metrics from Redis/Valkey counters.

**Response:**

```json
{
  "total_requests_processed": 0,
  "shadow_execution_errors": 0,
  "shadow_execution_timeouts": 0,
  "shadow_tasks_shed": 0,
  "comparisons_completed": 0,
  "exact_match_count": 0,
  "exact_match_rate": 0.0
}
```

| Field | Description |
|-------|-------------|
| `total_requests_processed` | Primary requests completed |
| `shadow_execution_errors` | Candidate call failed |
| `shadow_execution_timeouts` | Candidate timed out |
| `shadow_tasks_shed` | Jobs dropped (queue full) |
| `comparisons_completed` | Shadow evaluations finished |
| `exact_match_count` | Exact `action` matches |
| `exact_match_rate` | `exact_match_count / comparisons_completed` |

---

## GET /health

```json
{ "status": "ok" }
```

---

## GET /test

Browser-based test UI for sending requests to the primary LLM.

---

## GET /docs

Interactive OpenAPI (Swagger) documentation.
