# API Reference

## POST /v1/chat

Proxy to primary LLM. Response returns immediately; primary result is saved to `proxy_requests` by `request_id` for shadow worker lookup.

**Request:** Body forwarded as-is to `PRIMARY_LLM_URL`.

**Response headers:**
- `X-Request-ID` — server-generated UUID (not accepted from client; avoids PK collisions in `proxy_requests`)

**Response:** Primary LLM status + body (passthrough).

**Errors:**

| Status | Code | When |
|--------|------|------|
| 502 | `PRIMARY_UNAVAILABLE` | Cannot reach primary |
| 504 | `PRIMARY_TIMEOUT` | Primary exceeded timeout |

**Staged record (`proxy_requests`):**

| Field | Purpose |
|-------|---------|
| `request_id` | Shadow worker lookup key |
| `request_body` | Original inbound JSON |
| `primary_response` | Raw primary body (for evaluator) |
| `shadow_status` | `pending` until worker runs |

---

## GET /metrics

Real-time shadow evaluation metrics (Phase 3).

---

## GET /health

```json
{ "status": "ok" }
```
