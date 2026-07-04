# Design Decisions

This file summarizes core contracts. For the **full interview-ready design document** (diagrams, sequences, trade-offs), see **[docs/DESIGN.md](docs/DESIGN.md)**.

## Stack

- **Python 3.11+** with **FastAPI**
- **Valkey/Redis + ARQ** for async shadow job queue
- **SQLAlchemy 2 async** for SQLite (local) and PostgreSQL (production)

## Core contract

- Primary path is **sync** — user never waits for candidate LLM
- Shadow path is **async** — enqueued after primary 2xx response
- Side-effects (DB, metrics, queue) run in **background tasks** — never fail the user response
- Comparison runs only after **candidate response** is received

## Heuristics

1. Valid JSON with an `action` key (extracted from chat completion content)
2. Exact action match: `primary.action == candidate.action`

## Key configs

| Variable | Purpose |
|----------|---------|
| `SHADOW_MAX_CONCURRENCY` | Max parallel shadow jobs (worker) |
| `SHADOW_MAX_QUEUE_SIZE` | Load shedding threshold |

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Deployment](docs/DEPLOYMENT.md)
- [README](README.md)
