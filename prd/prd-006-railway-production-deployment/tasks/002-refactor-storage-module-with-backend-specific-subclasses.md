---
parent_prd: ../prd-006-railway-production-deployment/prd.md
prd_name: "PRD 006: Railway Production Deployment"
prd_id: 006
task_id: 002
created: 2026-03-19
state: complete
---

# Task 002: Refactor storage module with backend-specific subclasses

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
| 2026-03-19 | Completed — commit `a362384` |

## Objective

Refactor `adapters/storage.py` to separate SQLAlchemy query logic from backend-specific engine configuration. The class hierarchy:

```
domain/ports.py
  CrawlRepository (ABC)                 ← already exists, unchanged

adapters/storage.py
  SqlAlchemyStorageRepository            ← shared SQLAlchemy query logic
      ├── SqliteStorageRepository         ← SQLite engine config
      └── PgSqlStorageRepository          ← Postgres engine config

  get_storage(settings) → CrawlRepository
```

## Inputs

- Existing `src/crawllmer/adapters/storage.py` with `SqliteCrawlRepository`
- Existing `domain/ports.py` with abstract `CrawlRepository` (unchanged)
- `Settings` with `storage_backend` and `engine_kwargs` from Task 001

## Outputs

- Refactored `storage.py` with class hierarchy
- Updated `app/web/runtime.py` and `app/indexer/app.py` to use `get_storage()`
- All existing tests pass without modification

## Steps

1. In `storage.py`, rename `SqliteCrawlRepository` → `SqlAlchemyStorageRepository`:
   - Constructor takes a pre-built `engine` instead of a `db_url`
   - All query methods stay in this class unchanged
   - Runs `SQLModel.metadata.create_all(engine)` in constructor
2. Create `SqliteStorageRepository(SqlAlchemyStorageRepository)`:
   - `__init__` creates engine with `connect_args={"check_same_thread": False}`
   - Wraps `create_all()` in `try/except OperationalError` for race-condition handling
   - Passes engine to super
3. Create `PgSqlStorageRepository(SqlAlchemyStorageRepository)`:
   - `__init__` creates engine with `pool_pre_ping=True, pool_size=5`
   - Standard `create_all()` without the SQLite race-condition catch
   - Passes engine to super
4. Create `get_storage(settings=None) -> CrawlRepository`:
   - If `settings.storage_backend == "pgsql"` → `PgSqlStorageRepository(settings.db_url)`
   - Else → `SqliteStorageRepository(settings.db_url)`
5. Update `app/web/runtime.py`: replace `default_repository(db_url=...)` with `get_storage()`
6. Update `app/indexer/app.py`: replace `default_repository(db_url=...)` with `get_storage()`
7. Remove `default_repository()` function
8. Run `make check`

## Done Criteria

- [ ] `SqlAlchemyStorageRepository` contains all query logic, no backend-specific config
- [ ] `SqliteStorageRepository` and `PgSqlStorageRepository` subclass it with correct engine kwargs
- [ ] `get_storage()` returns the right subclass based on `settings.storage_backend`
- [ ] `app/web/runtime.py` uses `get_storage()` instead of `default_repository()`
- [ ] `app/indexer/app.py` uses `get_storage()` instead of `default_repository()`
- [ ] All existing tests pass (unit + integration)
- [ ] `make check` passes

## Notes

The abstract `CrawlRepository` in `domain/ports.py` stays untouched — it's the interface contract. `SqlAlchemyStorageRepository` is the concrete implementation layer that both backend-specific subclasses share.

### Completion Notes

- `SqlAlchemyStorageRepository` base class at line 103 of `storage.py` — all query logic
- `SqliteStorageRepository` subclass at line 400 — SQLite-specific engine config
- `PgSqlStorageRepository` subclass at line 412 — Postgres-specific engine config
- `get_storage(settings)` factory at line 420 — returns correct subclass
- `app/web/runtime.py` and `app/indexer/app.py` updated to use `get_storage()`
- `default_repository()` removed
- All unit + integration tests pass
