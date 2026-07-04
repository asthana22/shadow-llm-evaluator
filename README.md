# Shadow-Mode LLM Evaluator API

Production-ready **FastAPI** proxy that serves customer traffic through a **primary LLM** while asynchronously routing the same requests to a **candidate LLM** for shadow evaluation — without adding latency to the user.

[![CI](https://github.com/asthana22/shadow-llm-evaluator/actions/workflows/ci.yml/badge.svg)](https://github.com/asthana22/shadow-llm-evaluator/actions/workflows/ci.yml)

---

## What it does

1. **Sync:** `POST /v1/chat` → forwards to your **primary LLM** and returns the response immediately  
2. **Async:** Same request is queued for **candidate LLM** evaluation in the background  
3. **Compare:** Heuristic check — valid JSON + exact `{ "action": "..." }` match  
4. **Observe:** `GET /metrics` — live counters and match rate  

```
Client ──► Primary LLM ──► response (immediate)
              │
              └──► [background] ──► Candidate LLM ──► Evaluator ──► Metrics
```

📄 **Interview / deep dive:** [docs/DESIGN.md](docs/DESIGN.md) · [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/DATA.md](docs/DATA.md)

---

## Live demo

| Endpoint | URL |
|----------|-----|
| Health | https://sea-lion-app-l24ve.ondigitalocean.app/health |
| Test UI | https://sea-lion-app-l24ve.ondigitalocean.app/test |
| Metrics | https://sea-lion-app-l24ve.ondigitalocean.app/metrics |
| API docs | https://sea-lion-app-l24ve.ondigitalocean.app/docs |

---

## Quick start (local)

### Prerequisites

- Python 3.11+
- Docker (for Redis + Postgres locally)

### 1. Clone and configure

```bash
git clone https://github.com/asthana22/shadow-llm-evaluator.git
cd shadow-llm-evaluator
cp .env.example .env
# Edit .env — add PRIMARY_LLM_API_KEY, CANDIDATE_LLM_API_KEY
```

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Start infrastructure

```bash
docker compose up -d redis postgres
```

### 4. Run the API and worker (two terminals)

```bash
# Terminal 1 — Web API
uvicorn app.main:app --reload --port 8080

# Terminal 2 — Shadow worker
arq worker.main.WorkerSettings
```

### 5. Try it

**Browser:** http://localhost:8080/test  

**curl:**

```bash
# Health
curl http://localhost:8080/health

# Chat (primary LLM)
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Say hello"}]}'

# Metrics (after a few seconds for worker)
curl http://localhost:8080/metrics
```

**Smoke script:**

```bash
python scripts/smoke_chat.py
```

---

## Docker Compose (full stack)

```bash
cp .env.example .env   # configure keys
docker compose up --build
```

Runs: `api`, `worker`, `redis`, `postgres` on port **8080**.

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/chat` | Proxy to primary LLM; shadow eval enqueued async |
| `GET` | `/metrics` | Real-time evaluation metrics |
| `GET` | `/health` | Health check |
| `GET` | `/test` | Browser test UI |
| `GET` | `/docs` | OpenAPI (Swagger) |

Full API details: [docs/API.md](docs/API.md)

### Example chat request

```bash
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "Reply with JSON containing an action field."},
      {"role": "user", "content": "Find flights to NYC"}
    ]
  }'
```

Response includes upstream LLM JSON + header `X-Request-ID`.

### Example metrics response

```json
{
  "total_requests_processed": 42,
  "shadow_execution_errors": 1,
  "shadow_execution_timeouts": 0,
  "shadow_tasks_shed": 0,
  "comparisons_completed": 40,
  "exact_match_count": 35,
  "exact_match_rate": 0.875
}
```

---

## Configuration

All settings via environment variables (see [.env.example](.env.example)).

| Variable | Description | Default |
|----------|-------------|---------|
| `PRIMARY_LLM_URL` | Primary upstream URL | DO inference endpoint |
| `PRIMARY_LLM_API_KEY` | Primary API key | — |
| `PRIMARY_LLM_MODEL` | Primary model name | `llama3.3-70b-instruct` |
| `CANDIDATE_LLM_URL` | Candidate upstream URL | DO inference endpoint |
| `CANDIDATE_LLM_API_KEY` | Candidate API key | — |
| `CANDIDATE_LLM_MODEL` | Candidate model name | `openai-gpt-oss-120b` |
| `REDIS_URL` | Valkey/Redis URL | `redis://localhost:6379` |
| `DB_DRIVER` | `sqlite` or `postgres` | auto-detect |
| `DATABASE_URL` | Postgres connection string | — |
| `SHADOW_MAX_CONCURRENCY` | Max parallel shadow jobs | `50` |
| `SHADOW_MAX_QUEUE_SIZE` | Load-shed threshold | `500` |
| `LOG_LEVEL` | Logging level | `INFO` |

---

## Project structure

```
shadow-llm-evaluator/
├── app/
│   ├── main.py                 # FastAPI entry
│   ├── config.py               # Settings + Postgres URL normalization
│   ├── api/routes/             # HTTP endpoints
│   ├── proxy/                  # Primary + candidate LLM clients
│   ├── shadow/                 # Shadow worker orchestration
│   ├── queue/                  # ARQ queue + load shedding
│   ├── evaluator/              # JSON + action match heuristics
│   ├── metrics/                # Redis counters
│   ├── db/                     # SQLAlchemy models + repositories
│   └── static/test-ui/         # Browser test UI
├── worker/main.py              # ARQ worker entry
├── tests/                      # Unit + integration tests
├── docs/                       # Design, architecture, deployment
├── deploy/digitalocean/        # App Platform spec
├── Dockerfile
└── docker-compose.yml
```

---

## Testing

```bash
pytest -v
ruff check app tests worker
```

CI runs on every push to `main` (GitHub Actions).

---

## Deployment

Production deployment on **DigitalOcean App Platform**:

- **Web** — `uvicorn app.main:app --host 0.0.0.0 --port 8080`
- **Worker** — `arq worker.main.WorkerSettings`
- **Managed PostgreSQL** + **Managed Valkey**

Step-by-step guide: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## Design highlights (for reviewers)

| Property | How it's achieved |
|----------|-------------------|
| **Zero added latency** | User response sent before DB/metrics/shadow work |
| **Primary isolation** | Shadow failures never fail the user request |
| **Load shedding** | Queue cap drops excess shadow jobs under spike |
| **Bounded concurrency** | Worker `max_jobs` limits parallel candidate calls |
| **Observability** | Structured logs + `/metrics` + `X-Request-ID` |

Full design document: [docs/DESIGN.md](docs/DESIGN.md)

---

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| `/v1/chat` 401 | Wrong `PRIMARY_LLM_API_KEY` |
| `/metrics` 500 | `REDIS_URL` wrong or Valkey not reachable |
| `comparisons_completed` stays 0 | Worker not running or missing env vars |
| App crash on startup | Wrong `DATABASE_URL` password or SSL |
| Shadow never runs | Primary returned non-2xx (by design) |

Check **Runtime Logs** for both **web** and **worker** components in App Platform.

---

## License

MIT (or your org's license — update as needed)
