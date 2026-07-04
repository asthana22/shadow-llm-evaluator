# Shadow-Mode LLM Evaluator API

Production-ready **FastAPI** proxy that serves customer traffic through a **primary LLM** while asynchronously routing the same requests to a **candidate LLM** for shadow evaluation.

## Stack

| Layer | Technology |
|-------|------------|
| API | **FastAPI** + Uvicorn |
| Queue | **Redis** + **ARQ** (async worker) |
| Metrics | Redis counters |
| DB (audit) | **SQLite** (local) / **PostgreSQL** (production) |
| ORM | SQLAlchemy 2 (async) |
| Deploy | DigitalOcean App Platform |

## Project Structure

```
shadow-llm-evaluator/
├── app/
│   ├── main.py                    # FastAPI app entry
│   ├── config.py                  # Pydantic settings
│   ├── api/routes/                # /v1/chat, /metrics, /health
│   ├── proxy/                     # Primary LLM client
│   ├── shadow/                    # Shadow orchestration
│   ├── queue/                     # ARQ queue + load shedding
│   ├── evaluator/                 # JSON + action match heuristics
│   ├── metrics/                   # Redis counters
│   ├── db/
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── client.py              # Async engine/session
│   │   ├── repositories/          # Data access (SQL)
│   │   └── services/              # Audit business logic
│   └── types/                     # Pydantic models
├── worker/
│   └── main.py                    # ARQ worker entry
├── tests/
│   ├── unit/
│   └── integration/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── requirements.txt
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/chat` | Proxy to primary LLM; shadow eval enqueued async |
| GET | `/metrics` | Real-time evaluation metrics |
| GET | `/health` | Health check |

## Quick Start (local)

```bash
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Create SQLite tables
python -m app.db.repositories.shadow_evaluation_repository

docker compose up -d redis postgres

# Terminal 1 — API
uvicorn app.main:app --reload --port 8080

# Terminal 2 — shadow worker (Phase 4)
arq worker.main.WorkerSettings

pytest -v
```

## Database

| Environment | Config |
|-------------|--------|
| Local | `DB_DRIVER=sqlite` + `SQLITE_PATH=./data/shadow_evaluator.db` |
| Production | `DB_DRIVER=postgres` + `DATABASE_URL=postgresql://...` |

## Implementation Order

1. Primary proxy (`POST /v1/chat`)
2. Evaluator heuristics (unit tests)
3. Metrics (`GET /metrics`)
4. Redis queue + ARQ shadow worker
5. Bounded concurrency + load shedding
6. PostgreSQL audit (optional)
7. CI + DigitalOcean deploy

See [DESIGN.md](./DESIGN.md) for contracts and [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) for DigitalOcean setup.
