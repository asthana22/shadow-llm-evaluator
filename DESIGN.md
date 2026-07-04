# Design Decisions

## Stack

- **Python 3.11+** with **FastAPI**
- **Redis + ARQ** for async shadow job queue (replaces BullMQ)
- **SQLAlchemy 2 async** for SQLite (local) and PostgreSQL (production)

## Core contract

- Primary path is **sync** — user never waits for candidate LLM
- Shadow path is **async** — enqueued after primary response is ready
- Comparison runs only when both responses are received

## Heuristics

1. **Valid JSON payload** — body parses as JSON and contains an `action` key
2. **Exact action match** — `primary.action == candidate.action` (string equality)

## Metrics (`GET /metrics`)

| Field | Description |
|-------|-------------|
| `total_requests_processed` | Completed primary proxy requests |
| `shadow_execution_errors` | Candidate call failed |
| `shadow_execution_timeouts` | Candidate call exceeded timeout |
| `shadow_tasks_shed` | Jobs rejected due to queue capacity |
| `comparisons_completed` | Finished shadow evaluations |
| `exact_match_count` | Both valid JSON + matching `action` |
| `exact_match_rate` | `exact_match_count / comparisons_completed` |

## Queue

- **Redis + ARQ**
- `SHADOW_MAX_CONCURRENCY` — max parallel shadow jobs per worker
- `SHADOW_MAX_QUEUE_SIZE` — load shedding threshold

## Database

- **Redis** — live metrics + job queue (required)
- **SQLite** — local dev audit log (default)
- **PostgreSQL** — production audit log
- **`proxy_requests`** — primary response staged by `request_id` for shadow worker (`shadow_status=pending`)
- Audit writes to `shadow_evaluations` only when `ENABLE_AUDIT_LOG=true` (after comparison)

### Layer split

| Layer | File | Role |
|-------|------|------|
| Repository | `app/db/repositories/shadow_evaluation_repository.py` | SQL only |
| Service | `app/db/services/shadow_evaluation_service.py` | Business rules |
| Orchestrator | `app/shadow/shadow_service.py` | Full shadow job flow |

## Processes

| Process | Entry | Role |
|---------|-------|------|
| Web | `uvicorn app.main:app` | HTTP API, primary proxy, enqueue shadow |
| Worker | `arq worker.main.WorkerSettings` | Candidate LLM + evaluate + metrics |

## Shadow flow (implemented)

1. Primary returns → row in `proxy_requests` (`shadow_status=pending`)
2. Job enqueued to Redis (ARQ) if queue not full
3. Worker loads row by `request_id`, calls candidate LLM
4. Saves candidate response + evaluation fields on same row
5. Updates Redis metrics (`GET /metrics`)

## Evaluator (3-hour scope)

- Extract `action` from chat completion `choices[0].message.content` JSON
- Valid if parseable JSON with string `action` field
- Exact match: `primary_action == candidate_action`
- Real-time via Redis counters (sub-ms reads on `GET /metrics`)
