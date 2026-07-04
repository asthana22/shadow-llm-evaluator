# Data Storage — PostgreSQL vs Valkey/Redis

This document describes **what is stored where**, **when it is written**, and **who reads it** (web vs worker).

---

## Summary

| Store | Role | Lifetime | Used by |
|-------|------|----------|---------|
| **PostgreSQL** | Durable per-request audit trail (primary + shadow results) | Persistent | Web (write primary), Worker (read/update shadow) |
| **Valkey/Redis** | Ephemeral job queue + live counters for `/metrics` | Queue: until processed; metrics: until reset | Web (enqueue + increment), Worker (consume + increment) |

```
POST /v1/chat
    │
    ├─► PostgreSQL     proxy_requests row (primary response staged)
    ├─► Redis          INCR metrics:total_requests
    └─► Redis          ENQUEUE arq job { request_id }   (primary 2xx only)

Worker process_shadow_request
    │
    ├─► PostgreSQL     read proxy_requests, update shadow fields
    ├─► Redis          INCR comparisons / errors / timeouts
    └─► (optional)     shadow_evaluations — schema exists, not wired in worker yet
```

---

## PostgreSQL

**Driver:** SQLite locally (`DB_DRIVER=sqlite`), PostgreSQL in production (`DB_DRIVER=postgres`).

**Schema bootstrap:** `init_db()` on app/worker startup — `Base.metadata.create_all`. SQLite dev DB also gets lightweight column migrations for `proxy_requests`.

### Table: `proxy_requests` (active — primary data store)

One row per chat request. Written by the **web** after primary response; updated by the **worker** after candidate evaluation.

| Column | Type | Written by | When | Description |
|--------|------|------------|------|-------------|
| `request_id` | `VARCHAR(36)` PK | Web | Primary side-effects | Server-generated UUID (`X-Request-ID`) |
| `created_at` | `TIMESTAMPTZ` | Web | Insert | Row creation time |
| `request_body` | `JSON` | Web | Insert | Original inbound chat JSON |
| `primary_status` | `INTEGER` | Web | Insert | HTTP status from primary LLM |
| `primary_response` | `TEXT` | Web | Insert | Raw primary response body |
| `latency_primary_ms` | `INTEGER` | Web | Insert | Primary call duration |
| `shadow_status` | `VARCHAR(32)` | Web → Worker | Insert → update | `pending` → `processing` → `completed` / `failed` |
| `candidate_status` | `INTEGER` | Worker | Shadow complete | HTTP status from candidate LLM |
| `candidate_response` | `TEXT` | Worker | Shadow complete | Raw candidate response body |
| `latency_candidate_ms` | `INTEGER` | Worker | Shadow complete | Candidate call duration |
| `primary_valid` | `BOOLEAN` | Worker | Shadow complete | Primary content parses as JSON with `action` |
| `candidate_valid` | `BOOLEAN` | Worker | Shadow complete | Candidate content parses as JSON with `action` |
| `exact_action_match` | `BOOLEAN` | Worker | Shadow complete | `primary_action == candidate_action` |
| `primary_action` | `VARCHAR(255)` | Worker | Shadow complete | Extracted `action` from primary |
| `candidate_action` | `VARCHAR(255)` | Worker | Shadow complete | Extracted `action` from candidate |
| `shadow_error` | `TEXT` | Worker | On failure | e.g. `candidate_timeout`, `candidate_http_500` |

**`shadow_status` lifecycle:**

```
pending ──► processing ──► completed
                │
                └──► failed
```

**Important:** The ARQ job payload contains only `request_id`. The worker loads `request_body` and `primary_response` from this table — request bodies are **not** duplicated in Redis.

### Table: `shadow_evaluations` (optional — not wired in worker yet)

Separate audit table with a similar shape plus `shadow_outcome`. Created at startup, but **the worker does not write here today**.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `VARCHAR(36)` PK | UUID |
| `request_id` | `VARCHAR(64)` | Indexed; links to chat request |
| `created_at` | `TIMESTAMPTZ` | Insert time |
| `request_body` | `JSON` | Original request |
| `primary_status`, `primary_response` | nullable | Primary LLM result |
| `candidate_status`, `candidate_response` | nullable | Candidate LLM result |
| `primary_valid`, `candidate_valid` | `BOOLEAN` | Evaluator flags |
| `exact_action_match` | `BOOLEAN` | Match result |
| `primary_action`, `candidate_action` | `VARCHAR(255)` | Extracted actions |
| `shadow_outcome` | `VARCHAR(32)` | e.g. `completed`, `failed` |
| `latency_primary_ms`, `latency_candidate_ms` | nullable | Latencies |
| `error_message` | `TEXT` | Failure detail |

**Config:** `ENABLE_AUDIT_LOG=true` enables `ShadowEvaluationService`, but the shadow worker path currently updates **`proxy_requests` only**. Use `proxy_requests` for production queries today.

