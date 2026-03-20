---
parent_prd: ../prd-006-railway-production-deployment/prd.md
prd_name: "PRD 006: Railway Production Deployment"
prd_id: 006
task_id: 001
created: 2026-03-19
state: complete
---

# Task 001: Add psycopg2-binary dep and storage backend settings

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
| 2026-03-19 | Completed — commit `9fa57e9` |

## Objective

Add `psycopg2-binary` dependency and extend `Settings` in `config.py` with explicit storage backend selection, Postgres credential fields, and Pydantic validation.

## Inputs

- Existing `src/crawllmer/core/config.py` with `Settings(BaseSettings)`
- Existing `pyproject.toml`
- `.env.example` for documentation

## Outputs

- Updated `config.py` with `storage_backend`, `pg_*` fields, `model_validator`, and `engine_kwargs`
- Updated `pyproject.toml` with `psycopg2-binary`
- Updated `.env.example` with new variables documented

## Steps

1. Add `psycopg2-binary` to `pyproject.toml` dependencies
2. Add to `Settings` class in `config.py`:
   - `storage_backend: Literal["sqlite", "pgsql"] = "sqlite"`
   - `pg_host: str | None = None`
   - `pg_port: int = 5432`
   - `pg_user: str | None = None`
   - `pg_password: str | None = None`
   - `pg_database: str | None = None`
3. Add `model_validator(mode="after")` that:
   - When `storage_backend == "pgsql"`, validates all `pg_*` credentials are present
   - Assembles `db_url` from parts: `postgresql://{user}:{password}@{host}:{port}/{database}`
   - Raises `ValueError` with clear message listing missing fields
4. Add `engine_kwargs` property returning backend-appropriate kwargs
5. Update `.env.example` with the new `CRAWLLMER_STORAGE_BACKEND` and `CRAWLLMER_PG_*` variables
6. Add unit test for settings validation (pgsql without credentials fails, with credentials succeeds, sqlite works as default)
7. Run `make check`

## Done Criteria

- [ ] `psycopg2-binary` in pyproject.toml
- [ ] `Settings.storage_backend` is `Literal["sqlite", "pgsql"]` with default `"sqlite"`
- [ ] Setting `storage_backend=pgsql` without `pg_host`/`pg_user`/`pg_password`/`pg_database` raises `ValueError`
- [ ] Setting `storage_backend=pgsql` with all pg fields assembles correct `db_url`
- [ ] `engine_kwargs` returns `check_same_thread` for sqlite, `pool_pre_ping`/`pool_size` for pgsql
- [ ] `.env.example` documents the new variables
- [ ] `make check` passes

## Notes

- `psycopg2-binary>=2.9.10` added to `pyproject.toml`
- `Settings` extended with `storage_backend`, `pg_host`, `pg_port`, `pg_user`, `pg_password`, `pg_database`
- `model_validator(mode="after")` validates all `pg_*` fields when `storage_backend == "pgsql"`, assembles `db_url`
- `engine_kwargs` property returns `check_same_thread` for sqlite, `pool_pre_ping`/`pool_size` for pgsql
- `celery_worker_pool` property derives pool type from broker URL (prefork for Redis, solo for SQLite)
- `.env.example` updated with all new variables
