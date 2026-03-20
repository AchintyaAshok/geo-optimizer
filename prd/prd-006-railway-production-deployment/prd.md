# PRD 006: Railway Production Deployment

## Overview

Deploy crawllmer as a live, publicly accessible application on Railway to satisfy the assignment deliverable: "A live, deployed version of the application. Deploy to a hosting platform of your choice."

The current stack runs locally via Docker Compose. This PRD covers deploying to Railway with Postgres (replacing SQLite), Redis (Celery broker), and the existing OTEL observability stack — producing a production-grade deployment.

### Why Railway

- Runs our entire stack (persistent processes for Celery workers and Streamlit)
- One-click Redis and Postgres plugins
- Private networking between services (`.railway.internal` DNS)
- Docker-based deploys from GitHub
- No serverless limitations (Vercel can't run Celery, SQLite, or Streamlit)

### What Already Exists (from main merge)

Much of the infrastructure work is already done:

| Component | Status | Location |
|-----------|--------|----------|
| Pydantic Settings | **Done** | `src/crawllmer/config.py` — `Settings(BaseSettings)` with `CRAWLLMER_` prefix |
| OTEL SDK bootstrap | **Done** | `src/crawllmer/core/observability/telemetry_setup.py` — dual-mode OTLP gRPC / console |
| Auto-instrumentation | **Done** | FastAPI, httpx, Celery, SQLite3 — all wired up |
| OTEL Collector config | **Done** | `infra/otel-collector-config.yaml` — receives gRPC :4317, exports to Jaeger + Prometheus |
| Observability Docker stack | **Done** | `docker-compose.observability.yml` — Collector, Jaeger, Prometheus, Grafana |
| Settings in app/web/runtime.py | **Done** | Uses `get_settings()` instead of `os.getenv()` |
| Settings in app/indexer/app.py | **Done** | Uses `get_settings()` instead of `os.getenv()` |

## Linked Tickets

| Ticket | Title | Status |
|--------|-------|--------|
| PRD-001 | Observability Stack | Complete |
| PRD-003 | Web UI & API | Complete |
| PRD-004 | Persistence & Delivery | Complete |
| PRD-006 (other) | Core Module Error Handling | Complete |

## Measures of Success

- [ ] All 3 app services (API, Worker, UI) running and accessible via public Railway URLs
- [ ] A user can submit a URL via Streamlit UI and receive a generated llms.txt
- [ ] A user can submit a URL via the FastAPI API and retrieve the result
- [ ] `/health` endpoint returns 200
- [ ] Celery worker processes tasks via Redis broker
- [ ] Data persists in Railway Postgres
- [ ] OTEL traces from pipeline runs are visible in Jaeger dashboard on Railway
- [ ] Deployment is reproducible from a single `git push` to GitHub

## Low Effort Version

### Architecture

```
┌──────────────────── Railway Project ─────────────────────────┐
│                                                               │
│  ┌────────┐  ┌────────┐  ┌──────────┐                       │
│  │  API   │  │ Worker │  │    UI    │                       │
│  │FastAPI │  │ Celery │  │Streamlit │                       │
│  │ :8000  │  │        │  │  :8501   │                       │
│  └───┬────┘  └───┬────┘  └──────────┘                       │
│      │           │                                            │
│      └─────┬─────┘                                            │
│            │ OTLP gRPC :4317                                  │
│            ▼                                                  │
│  ┌──────────────┐  ┌───────────┐                             │
│  │    OTEL      │  │  Jaeger   │                             │
│  │  Collector   │─►│  :16686   │                             │
│  │   :4317      │  └───────────┘                             │
│  └──────┬───────┘                                             │
│         │                                                     │
│         ▼                                                     │
│  ┌──────────────┐                                             │
│  │ Prometheus   │  (optional — can defer)                    │
│  │   :9090      │                                             │
│  └──────────────┘                                             │
│                                                               │
│  ┌──────────┐  ┌──────────────┐                              │
│  │  Redis   │  │  PostgreSQL  │                              │
│  │ (plugin) │  │   (plugin)   │                              │
│  └──────────┘  └──────────────┘                              │
│                                                               │
│  7-8 services total (Prometheus optional)                     │
└───────────────────────────────────────────────────────────────┘
```

### Services

| # | Service | Type | Start Command | Port | Notes |
|---|---------|------|---------------|------|-------|
| 1 | **API** | App (Dockerfile) | `uv run uvicorn crawllmer.app.api.main:app --host 0.0.0.0 --port 8000` | 8000 (public) | Healthcheck on `/health` |
| 2 | **Worker** | App (Dockerfile) | `uv run python -m crawllmer.app.indexer` | none | Background process |
| 3 | **UI** | App (Dockerfile) | `uv run streamlit run src/crawllmer/app/web/streamlit_app.py --server.port 8501 --server.address 0.0.0.0` | 8501 (public) | Streamlit frontend |
| 4 | **Redis** | Railway Plugin | managed | 6379 (private) | Celery broker + result backend |
| 5 | **PostgreSQL** | Railway Plugin | managed | 5432 (private) | App database (replaces SQLite) |
| 6 | **OTEL Collector** | Docker image | `otel/opentelemetry-collector-contrib:0.120.0` | 4317 (private) | Receives gRPC, exports to Jaeger + Prometheus |
| 7 | **Jaeger** | Docker image | `jaegertracing/jaeger:2` | 16686 (public) | Trace visualization UI |
| 8 | **Prometheus** | Docker image (optional) | `prom/prometheus:latest` | 9090 (private or public) | Metrics storage — can defer to later |

### What Needs To Be Built

| File | Change | Purpose |
|------|--------|---------|
| `Dockerfile` | **New** | Single image for API, Worker, UI — `python:3.12-slim` + uv |
| `src/crawllmer/core/config.py` | **Modify** | Add `storage_backend`, `pg_*` fields, `model_validator`, and `engine_kwargs` property |
| `src/crawllmer/adapters/storage.py` | **Refactor** | Extract shared SQLAlchemy logic into `SqlAlchemyCrawlRepository` base class; create `SqliteCrawlRepository` and `PostgresCrawlRepository` subclasses; add `get_storage()` factory |
| `pyproject.toml` | **Modify** | Add `psycopg2-binary` dependency |
| `docker-compose.postgres.yml` | **New** | Compose overlay for local Postgres dev (mirrors Railway setup) |
| `Makefile` | **Modify** | Add `run-postgres` target |
| `railway.toml` | **New** | Optional — per-service build/start config |
| `infra/otel-collector-config.yaml` | **No change** | Already configured for gRPC receive → Jaeger + Prometheus export |

### Settings Changes (`config.py`)

Add explicit storage backend selection with Pydantic validation:

```python
from pydantic import model_validator

class Settings(BaseSettings):
    # ── Storage ─────────────────────────────────────────────────
    storage_backend: Literal["sqlite", "pgsql"] = "sqlite"

    # SQLite (used when storage_backend == "sqlite")
    db_url: str = "sqlite:///./crawllmer.db"

    # Postgres (required when storage_backend == "pgsql")
    pg_host: str | None = None
    pg_port: int = 5432
    pg_user: str | None = None
    pg_password: str | None = None
    pg_database: str | None = None

    @model_validator(mode="after")
    def validate_storage_config(self) -> Settings:
        """Ensure Postgres credentials are provided when pgsql backend is selected."""
        if self.storage_backend == "pgsql":
            missing = [
                f for f in ("pg_host", "pg_user", "pg_password", "pg_database")
                if getattr(self, f) is None
            ]
            if missing:
                raise ValueError(
                    f"storage_backend='pgsql' requires: {', '.join(missing)}"
                )
            # Build the SQLAlchemy URL from explicit parts
            self.db_url = (
                f"postgresql://{self.pg_user}:{self.pg_password}"
                f"@{self.pg_host}:{self.pg_port}/{self.pg_database}"
            )
        return self

    @property
    def engine_kwargs(self) -> dict:
        """Return backend-appropriate SQLAlchemy engine args."""
        if self.storage_backend == "pgsql":
            return {"pool_pre_ping": True, "pool_size": 5}
        return {"connect_args": {"check_same_thread": False}}
```

**Key design decisions:**
- `CRAWLLMER_STORAGE_BACKEND` is an explicit `Literal["sqlite", "pgsql"]` — no URL sniffing
- Postgres requires `CRAWLLMER_PG_HOST`, `CRAWLLMER_PG_USER`, `CRAWLLMER_PG_PASSWORD`, `CRAWLLMER_PG_DATABASE` — validated at startup via `model_validator`
- `db_url` is assembled from parts for Postgres, kept as-is for SQLite
- App fails fast with a clear error if you set `storage_backend=pgsql` without credentials

### Storage Refactor (`adapters/storage.py`)

The abstract `CrawlRepository` interface already exists in `domain/ports.py`. The current `SqliteCrawlRepository` contains all query logic using SQLModel/SQLAlchemy — which is backend-agnostic. The refactor splits it into layers:

```
domain/ports.py
  CrawlRepository (ABC)              ← already exists, unchanged
      │
adapters/storage.py
  SqlAlchemyStorageRepository         ← NEW base class, gets all existing query logic
      ├── SqliteStorageRepository      ← SQLite engine config + check_same_thread
      └── PgSqlStorageRepository       ← NEW: Postgres engine config + pool settings

  get_storage(settings) → CrawlRepository   ← NEW factory, replaces default_repository()
```

**`SqlAlchemyStorageRepository`** (base): Takes an engine, contains all `create_run()`, `update_run()`, `list_work_items()` etc — the existing query code unchanged.

**`SqliteStorageRepository`**: Subclass that creates engine with `connect_args={"check_same_thread": False}` and handles the `OperationalError` race on `create_all()`.

**`PgSqlStorageRepository`**: Subclass that creates engine with `pool_pre_ping=True`, `pool_size=5`.

**`get_storage(settings=None)`**: Factory function that reads `settings.storage_backend` and returns the right subclass. Replaces `default_repository()`.

```python
def get_storage(settings: Settings | None = None) -> CrawlRepository:
    settings = settings or get_settings()
    if settings.storage_backend == "pgsql":
        return PgSqlStorageRepository(db_url=settings.db_url)
    return SqliteStorageRepository(db_url=settings.db_url)
```

Callers (`app/web/runtime.py`, `app/indexer/app.py`) change from `default_repository(db_url=...)` to `get_storage()`. The settings object handles the rest.

### Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
COPY . .
# Default: API server. Overridden per Railway service.
CMD ["uv", "run", "uvicorn", "crawllmer.app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables (Railway)

**API + Worker + UI (shared):**
```
CRAWLLMER_STORAGE_BACKEND=pgsql
CRAWLLMER_PG_HOST=${{Postgres.RAILWAY_PRIVATE_DOMAIN}}
CRAWLLMER_PG_PORT=5432
CRAWLLMER_PG_USER=${{Postgres.PGUSER}}
CRAWLLMER_PG_PASSWORD=${{Postgres.PGPASSWORD}}
CRAWLLMER_PG_DATABASE=${{Postgres.PGDATABASE}}
CRAWLLMER_CELERY_BROKER_URL=redis://${{Redis.RAILWAY_PRIVATE_DOMAIN}}:6379/0
CRAWLLMER_CELERY_RESULT_BACKEND=redis://${{Redis.RAILWAY_PRIVATE_DOMAIN}}:6379/1
```

**API + Worker (OTEL-enabled):**
```
OTEL_EXPORTER_OTLP_ENDPOINT=http://${{OTEL Collector.RAILWAY_PRIVATE_DOMAIN}}:4317
```

### Local Postgres Development (`docker-compose.postgres.yml`)

New compose overlay for running with Postgres locally — mirrors the Railway setup:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: crawllmer
      POSTGRES_PASSWORD: crawllmer
      POSTGRES_DB: crawllmer
    ports:
      - "5432:5432"
    volumes:
      - crawllmer-pgdata:/var/lib/postgresql/data

  api:
    environment:
      CRAWLLMER_STORAGE_BACKEND: pgsql
      CRAWLLMER_PG_HOST: postgres
      CRAWLLMER_PG_USER: crawllmer
      CRAWLLMER_PG_PASSWORD: crawllmer
      CRAWLLMER_PG_DATABASE: crawllmer
    depends_on:
      - postgres

  worker:
    environment:
      CRAWLLMER_STORAGE_BACKEND: pgsql
      CRAWLLMER_PG_HOST: postgres
      CRAWLLMER_PG_USER: crawllmer
      CRAWLLMER_PG_PASSWORD: crawllmer
      CRAWLLMER_PG_DATABASE: crawllmer
    depends_on:
      - postgres

volumes:
  crawllmer-pgdata:
```

**Usage:** `docker compose -f docker-compose.yml -f docker-compose.postgres.yml up`

Add a corresponding Makefile target: `make run-postgres`

### OTEL on Railway

The existing observability stack maps directly to Railway services:

| Local (docker-compose.observability.yml) | Railway Service | Notes |
|------------------------------------------|----------------|-------|
| `otel-collector` | OTEL Collector service | Same image + config file. Mount `infra/otel-collector-config.yaml` |
| `jaeger` | Jaeger service | Same image. Public port 16686 for UI |
| `prometheus` | Prometheus service (optional) | Same image + config. Can defer — Jaeger alone covers traces |
| `grafana` | Deferred | Nice-to-have dashboards, not required for deliverable |

The OTEL SDK (`telemetry_setup.py`) already uses gRPC exporters and the `OTEL_EXPORTER_OTLP_ENDPOINT` env var — **no code changes needed**. Just set the env var to point at the collector's Railway internal address.

The OTEL Collector config (`infra/otel-collector-config.yaml`) needs one change: the Jaeger export endpoint must use Railway's private DNS instead of Docker Compose service name:
```yaml
# Change from:
exporters:
  otlp/jaeger:
    endpoint: jaeger:4317
# To (via env var substitution or Railway-specific config):
exporters:
  otlp/jaeger:
    endpoint: ${JAEGER_ENDPOINT}  # Set to ${{Jaeger.RAILWAY_PRIVATE_DOMAIN}}:4317
```

## High Effort Version

Everything in Low Effort, plus:

- **CI/CD pipeline**: GitHub Actions that runs `make check` before deploying to Railway
- **Grafana on Railway**: Dashboards for pipeline metrics alongside Jaeger traces
- **Custom domain**: `crawllmer.yourdomain.com` instead of `*.up.railway.app`
- **Staging environment**: Separate Railway project for pre-production testing
- **Health monitoring**: External uptime check (e.g., UptimeRobot) that pages on downtime

## Possible Future Extensions

- Multi-worker scaling (Railway supports horizontal scaling per service)
- Rate limiting / API keys for public API access
- Blob storage for generated llms.txt artifacts (instead of DB column)
- Auto-deploy preview environments per PR (Railway supports this)
- Explicitly deferred: Kubernetes, AWS/GCP, multi-region

## Approval State

| Status | Date | Notes |
|--------|------|-------|
| Draft | 2026-03-19 | Initial draft — updated after merging main (pydantic settings, OTEL stack already exist) |
| Approved | 2026-03-19 | Approved for task breakdown |
| In Progress | 2026-03-19 | Tasks 001-003 complete, Task 004 in progress (Railway project created, first deploy pending) |

## Task Status

| # | Task | State | Commit |
|---|------|-------|--------|
| 001 | Add psycopg2-binary dep and storage backend settings | **complete** | `9fa57e9` |
| 002 | Refactor storage module with backend-specific subclasses | **complete** | `a362384` |
| 003 | Create Dockerfile and docker-compose.postgres.yml | **complete** | `9859ace` |
| 004 | Configure Railway services and deploy | **in_progress** | — |
| 005 | Wire OTEL collector and Jaeger on Railway | pending | — |
| 006 | End-to-end verification and smoke test | pending | — |

## Session Notes (2026-03-19)

### Railway Project Setup

- GitHub repo: `AchintyaAshok/geo-optimizer`
- 5 services: API, Worker, UI (app), Redis + PostgreSQL (plugins)
- Auto-deploy disabled — manual deploy only until ready
- Per-service config-as-code in `railway/api/`, `railway/worker/`, `railway/ui/`
- Shared variables set at project level for Postgres + Redis + log level

### Deviations from Original Plan

1. **Task 003**: Used Docker Compose profiles (`--profile distributed`) instead of separate `docker-compose.postgres.yml` overlay file — cleaner approach
2. **Task 004**: Per-service `railway.toml` files in `railway/` subdirectories instead of a single root `railway.toml` — allows different start commands and healthcheck configs per service without dashboard overrides
3. **Task 004**: Railway has no infrastructure-as-code (Terraform-style) — databases, env vars, and service creation are manual via dashboard. `railway.toml` only covers build/deploy settings
