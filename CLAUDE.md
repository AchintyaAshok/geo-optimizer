# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**crawllmer** — A web application that generates [llms.txt](https://llmstxt.org/) files for websites. Users input a URL, the app crawls the site, extracts metadata (titles, descriptions, URLs), and produces a spec-compliant llms.txt file for download.

Python 3.12 project using `uv` as the package manager. Stack: FastAPI + Streamlit (dual UI), Celery task queue, SQLModel/SQLite persistence. The full assignment spec lives in `docs/project_requirements.md`; architecture diagrams in `docs/architecture.md`.

## Commands

```bash
make sync      # Install/sync dependencies (uv sync)
make test      # Run tests (uv run pytest -v -s)
make lint      # Lint (uv run ruff check .)
make format    # Auto-format (uv run ruff format .)
make check     # Format → lint → test (quality gate)

# Runtime
make run-api   # FastAPI on :8000 (PYTHONPATH=src)
make run-ui    # Streamlit on :8501
make run-dev   # Both simultaneously

# Docker
docker compose up               # API + worker (SQLite Celery broker)
docker compose -f docker-compose.yml -f docker-compose.redis.yml up  # + Redis broker
```

Run a single test: `uv run pytest tests/test_example.py::test_name -v -s`

## Code Style

- **Formatter/Linter**: Ruff (line-length 88, target py312)
- **Lint rules**: E (errors), F (pyflakes), I (isort), N (naming), UP (upgrades)
- **Commits**: Conventional Commits — `type(scope): imperative description`

## Architecture

Source code lives in `src/crawllmer/`, organised as hexagonal (ports & adapters):

```
src/crawllmer/
├── domain/          # models.py (Pydantic/SQLModel), ports.py (abstract interfaces)
├── application/     # orchestrator.py, workers.py, queueing.py, scheduler.py, retry.py, observability.py
├── adapters/        # storage.py (SQLModel/SQLite persistence)
├── web/             # app.py (FastAPI routes), streamlit_app.py (Streamlit UI), runtime.py (shared bootstrap)
├── main.py          # FastAPI entrypoint
├── celery_app.py    # Celery config & task definitions
└── worker.py        # Celery worker entrypoint (__main__)
```

**Processing pipeline** (Celery tasks): discovery → extraction → canonicalization → scoring → generation

## Testing

```
tests/
├── conftest.py                  # Shared fixtures
├── unit/                        # test_models.py, test_orchestrator.py, test_workers.py
└── integration/                 # test_api.py, test_pipeline_flow.py
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CRAWLLMER_DB_URL` | `sqlite:///./crawllmer.db` | App database |
| `CRAWLLMER_CELERY_BROKER_URL` | `sqla+sqlite:///./celery-broker.db` | Celery broker (use `redis://...` for Redis) |
| `CRAWLLMER_CELERY_RESULT_BACKEND` | `db+sqlite:///./celery-results.db` | Celery results (use `redis://...` for Redis) |
| `CRAWLLMER_WORKER_POLL_SECONDS` | `2` | Worker polling interval |

## Key Specs

- llms.txt specification: https://llmstxt.org/
- Output must conform to the spec (not just the examples at llmstxt.site)

## Skills & Agent Workflows

Skills are invoked via the `Skill` tool in Claude Code. Invoke a skill by name before starting related work.

### Project-Local Skills

#### `prd` — Product Requirements Documents
- **Trigger**: Planning features, "PRD", "plan", "requirements", "break this down", "create tasks"
- **What it does**: Scaffolds a `prd/` directory with numbered PRD documents and sequential tasks using bundled shell scripts (`new-prd.sh`, `new-task.sh`)
- **Workflow**: Create PRD → Draft sections → User approval → Break into tasks → Execute tasks serially
- **Key rules**: Always use bundled scripts; PRDs must be approved before tasks; tasks execute sequentially; each task has YAML frontmatter with state tracking (`pending` → `in_progress` → `complete`)

#### `version-control` — Git Commit Workflow
- **Trigger**: "commit", "push", "save my work", or after completing implementation work
- **What it does**: Analyzes working tree, groups changes into logical micro-commits with Conventional Commit messages
- **Key rules**: Never `git add .`; never auto-push; one concern per commit; tests get their own commit; always include `Co-Authored-By` trailer

### Global Skills (Superpowers)

| Skill | When to Use |
|-------|-------------|
| `superpowers:brainstorming` | **Before any creative work** — features, components, functionality changes |
| `superpowers:writing-plans` | When you have specs for a multi-step task, before writing code |
| `superpowers:executing-plans` | When you have a written plan to execute with review checkpoints |
| `superpowers:test-driven-development` | Before writing implementation code for any feature or bugfix |
| `superpowers:systematic-debugging` | When encountering bugs or test failures — before proposing fixes |
| `superpowers:verification-before-completion` | Before claiming work is done — requires running verification commands |
| `superpowers:requesting-code-review` | When completing tasks or before merging |
| `superpowers:receiving-code-review` | When processing code review feedback |
| `superpowers:dispatching-parallel-agents` | When facing 2+ independent tasks without shared state |
| `superpowers:subagent-driven-development` | When executing plans with independent tasks in current session |
| `superpowers:using-git-worktrees` | When feature work needs isolation from current workspace |
| `superpowers:finishing-a-development-branch` | When implementation is complete — merge, PR, or cleanup |
| `superpowers:writing-skills` | When creating or editing skills |

### Other Skills

| Skill | Purpose |
|-------|---------|
| `claude-md-management:claude-md-improver` | Audit and improve CLAUDE.md files |
| `claude-md-management:revise-claude-md` | Update CLAUDE.md with session learnings |
| `frontend-design` | Production-grade frontend interfaces |

### Recommended Workflow

1. `superpowers:brainstorming` → explore requirements
2. `prd` → create and approve a PRD
3. `superpowers:writing-plans` → detailed implementation plan if needed
4. `superpowers:test-driven-development` → implement each task with TDD
5. `version-control` → commit after each task
6. `superpowers:verification-before-completion` → verify before claiming done
7. Run `make check` before marking any task complete
