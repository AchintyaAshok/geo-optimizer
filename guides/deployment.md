# Deployment Guide

crawllmer has three runtime processes and supports local, Docker, and Redis-backed deployments.

## Processes

| Process | Command | Port | Purpose |
|---------|---------|------|---------|
| **API** | `make run-api` | 8000 | FastAPI REST server |
| **UI** | `make run-ui` | 8501 | Streamlit web interface |
| **Worker** | `make run-worker` | — | Celery task worker |

All three share the same database and can run independently or together with `make run-dev`.

## Local Development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

### Install and Run

```bash
uv sync               # install dependencies
make run-dev           # start all three processes
```

`make run-dev` launches API, UI, and worker in parallel. `Ctrl-C` stops all of them.

Alternatively, run each in its own terminal:

```bash
# Terminal 1
make run-api

# Terminal 2
make run-ui

# Terminal 3
make run-worker
```

### Default Configuration

Out of the box, everything uses SQLite:

| Variable | Default |
|----------|---------|
| `CRAWLLMER_DB_URL` | `sqlite:///./crawllmer.db` |
| `CRAWLLMER_CELERY_BROKER_URL` | `sqla+sqlite:///./celery-broker.db` |
| `CRAWLLMER_CELERY_RESULT_BACKEND` | `db+sqlite:///./celery-results.db` |

No external services required. Database files are created automatically in the project root.

### Resetting State

```bash
make clean-db          # delete SQLite database files
make restart           # stop processes, wipe DBs, start fresh
make clean             # delete venv, caches, and DB files (run `make sync` after)
```

## Docker

### SQLite-Backed (Baseline)

```bash
docker compose up --build
```

This starts:
- **api** — FastAPI on port 8000 with a healthcheck at `/health`
- **worker** — Celery worker, starts after the API is healthy

Both containers share a Docker volume (`crawllmer-db`) for SQLite files at `/app/data/`.

Verify:
```bash
curl http://localhost:8000/health
```

### Redis-Backed

For higher throughput or multi-worker setups, add the Redis extension profile:

```bash
docker compose -f docker-compose.yml -f docker-compose.redis.yml up --build
```

This adds:
- **redis** — Redis 7 on port 6379
- **worker-redis** — A second worker using Redis for broker and result backend

The Redis worker uses:
- Broker: `redis://redis:6379/0`
- Result backend: `redis://redis:6379/1`

### Docker Environment Variables

The containers use the same environment variables as local development, pre-configured in the compose files to point to `/app/data/` paths:

```yaml
CRAWLLMER_DB_URL: sqlite:////app/data/crawllmer.db
CRAWLLMER_CELERY_BROKER_URL: sqla+sqlite:////app/data/celery-broker.db
CRAWLLMER_CELERY_RESULT_BACKEND: db+sqlite:////app/data/celery-results.db
```

Override with `-e` or an `--env-file` for custom configurations.

## Environment Variables Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `CRAWLLMER_DB_URL` | `sqlite:///./crawllmer.db` | SQLModel database URL |
| `CRAWLLMER_CELERY_BROKER_URL` | `sqla+sqlite:///./celery-broker.db` | Celery message broker |
| `CRAWLLMER_CELERY_RESULT_BACKEND` | `db+sqlite:///./celery-results.db` | Celery result storage |
| `CRAWLLMER_WORKER_POLL_SECONDS` | `2` | Worker polling interval (seconds) |

### Using Redis

To switch from SQLite to Redis for Celery:

```env
CRAWLLMER_CELERY_BROKER_URL=redis://localhost:6379/0
CRAWLLMER_CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

The application database (`CRAWLLMER_DB_URL`) always uses SQLite — only the Celery broker and result backend can be swapped to Redis.

## Process Management

```bash
make stop              # kill all running crawllmer processes
make restart           # stop → clean DBs → start fresh
```

`make stop` sends SIGTERM to uvicorn, streamlit, and worker processes by name. `make restart` chains stop, clean-db, and run-dev.
