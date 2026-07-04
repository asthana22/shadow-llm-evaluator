# Deployment Guide

## DigitalOcean App Platform

Two components from the same Dockerfile:

| Component | Command |
|-----------|---------|
| Web | `uvicorn app.main:app --host 0.0.0.0 --port 8080` |
| Worker | `arq worker.main.WorkerSettings` |

### Environment variables

```
PRIMARY_LLM_URL
CANDIDATE_LLM_URL
REDIS_URL
DATABASE_URL
DB_DRIVER=postgres
SHADOW_MAX_CONCURRENCY=50
SHADOW_MAX_QUEUE_SIZE=500
ENABLE_AUDIT_LOG=false   # optional shadow_evaluations table — not wired in worker yet
```

### Data stores (production)

| Service | Purpose |
|---------|---------|
| **Managed PostgreSQL** | `proxy_requests` — request bodies, primary/candidate responses, evaluation results |
| **Managed Valkey** | ARQ job queue + `metrics:*` counters for `GET /metrics` |

See [DATA.md](DATA.md) for schema and write paths.

### Local parity

```bash
docker compose up --build
```

## CI

GitHub Actions runs `pytest` and `ruff` on every push.
