# Architecture

## 1. System Context

```mermaid
C4Context
    title System Context — Shadow-Mode LLM Evaluator

    Person(client, "Client", "Application or test UI")
    System(api, "Shadow Evaluator API", "Proxies primary LLM, async shadow eval")
    System_Ext(primary, "Primary LLM", "Production model")
    System_Ext(candidate, "Candidate LLM", "Model under evaluation")
    SystemDb(valkey, "Valkey/Redis", "Queue + metrics")
    SystemDb(postgres, "PostgreSQL", "Request audit")

    Rel(client, api, "POST /v1/chat, GET /metrics")
    Rel(api, primary, "Sync HTTP")
    Rel(api, valkey, "Enqueue + metrics")
    Rel(api, postgres, "Stage requests")
    Rel(api, candidate, "Async via worker")
    Rel(api, valkey, "Worker consumes queue")
```

---

## 2. Container Diagram

```mermaid
flowchart TB
    subgraph Clients
        Browser[Test UI /test]
        App[Client App]
    end

    subgraph "App Platform — Web Container"
        FastAPI[FastAPI + Uvicorn]
        ProxySvc[PrimaryProxyService]
        LLMClient[PrimaryLlmClient]
    end

    subgraph "App Platform — Worker Container"
        ARQ[ARQ Worker]
        ShadowSvc[ShadowService]
        CandClient[CandidateLlmClient]
        Eval[Evaluator]
    end

    subgraph "Managed Data"
        PG[(PostgreSQL<br/>proxy_requests)]
        VK[(Valkey<br/>arq:queue + metrics:*)]
    end

    subgraph "External APIs"
        Primary[Primary LLM]
        Candidate[Candidate LLM]
    end

    Browser --> FastAPI
    App --> FastAPI
    FastAPI --> ProxySvc
    ProxySvc --> LLMClient
    LLMClient --> Primary

    ProxySvc -.->|background| PG
    ProxySvc -.->|background| VK

    VK --> ARQ
    ARQ --> ShadowSvc
    ShadowSvc --> PG
    ShadowSvc --> CandClient
    CandClient --> Candidate
    ShadowSvc --> Eval
    ShadowSvc --> VK

    FastAPI -->|GET /metrics| VK
```

---

## 3. Primary Request Flow

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant Route as chat.py
    participant Service as PrimaryProxyService
    participant LLM as Primary LLM
    participant BG as Background Task

    Client->>Route: POST /v1/chat
    Route->>Service: handle_chat(request_id, body)
    Service->>LLM: forward(body)
    LLM-->>Service: status + body
    Service-->>Route: PrimaryProxyResult
    Service--)BG: create_task(side_effects)
    Route-->>Client: response + X-Request-ID

    Note over BG: Non-blocking — failures logged only
    BG->>BG: save DB, metrics, enqueue if 2xx
```

---

## 4. Shadow Worker Flow

```mermaid
sequenceDiagram
    autonumber
    participant Q as Valkey/ARQ
    participant Worker as process_shadow_request
    participant DB as PostgreSQL
    participant Cand as Candidate LLM
    participant Eval as Evaluator
    participant M as Metrics

    Q->>Worker: job(request_id)
    Worker->>DB: get proxy_requests row
    Worker->>DB: mark processing
    Worker->>Cand: complete(request_body)
    Cand-->>Worker: candidate response
    Worker->>Eval: compare(primary, candidate)
    Eval-->>Worker: match result
    Worker->>DB: save shadow results
    Worker->>M: record_comparison
```

**Order matters:** Candidate LLM is called **before** the evaluator runs.

---

## 5. Component Responsibilities

| Component | Process | Responsibility |
|-----------|---------|----------------|
| `app/api/routes/chat.py` | Web | HTTP in/out for `/v1/chat` |
| `PrimaryProxyService` | Web | Primary call + schedule side-effects |
| `PrimaryLlmClient` | Web | httpx forward to upstream |
| `ShadowQueue` | Web (BG) | ARQ enqueue + load shedding |
| `MetricsStore` | Web + Worker | Redis counters |
| `ShadowService` | Worker | Full shadow job lifecycle |
| `CandidateLlmClient` | Worker | httpx to candidate model |
| `evaluator/` | Worker | JSON + action extraction/match |

---

## 6. Infrastructure (Production)

| Resource | DigitalOcean Product | Purpose |
|----------|---------------------|---------|
| Web service | App Platform | `uvicorn app.main:app --host 0.0.0.0 --port 8080` |
| Worker | App Platform | `arq worker.main.WorkerSettings` |
| Database | Managed PostgreSQL | `proxy_requests` table |
| Cache/Queue | Managed Valkey | ARQ queue + live metrics |
| LLM | Serverless Inference | Primary + candidate models |

### Environment split

| Variable | Web | Worker |
|----------|-----|--------|
| `DATABASE_URL` | ✅ | ✅ |
| `REDIS_URL` | ✅ | ✅ |
| `PRIMARY_LLM_*` | ✅ | ✅ (worker may reuse for config) |
| `CANDIDATE_LLM_*` | optional | ✅ |
| `PORT` | ✅ | — |

---

## 7. Database Strategy

| Environment | Driver | Connection |
|-------------|--------|------------|
| Local dev | SQLite | `sqlite+aiosqlite:///./data/shadow_evaluator.db` |
| Production | PostgreSQL | `postgresql+asyncpg://...` with SSL |

Schema bootstrapped via `init_db()` on startup (`Base.metadata.create_all`).

**What goes where:** PostgreSQL stores per-request audit (`proxy_requests`); Valkey/Redis stores the ARQ queue and live metrics counters. See [DATA.md](DATA.md) for full schema and write timeline.

---

## 8. Observability

| Signal | Where |
|--------|-------|
| Structured logs | stdout → App Platform Runtime Logs |
| Live metrics | `GET /metrics` (Redis counters) |
| Health | `GET /health` |
| Request tracing | `X-Request-ID` on every chat response |

Log format: `timestamp LEVEL [module] message` with `request_id=` in key paths.
