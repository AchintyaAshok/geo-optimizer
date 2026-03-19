---
parent_prd: ../prd-001-observability-stack/prd.md
prd_name: "PRD 001: Observability Stack"
prd_id: 001
task_id: 002
created: 2026-03-18
state: pending
---

# Task 002: Auto-instrumentation for FastAPI, httpx, Celery, SQLite

## Metadata

| Field | Value |
|-------|-------|
| PRD | [PRD 001: Observability Stack](../prd.md) |
| Created | 2026-03-18 |
| State | pending |

## Changelog

| Date | Change |
|------|--------|
| 2026-03-18 | Task created |

## Objective

Add OTEL auto-instrumentation libraries for FastAPI, httpx, Celery, and SQLite3. Activate all instrumentors inside `setup_telemetry()` so that every HTTP request, outbound crawl call, Celery task, and DB query automatically produces spans — zero manual code in business logic.

## Inputs

- Task 001 complete (`telemetry_setup.py` exists with `setup_telemetry()`)
- `pyproject.toml` for adding dependencies

## Outputs

- Updated `pyproject.toml` with instrumentation packages
- Updated `telemetry_setup.py` — instrumentors activated during setup
- Auto-generated spans for all FastAPI endpoints, httpx requests, Celery tasks, and SQLite queries

## Steps

1. Add dependencies to `pyproject.toml`:
   - `opentelemetry-instrumentation-fastapi`
   - `opentelemetry-instrumentation-httpx`
   - `opentelemetry-instrumentation-celery`
   - `opentelemetry-instrumentation-sqlite3`
2. In `setup_telemetry()`, after configuring providers, call:
   - `FastAPIInstrumentor.instrument()` (or `.instrument_app(app)` if app reference is available)
   - `HTTPXClientInstrumentor().instrument()`
   - `CeleryInstrumentor().instrument()`
   - `SQLite3Instrumentor().instrument()`
3. Exclude noisy endpoints from tracing (e.g., `/health`) via FastAPI instrumentor's `excluded_urls` parameter
4. Verify trace propagation works across process boundaries: API → Celery task should share a single trace via propagated context
5. Run `make check`

## Done Criteria

- [ ] FastAPI requests produce spans with HTTP method, route, status code attributes
- [ ] httpx outbound calls produce client spans with URL and status
- [ ] Celery task execution produces spans linked to the parent API span (distributed trace)
- [ ] SQLite queries produce DB spans
- [ ] `/health` endpoint is excluded from tracing
- [ ] `make check` passes

## Notes

- Celery trace propagation requires the `CeleryInstrumentor` to inject/extract context into task headers. Verify this works with the SQLite broker (the default) — some instrumentors assume Redis/RabbitMQ.
- `FastAPIInstrumentor` can be called with `.instrument()` (global) or `.instrument_app(app)` (per-app). Global is simpler since we only have one app.
