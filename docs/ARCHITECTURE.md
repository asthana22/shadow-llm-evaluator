# Architecture

## System overview

```mermaid
flowchart TB
    Client -->|POST /v1/chat| API[FastAPI Server]
    Client -->|GET /metrics| API

    API -->|sync httpx| Primary[Primary LLM]
    Primary --> API
    API -->|return immediately| Client

    API -->|enqueue ARQ job| Queue[(Redis)]
    Queue --> Worker[ARQ Worker Pool]
    Worker -->|same body| Candidate[Candidate LLM]
    Worker --> Evaluator[Heuristic Evaluator]
    Evaluator --> Metrics[(Redis Counters)]
    Evaluator -->|optional| PG[(PostgreSQL / SQLite Audit)]

    API -->|read| Metrics
```

## DigitalOcean deployment

- **App Platform Web** — `uvicorn app.main:app`
- **App Platform Worker** — `arq worker.main.WorkerSettings`
- **Managed Redis** — queue + metrics
- **Managed PostgreSQL** — production audit log

## Database strategy

| Environment | Driver | ORM URL |
|-------------|--------|---------|
| Local | SQLite | `sqlite+aiosqlite:///./data/shadow_evaluator.db` |
| Production | PostgreSQL | `postgresql+asyncpg://...` |

Tables created via SQLAlchemy `Base.metadata.create_all` (run migrations script).
