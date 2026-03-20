Help a new user set up their crawllmer development environment. Walk them through a guided questionnaire, generate the right `.env` file, install dependencies, and verify everything works.

## Before Starting

Read these files to understand the available options:

- `guides/environment.md` — all configuration variables, storage backends, Docker profiles
- `guides/deployment.md` — local, Docker, and distributed deployment options
- `.env.example` — template with all variables and inline documentation
- `Makefile` — all available make targets

## Questionnaire

Ask the user these questions **one at a time**. Use the answers to build their `.env` file.

### 1. Runtime mode

> How do you want to run crawllmer?
>
> - **(a) Local** — Python processes directly on your machine (`make run-dev`)
> - **(b) Docker** — Containerised via Docker Compose (`make docker-up`)
> - **(c) Docker distributed** — Postgres + Redis in Docker (`make distributed-up`)

If they pick (b) or (c), verify Docker is installed: `docker compose version`

### 2. Storage backend (skip if they chose (a) — default is SQLite)

> Which database backend?
>
> - **(a) SQLite** — zero setup, files created automatically (recommended for local dev)
> - **(b) PostgreSQL** — requires a running Postgres instance or Docker distributed mode

If they pick PostgreSQL and didn't choose Docker distributed in Q1, ask for connection details:
- Host, port, user, password, database name

### 3. Celery broker (skip if they chose (c) — distributed always uses Redis)

> Which Celery broker?
>
> - **(a) SQLite** — zero setup (recommended for local dev)
> - **(b) Redis** — requires a running Redis instance or Docker redis/distributed mode

If they pick Redis and aren't using Docker, ask for the Redis URL (default: `redis://localhost:6379/0`).

### 4. Log level

> Log level? (default: DEBUG)
>
> DEBUG / INFO / WARNING / ERROR

### 5. OpenTelemetry (optional)

> Want to enable OpenTelemetry export?
>
> - **(a) No** — telemetry prints to console (default)
> - **(b) Yes** — export to a collector

If yes, ask for the endpoint (default: `http://localhost:4317`). Mention they can run `make otel-up` to get a local OTEL stack with Jaeger/Prometheus/Grafana.

## Generate the .env file

Based on their answers:

1. Read `.env.example` as the template
2. Generate a `.env` file with their chosen values
3. For Docker distributed mode, also confirm `.env.local-distributed` exists (it ships with the repo)
4. Show the user what was generated and ask them to confirm

## Install and verify

Based on their runtime choice:

### Local mode
```bash
make sync
make run-dev
```
Then verify:
```bash
curl -s http://localhost:8000/health
# Open http://localhost:8501 for Streamlit UI
```

### Docker mode
```bash
make docker-up          # or make redis-up / make distributed-up
```
Then verify:
```bash
curl -s http://localhost:8000/health
# Open http://localhost:8501 for Streamlit UI
```

## After setup

Tell the user:
- Run `make check` before committing (format + lint + test)
- Run `make help` to see all available targets
- See `guides/` for detailed documentation on the pipeline, API, and deployment
- The Streamlit UI is at http://localhost:8501, API docs at http://localhost:8000/docs

## Key rules

- **One question at a time** — don't dump all questions at once
- **Always generate the .env file** — don't just tell them what to set
- **Verify the setup works** — run the health check after starting
- **Don't skip the questionnaire** — even if the user says "just set it up", walk through the questions so they understand their options
