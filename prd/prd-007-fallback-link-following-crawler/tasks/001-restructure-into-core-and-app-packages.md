---
parent_prd: ../prd-007-fallback-link-following-crawler/prd.md
prd_name: "PRD 007: Fallback Link-Following Crawler"
prd_id: 007
task_id: 001
created: 2026-03-19
state: pending
---

# Task 001: Restructure into core and app packages

## Metadata

| Field | Value |
|-------|-------|
| PRD | [PRD 007: Fallback Link-Following Crawler](../prd.md) |
| Created | 2026-03-19 |
| State | pending |

## Changelog

| Date | Change |
|------|--------|
| 2026-03-19 | Task created |

## Objective

Reorganise the `src/crawllmer/` package from the current flat layout into the new `core/` + `app/{api,web,indexer}/` structure defined in the PRD. Eliminate the `application/` package entirely, move modules to their new homes, update every import across source and test files, and adjust all build/run tooling (Makefile, docker-compose, pyproject.toml) so the project boots and passes tests with the new structure.

## Inputs

- Current source tree under `src/crawllmer/` (application/, web/, adapters/, domain/, config.py, main.py, celery_app.py, worker.py)
- PRD migration path table mapping old locations to new locations
- Makefile, docker-compose.yml, docker-compose.redis.yml, pyproject.toml with current entrypoint references

## Outputs

- `src/crawllmer/core/` package containing config.py, orchestrator.py, retry.py, scheduler.py, scoring.py, generation.py, and observability/
- `src/crawllmer/app/api/` package containing main.py (FastAPI app + lifespan) and routes.py (endpoints)
- `src/crawllmer/app/web/` package containing streamlit_app.py and runtime.py
- `src/crawllmer/app/indexer/` package containing app.py (Celery instance), tasks.py, queueing.py, discovery.py, page_indexer.py, and __main__.py
- `src/crawllmer/application/` directory deleted
- Updated imports in all source files and test files
- Updated Makefile targets (run-api, run-worker, run-ui)
- Updated docker-compose service commands and pyproject.toml entrypoints

## Steps

1. Create the new directory structure: `core/`, `core/observability/`, `app/`, `app/api/`, `app/web/`, `app/indexer/` with `__init__.py` files
2. Move `application/orchestrator.py` to `core/orchestrator.py`
3. Move `application/retry.py` to `core/retry.py`
4. Move `application/scheduler.py` to `core/scheduler.py`
5. Split `application/workers.py`: extract scoring logic to `core/scoring.py`, generation logic to `core/generation.py`, discovery logic to `app/indexer/discovery.py`, extraction logic to `app/indexer/page_indexer.py`
6. Move `application/queueing.py` to `app/indexer/queueing.py`
7. Move `application/observability.py` and `application/telemetry_setup.py` to `core/observability/`
8. Move `config.py` to `core/config.py`
9. Move `main.py` to `app/api/main.py`
10. Move `web/app.py` to `app/api/routes.py` (API route definitions)
11. Move `web/streamlit_app.py` and `web/runtime.py` to `app/web/`
12. Move `celery_app.py` to `app/indexer/app.py`, extract task definitions to `app/indexer/tasks.py`
13. Move `worker.py` to `app/indexer/__main__.py`
14. Delete `application/` and old `web/` directories
15. Update all imports across `src/crawllmer/` — use Grep to find every `from crawllmer.application`, `from crawllmer.web`, `from crawllmer.celery_app`, `from crawllmer.worker`, `from crawllmer.config`, `from crawllmer.main` and rewrite
16. Update all imports in `tests/` to match new paths
17. Update Makefile: `run-api` target to `uvicorn crawllmer.app.api.main:app`, `run-worker` to `python -m crawllmer.app.indexer`, `run-ui` to point at `app/web/streamlit_app.py`
18. Update docker-compose.yml and docker-compose.redis.yml service commands
19. Update pyproject.toml entrypoints/scripts if any
20. Run `make check` (format, lint, test) and fix any remaining import or path issues

## Done Criteria

- [ ] `src/crawllmer/application/` directory no longer exists
- [ ] All modules live at their new paths per the PRD migration table
- [ ] `make lint` passes with zero errors
- [ ] `make test` passes — all existing tests run green
- [ ] `make check` passes end-to-end (format + lint + test)
- [ ] `make run-dev` starts both FastAPI and Streamlit without import errors
- [ ] Docker compose builds and starts successfully
- [ ] No residual imports referencing old paths (`crawllmer.application`, `crawllmer.web.app`, `crawllmer.celery_app`, `crawllmer.worker`, `crawllmer.config`, `crawllmer.main`)

## Notes

_Any additional context or decisions made during execution._
