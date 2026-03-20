# Environment & Configuration Guide

All configuration is managed through environment variables with the `CRAWLLMER_` prefix, loaded via [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) in `src/crawllmer/core/config.py`.

## Quick Setup

```bash
cp .env.example .env    # SQLite defaults — works out of the box
make run-dev             # start everything locally
```

No external services required. SQLite handles the app database, Celery broker, and result backend.

## Environment Files

| File | Purpose | Used with |
|------|---------|-----------|
| `.env` | Local development defaults (SQLite) | `make run-dev` |
| `.env.example` | Template with all variables documented | Copy to `.env` |
| `.env.redis` | Redis broker, SQLite DB | `make redis-up` |
| `.env.local-distributed` | Postgres + Redis (production-like) | `make distributed-up` |

## Storage Backends

### SQLite (default)

Zero-config. Database files created automatically in the project root.

```env
CRAWLLMER_STORAGE_BACKEND=sqlite
CRAWLLMER_DB_URL=sqlite:///./crawllmer.db
```

### PostgreSQL

Set `CRAWLLMER_STORAGE_BACKEND=pgsql` and provide all credential fields. The app assembles the connection URL from parts and validates at startup — missing fields cause a clear error.

```env
CRAWLLMER_STORAGE_BACKEND=pgsql
CRAWLLMER_PG_HOST=localhost
CRAWLLMER_PG_PORT=5432
CRAWLLMER_PG_USER=crawllmer
CRAWLLMER_PG_PASSWORD=crawllmer
CRAWLLMER_PG_DATABASE=crawllmer
```

When `storage_backend=pgsql`, the `CRAWLLMER_DB_URL` field is ignored — the URL is built from the `PG_*` fields.

## Celery Broker

### SQLite (default)

```env
CRAWLLMER_CELERY_BROKER_URL=sqla+sqlite:///./celery-broker.db
CRAWLLMER_CELERY_RESULT_BACKEND=db+sqlite:///./celery-results.db
```

### Redis

```env
CRAWLLMER_CELERY_BROKER_URL=redis://localhost:6379/0
CRAWLLMER_CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

## All Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CRAWLLMER_STORAGE_BACKEND` | `sqlite` | Database backend: `sqlite` or `pgsql` |
| `CRAWLLMER_DB_URL` | `sqlite:///./crawllmer.db` | SQLite connection URL (ignored when `pgsql`) |
| `CRAWLLMER_PG_HOST` | — | Postgres host (required when `pgsql`) |
| `CRAWLLMER_PG_PORT` | `5432` | Postgres port |
| `CRAWLLMER_PG_USER` | — | Postgres user (required when `pgsql`) |
| `CRAWLLMER_PG_PASSWORD` | — | Postgres password (required when `pgsql`) |
| `CRAWLLMER_PG_DATABASE` | — | Postgres database name (required when `pgsql`) |
| `CRAWLLMER_CELERY_BROKER_URL` | `sqla+sqlite:///./celery-broker.db` | Celery message broker |
| `CRAWLLMER_CELERY_RESULT_BACKEND` | `db+sqlite:///./celery-results.db` | Celery result storage |
| `CRAWLLMER_CELERY_TASK_ACKS_LATE` | `true` | Ack tasks after completion (redelivery on worker crash) |
| `CRAWLLMER_CELERY_TASK_REJECT_ON_WORKER_LOST` | `true` | Reject tasks back to queue if worker is killed |
| `CRAWLLMER_CELERY_BROKER_VISIBILITY_TIMEOUT` | `3600` | Redis: redelivery timeout for unacked tasks (seconds) |
| `CRAWLLMER_LOG_LEVEL` | `DEBUG` | Logging severity |
| `CRAWLLMER_WORKER_POLL_SECONDS` | `2` | Worker polling interval |
| `CRAWLLMER_API_BASE_URL` | `http://localhost:8000` | API URL for the Streamlit UI |
| `CRAWLLMER_UI_REFRESH_SECONDS` | `2` | Streamlit UI polling interval |
| `CRAWLLMER_SPIDER_MAX_DEPTH` | `3` | Max link hops for fallback spider |
| `CRAWLLMER_SPIDER_MAX_SCAN_PAGES` | `100` | Max pages to scan in spider Phase 1 |
| `CRAWLLMER_SPIDER_MAX_INDEX_PAGES` | `50` | Max pages to index in spider Phase 2 |
| `CRAWLLMER_SPIDER_INCLUDE_EXTENSIONS` | `.html,.htm,.txt,.md,` | Extensions to index (trailing comma = extensionless) |
| `CRAWLLMER_SPIDER_TIMEOUT_PER_PAGE` | `5` | Per-page timeout in seconds |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTEL collector endpoint (unset = console export) |

## Docker Compose Profiles

The `docker-compose.yml` uses profiles to toggle infrastructure services. App services (api, worker, ui) always start.

### Default — SQLite everything

```bash
make docker-up
# or: docker compose up --build
```

### Redis broker only

Adds Redis for Celery. App database stays SQLite.

```bash
make redis-up
# or: docker compose --profile redis --env-file .env.redis up --build
```

### Distributed — Postgres + Redis

Production-like setup with Postgres for the app DB and Redis for Celery.

```bash
make distributed-up
# or: docker compose --profile distributed --env-file .env.local-distributed up --build
```

### Full stack — Distributed + Observability

Everything above plus OTEL Collector, Jaeger, Prometheus, and Grafana.

```bash
make otel-up
```

| Service | Port | UI |
|---------|------|----|
| API | 8000 | `/health`, `/docs` |
| Streamlit | 8501 | Web UI |
| Jaeger | 16686 | Trace viewer |
| Prometheus | 9090 | Metrics |
| Grafana | 3000 | Dashboards |

## OpenTelemetry

When `OTEL_EXPORTER_OTLP_ENDPOINT` is set, traces, metrics, and logs are exported via OTLP gRPC to the configured collector. When unset, telemetry prints to stdout (console exporters).

```env
# Send to local collector
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Or in Docker (otel-collector service name)
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

Auto-instrumented: FastAPI, httpx, Celery, SQLite3. Custom pipeline telemetry via `PipelineTelemetry` in `core/observability/`.
