# Deployment Guide

crawllmer has three runtime processes and supports local, Docker, and distributed deployments.

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
make sync              # install dependencies
cp .env.example .env   # adjust values as needed
make run-dev           # start all three processes
```

`make run-dev` launches API, UI, and worker in parallel. `Ctrl-C` stops all of them.

### Default Configuration

Out of the box, everything uses SQLite — no external services required. See [guides/environment.md](environment.md) for all configuration options.

### Resetting State

```bash
make clean-db          # delete SQLite database files
make restart           # stop processes, wipe DBs, start fresh
make clean             # delete venv, caches, and DB files (run `make sync` after)
```

## Docker

### SQLite (default)

```bash
make docker-up
```

Starts api, worker, and ui containers. SQLite files stored in a Docker volume.

### Redis Broker

Adds Redis for Celery while keeping SQLite for the app database:

```bash
make redis-up
```

### Distributed (Postgres + Redis)

Production-like setup with Postgres and Redis:

```bash
make distributed-up
```

### Full Stack with Observability

Everything above plus OTEL Collector, Jaeger, Prometheus, and Grafana:

```bash
make full-stack-distributed-up
```

| Service | Port | Purpose |
|---------|------|---------|
| API | 8000 | REST endpoints |
| Streamlit | 8501 | Web UI |
| Jaeger | 16686 | Trace viewer |
| Prometheus | 9090 | Metrics |
| Grafana | 3000 | Dashboards |

### How Profiles Work

The `docker-compose.yml` uses Docker Compose profiles to toggle infrastructure:

- **No profile** → SQLite everything
- **`redis`** → adds Redis (Celery broker only)
- **`distributed`** → adds Redis + Postgres

App services (api, worker, ui) always start. Environment variables are injected via `--env-file`:

```bash
# Explicit form (equivalent to make targets)
docker compose --profile distributed --env-file .env.local-distributed up --build
```

See [guides/environment.md](environment.md) for env file details and all configuration variables.

## Process Management

```bash
make stop              # kill all running crawllmer processes
make restart           # stop → clean DBs → start fresh
```