---

## Valkey / Redis

**Connection:** `REDIS_URL` (local: `redis://`, production: `rediss://` for TLS).

Two distinct uses: **ARQ job queue** and **metrics counters**.

### 1. ARQ job queue

| Key / pattern | Type | Written by | Read by | Content |
|---------------|------|------------|---------|---------|
| `arq:queue` | Sorted set | Web (`ShadowQueue.try_enqueue`) | Worker (ARQ) | Pending job IDs ordered by enqueue time |
| `arq:job:*`, `arq:result:*`, … | ARQ-managed | ARQ library | ARQ library | Job metadata, payloads, results |

**Job definition:**

```python
# Enqueued by web after primary 2xx
await pool.enqueue_job("process_shadow_request", request_id)
```

**Load shedding:** Before enqueue, web checks `ZCARD arq:queue`. If depth ≥ `SHADOW_MAX_QUEUE_SIZE`, the job is **dropped** and `metrics:shadow_shed` is incremented.

**Concurrency:** Worker `max_jobs` = `SHADOW_MAX_CONCURRENCY` limits parallel candidate LLM calls.

### 2. Metrics counters (live `/metrics`)

Integer counters — **not** per-request detail. Reset only if Redis is flushed.

| Redis key | API field | Incremented when | Process |
|-----------|-----------|------------------|---------|
| `metrics:total_requests` | `total_requests_processed` | Primary side-effects complete | Web |
| `metrics:shadow_shed` | `shadow_tasks_shed` | Queue full, job not enqueued | Web |
| `metrics:shadow_errors` | `shadow_execution_errors` | Candidate failure, enqueue failure, missing row | Web / Worker |
| `metrics:shadow_timeouts` | `shadow_execution_timeouts` | Candidate timeout | Worker |
| `metrics:comparisons_completed` | `comparisons_completed` | Shadow evaluation finished | Worker |
| `metrics:exact_match_count` | `exact_match_count` | Exact `action` match | Worker |

**Derived field:** `exact_match_rate` = `exact_match_count / comparisons_completed` (computed at read time in `MetricsStore.get_all()`).

---

## Write timeline by request

### Step 1 — Web: primary response returned to client

User receives primary LLM response. Background task runs:

| # | Action | Store | Key / table |
|---|--------|-------|-------------|
| 1 | Save primary result | PostgreSQL | `proxy_requests` insert |
| 2 | Count request | Redis | `INCR metrics:total_requests` |
| 3a | Enqueue shadow (if 2xx + queue has room) | Redis | `arq:queue` + ARQ job |
| 3b | Or shed (if queue full) | Redis | `INCR metrics:shadow_shed` |

### Step 2 — Worker: shadow evaluation

| # | Action | Store | Key / table |
|---|--------|-------|-------------|
| 1 | Load staged request | PostgreSQL | `SELECT proxy_requests WHERE request_id = ?` |
| 2 | Claim job | PostgreSQL | `shadow_status = processing` |
| 3 | Call candidate LLM | External | — |
| 4 | Evaluate + save | PostgreSQL | Update `proxy_requests` shadow columns |
| 5 | Record metrics | Redis | `INCR metrics:comparisons_completed` (+ `exact_match_count` if match) |

On candidate timeout/error:

| Action | Store |
|--------|-------|
| Save failure on row | PostgreSQL (`shadow_status=failed`, `shadow_error`) |
| Increment error/timeout | Redis |

---

## What is **not** stored in Redis

- Full request/response bodies (PostgreSQL only)
- Per-request evaluation history for analytics (PostgreSQL `proxy_requests`; optional `shadow_evaluations` when wired)
- Long-term audit beyond Redis persistence policy

## What is **not** stored in PostgreSQL

- Queue position / pending jobs (Redis ARQ)
- Aggregated live counters served by `/metrics` (Redis)

---

## Local vs production

| | Local | Production |
|---|-------|------------|
| SQL | SQLite file `./data/shadow_evaluator.db` | DO Managed PostgreSQL |
| Redis | Docker `redis:6379` | DO Managed Valkey (`rediss://`) |
| Tables | Same schema | Same schema |

---

## Useful queries

**Recent shadow results (PostgreSQL):**

```sql
SELECT request_id, shadow_status, primary_action, candidate_action,
       exact_action_match, shadow_error, created_at
FROM proxy_requests
ORDER BY created_at DESC
LIMIT 20;
```

**Queue depth (Redis CLI):**

```bash
redis-cli ZCARD arq:queue
```

**All metrics (Redis CLI):**

```bash
redis-cli MGET metrics:total_requests metrics:shadow_errors metrics:shadow_timeouts \
  metrics:shadow_shed metrics:comparisons_completed metrics:exact_match_count
```

Or use `GET /metrics` on the API.
