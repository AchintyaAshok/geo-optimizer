---
parent_prd: ../prd-006-railway-production-deployment/prd.md
prd_name: "PRD 006: Railway Production Deployment"
prd_id: 006
task_id: 003
created: 2026-03-19
state: complete
---

# Task 003: Create Dockerfile and docker-compose.postgres.yml

## Metadata

| Field | Value |
|-------|-------|
| PRD | [PRD 006: Railway Production Deployment](../prd.md) |
| Created | 2026-03-19 |
| State | complete |

## Changelog

| Date | Change |
|------|--------|
| 2026-03-19 | Task created |
| 2026-03-19 | Completed — commit `9859ace` |

## Objective

Create a production `Dockerfile` for the app image and a `docker-compose.postgres.yml` overlay for local Postgres development. Add a `make run-postgres` target.

## Inputs

- Existing `docker-compose.yml` (uses `python:3.12-slim` inline, no Dockerfile)
- Existing `docker-compose.redis.yml` overlay pattern
- Settings from Task 001 (`CRAWLLMER_STORAGE_BACKEND`, `CRAWLLMER_PG_*`)

## Outputs

- `Dockerfile` — single image for API, Worker, UI
- `docker-compose.postgres.yml` — compose overlay with Postgres + Redis
- Updated `Makefile` with `run-postgres` target
- Updated `docker-compose.yml` to use the Dockerfile instead of inline image

## Steps

1. Create `Dockerfile`:
   - Base: `python:3.12-slim`
   - Install `uv`, copy `pyproject.toml` + `uv.lock`, run `uv sync --frozen`
   - Copy source code
   - Default CMD: uvicorn (overridden per service)
2. Update `docker-compose.yml` to use `build: .` instead of `image: python:3.12-slim` + inline install commands
3. Create `docker-compose.postgres.yml`:
   - `postgres` service: `postgres:16-alpine` with credentials
   - `redis` service: `redis:7-alpine`
   - Override `api` and `worker` environment with `CRAWLLMER_STORAGE_BACKEND=pgsql` and `CRAWLLMER_PG_*` vars
   - Persistent volume for Postgres data
4. Add `run-postgres` target to Makefile:
   - `docker compose -f docker-compose.yml -f docker-compose.postgres.yml up --build`
5. Test: `make run-postgres`, verify API starts and connects to Postgres
6. Test: `make run-dev` still works with SQLite (no regression)

## Done Criteria

- [ ] `Dockerfile` builds successfully
- [ ] `docker-compose.yml` uses Dockerfile instead of inline setup
- [ ] `docker-compose.postgres.yml` starts Postgres + Redis + API + Worker
- [ ] `make run-postgres` brings up the full stack with Postgres
- [ ] API `/health` returns 200 when running with Postgres
- [ ] `make run-dev` still works with SQLite default
- [ ] `make check` passes

## Notes

The Dockerfile should be optimized for layer caching — copy dependency files first, install, then copy source.

### Completion Notes

- `Dockerfile` created: `python:3.12-slim` base, installs `uv`, caches deps, copies source, default CMD uvicorn
- Instead of a separate `docker-compose.postgres.yml`, compose files were consolidated with **profiles** (commit `9859ace`):
  - Profile `distributed` activates Postgres + Redis: `docker compose --profile distributed up --build`
  - This was an intentional deviation — profiles are cleaner than overlay files
- `docker-compose.yml` updated to `build: .` instead of inline image
- Makefile targets: `make distributed-up` replaces the planned `make run-postgres`
- All services (`api`, `worker`, `ui`) build from the shared Dockerfile
