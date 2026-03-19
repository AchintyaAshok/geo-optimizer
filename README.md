# crawllmer

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Celery](https://img.shields.io/badge/Celery-Task%20Queue-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![uv](https://img.shields.io/badge/uv-package%20manager-DE5FE9?logo=astral&logoColor=white)](https://docs.astral.sh/uv/)
[![Ruff](https://img.shields.io/badge/ruff-linter%20%2B%20formatter-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)

A queue-driven web application that generates spec-compliant [llms.txt](https://llmstxt.org/) files for any website. Input a URL, and crawllmer discovers pages, extracts metadata, scores quality, and produces a downloadable `llms.txt` — all through a REST API or Streamlit UI.

## Quick Start

```bash
uv sync                   # install dependencies
make run-dev              # start API + Streamlit UI + Celery worker
```

Verify it's running:

```bash
curl -s http://localhost:8000/health          # → {"status": "ok"}
open http://localhost:8501                     # Streamlit UI
```

### Generate an llms.txt

```bash
# 1. Enqueue a crawl
curl -X POST http://localhost:8000/api/v1/crawls \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com"}'
# → {"run_id": "<RUN_ID>", "status": "queued"}

# 2. Process it (synchronous — returns when done)
curl -X POST http://localhost:8000/api/v1/crawls/<RUN_ID>/process
# → {"run_id": "...", "status": "completed", "score": 0.85, "score_breakdown": {...}}

# 3. Download the result
curl http://localhost:8000/api/v1/crawls/<RUN_ID>/llms.txt
```

Or use the Streamlit UI at `http://localhost:8501` — paste a URL, click **Crawl**, and watch the pipeline stages progress in real time.

## How It Works

crawllmer runs a five-stage pipeline for every URL:

```
URL → Discovery → Extraction → Canonicalization → Scoring → Generation → llms.txt
```

1. **Discovery** — Probes `/llms.txt`, `robots.txt`, `sitemap.xml`, then falls back to the seed URL
2. **Extraction** — Fetches each discovered page and extracts titles and descriptions from `<head>` meta, Open Graph, Twitter cards, and JSON-LD
3. **Canonicalization** — Normalizes URLs and deduplicates entries, keeping the highest-confidence metadata
4. **Scoring** — Computes a quality score: `(coverage × 0.4) + (confidence × 0.4) + (redundancy × 0.2)`
5. **Generation** — Builds a deterministic, sorted `llms.txt` document conforming to the [spec](https://llmstxt.org/)

Full pipeline details: **[guides/pipeline.md](guides/pipeline.md)**

## Running the Server

### Local Development

```bash
make run-api              # FastAPI on :8000
make run-ui               # Streamlit on :8501
make run-worker           # Celery worker (SQLite broker)
make run-dev              # All three together
```

The default configuration uses SQLite for everything — the app database, Celery broker, and result backend. No external services required.

### Docker

```bash
docker compose up --build                     # API + worker (SQLite Celery broker)
curl http://localhost:8000/health             # verify
```

### Docker + Redis

For production-like setups with Redis as the Celery broker:

```bash
docker compose -f docker-compose.yml -f docker-compose.redis.yml up --build
```

This adds a Redis container and routes Celery through it instead of SQLite.

Full deployment guide: **[guides/deployment.md](guides/deployment.md)**

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/crawls` | Enqueue a crawl (`{"url": "https://..."}`) |
| `POST` | `/api/v1/crawls/{run_id}/process` | Execute the pipeline synchronously |
| `GET` | `/api/v1/crawls/{run_id}` | Get run status and score |
| `GET` | `/api/v1/crawls/{run_id}/llms.txt` | Download generated llms.txt |
| `GET` | `/api/v1/history` | List recent runs (optional `?host=` filter) |

Full API details with request/response shapes: **[guides/api.md](guides/api.md)**

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` to override defaults:

```bash
cp .env.example .env
```

| Variable | Default | Purpose |
|----------|---------|---------|
| `CRAWLLMER_DB_URL` | `sqlite:///./crawllmer.db` | Application database |
| `CRAWLLMER_CELERY_BROKER_URL` | `sqla+sqlite:///./celery-broker.db` | Celery broker URL |
| `CRAWLLMER_CELERY_RESULT_BACKEND` | `db+sqlite:///./celery-results.db` | Celery result backend |
| `CRAWLLMER_WORKER_POLL_SECONDS` | `2` | Worker polling interval |

For Redis: set broker to `redis://localhost:6379/0` and result backend to `redis://localhost:6379/1`.

## Architecture

The project follows a **hexagonal architecture** (ports & adapters):

```
                    ┌───────────────────────────────────────────┐
                    │             Interface Layer                │
                    │                                           │
                    │   FastAPI (REST API)    Streamlit (UI)     │
                    └──────────┬────────────────────┬───────────┘
                               │                    │
                    ┌──────────▼────────────────────▼───────────┐
                    │           Application Core                │
                    │                                           │
                    │   CrawlPipeline    Workers    Scheduler   │
                    │   RetryPolicy      Observability          │
                    └──────────┬────────────────────┬───────────┘
                               │                    │
               ┌───────────────▼──────┐  ┌──────────▼──────────┐
               │    Domain Layer      │  │    Adapters          │
               │                      │  │                      │
               │  Models (Pydantic)   │  │  SqliteCrawlRepo     │
               │  Ports (ABCs)        │  │  CeleryQueuePublisher│
               └──────────────────────┘  └──────────────────────┘
```

Source code in `src/crawllmer/`:

```
src/crawllmer/
├── domain/          # models.py, ports.py — pure domain logic and abstract interfaces
├── application/     # orchestrator.py, workers.py, queueing.py, scheduler.py, retry.py, observability.py
├── adapters/        # storage.py — SQLModel/SQLite persistence
├── web/             # app.py (FastAPI), streamlit_app.py (Streamlit UI), runtime.py
├── main.py          # FastAPI entrypoint
├── celery_app.py    # Celery config & task definitions
└── worker.py        # Celery worker entrypoint
```

Full architecture documentation: **[docs/architecture.md](docs/architecture.md)**

## Design Decisions

- **Hexagonal architecture** — Domain and application logic have zero imports from web or storage layers. Adapters implement abstract ports, so you can swap SQLite for Postgres or Celery for any queue without touching business logic.

- **Hierarchical discovery** — Instead of blindly crawling, we check `/llms.txt` first (the source of truth), then `robots.txt` hints, then `sitemap.xml`, and only fall back to the seed URL. This respects existing llms.txt files and produces better results.

- **Confidence-scored extraction** — Every metadata extraction (title, description) carries a confidence score based on its source. `<title>` tags get 1.0, Open Graph gets 0.8, JSON-LD gets 0.6. During deduplication, the highest-confidence entry wins.

- **Deterministic output** — `llms.txt` entries are sorted by URL, making output reproducible and diffable.

- **SQLite everywhere** — SQLite serves as the app database, Celery broker, and result backend. Zero external dependencies for local dev. Redis is available as a compose extension for production.

- **Work-item state machine** — Every pipeline stage is tracked as a work item with `queued → processing → completed/failed` transitions and an event audit trail.

More on architecture and design: **[docs/architecture.md](docs/architecture.md)** and **[docs/design_decisions.md](docs/design_decisions.md)**

## Testing

```bash
make test                 # run all tests
make check                # format + lint + test (quality gate)
```

Run a single test:

```bash
uv run pytest tests/unit/test_workers.py::test_extracts_title_and_description_from_head_meta -v -s
```

Test structure:

```
tests/
├── conftest.py                  # Shared fixtures, test DB cleanup
├── unit/
│   ├── test_models.py           # Domain model state machine, serialization
│   ├── test_orchestrator.py     # Pipeline orchestration logic
│   └── test_workers.py          # Discovery, extraction, scoring functions
└── integration/
    ├── test_api.py              # FastAPI endpoint tests
    └── test_pipeline_flow.py    # End-to-end pipeline with mocked HTTP
```

## Development

```bash
make sync                 # install/sync dependencies
make format               # auto-format with ruff
make lint                 # lint with ruff
make check                # format → lint → test (run before committing)
make clean                # remove venv, caches, and DB files
make stop                 # kill running server processes
make restart              # stop → clean DBs → start fresh
```

Full Makefile reference: run `make help` or see the [Makefile](Makefile) (all targets are commented).

### Code Style

- **Formatter/Linter**: Ruff (line-length 88, target py312)
- **Lint rules**: E (errors), F (pyflakes), I (isort), N (naming), UP (upgrades)
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) — `type(scope): imperative description`

## Guides

| Guide | Description |
|-------|-------------|
| [Pipeline](guides/pipeline.md) | Deep dive into the five-stage processing pipeline |
| [API Reference](guides/api.md) | Complete API documentation with request/response examples |
| [Deployment](guides/deployment.md) | Local, Docker, and Redis deployment options |

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System architecture, hexagonal design, and runtime topology |
| [Design Decisions](docs/design_decisions.md) | Trade-offs and rationale behind key technical choices |
| [Project Requirements](docs/project_requirements.md) | Original assignment specification |
| [PRDs](prd/) | Product requirement documents for each feature area |

## Keeping Docs Up to Date

This project includes a Claude Code slash command for refreshing documentation after code changes:

```
/proj-refresh-docs
```

It reads the current source code, diffs against the existing docs, and surgically updates only what's stale — README sections, guides, docs, and Makefile comments. See [`.claude/commands/proj-refresh-docs.md`](.claude/commands/proj-refresh-docs.md) for the full specification including README structure rules, guides vs docs guidelines, and negative examples.
