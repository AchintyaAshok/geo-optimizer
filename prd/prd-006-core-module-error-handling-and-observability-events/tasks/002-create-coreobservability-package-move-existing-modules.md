---
parent_prd: ../prd-006-core-module-error-handling-and-observability-events/prd.md
prd_name: "PRD 006: Core Module — Error Handling and Observability Events"
prd_id: 006
task_id: 002
created: 2026-03-19
state: pending
---

# Task 002: Create core/observability/ package (move existing modules)

## Metadata

| Field | Value |
|-------|-------|
| PRD | [PRD 006: Core Module — Error Handling and Observability Events](../prd.md) |
| Created | 2026-03-19 |
| State | pending |

## Changelog

| Date | Change |
|------|--------|
| 2026-03-19 | Task created |

## Objective

Create the `core/observability/` package by moving `application/observability.py` and `application/telemetry_setup.py` into it. Update all imports across the codebase so existing functionality is preserved under the new paths.

## Inputs

- `src/crawllmer/application/observability.py` (existing, to be moved)
- `src/crawllmer/application/telemetry_setup.py` (existing, to be moved)
- `src/crawllmer/core/` package created in Task 1

## Outputs

- `src/crawllmer/core/observability/__init__.py` — re-exports `log_event`, `PipelineTelemetry`, `setup_telemetry`
- `src/crawllmer/core/observability/pipeline_telemetry.py` — moved from `application/observability.py`
- `src/crawllmer/core/observability/telemetry_setup.py` — moved from `application/telemetry_setup.py`
- Deleted: `src/crawllmer/application/observability.py`
- Deleted: `src/crawllmer/application/telemetry_setup.py`
- Modified: `src/crawllmer/application/orchestrator.py` (updated imports)
- Modified: `src/crawllmer/web/app.py` (updated imports)
- Modified: `src/crawllmer/celery_app.py` (updated imports)
- Modified: `tests/integration/test_pipeline_flow.py` (updated imports)

## Steps

1. Create `core/observability/pipeline_telemetry.py` — copy contents of `application/observability.py` verbatim
2. Create `core/observability/telemetry_setup.py` — copy contents of `application/telemetry_setup.py` verbatim
3. Create `core/observability/__init__.py` — re-export `log_event`, `PipelineTelemetry`, `setup_telemetry`
4. Update imports in `orchestrator.py`: `from crawllmer.core.observability import PipelineTelemetry, log_event`
5. Update imports in `web/app.py`: `from crawllmer.core.observability import log_event, setup_telemetry`
6. Update imports in `celery_app.py`: `from crawllmer.core.observability import setup_telemetry`
7. Update imports in `tests/integration/test_pipeline_flow.py`: `from crawllmer.core.observability import PipelineTelemetry`
8. Delete `application/observability.py` and `application/telemetry_setup.py`
9. Run `make check` — all tests pass with new import paths

## Done Criteria

- [ ] `core/observability/pipeline_telemetry.py` exists with contents from former `application/observability.py`
- [ ] `core/observability/telemetry_setup.py` exists with contents from former `application/telemetry_setup.py`
- [ ] `core/observability/__init__.py` re-exports `log_event`, `PipelineTelemetry`, `setup_telemetry`
- [ ] `application/observability.py` and `application/telemetry_setup.py` are deleted
- [ ] All imports in `orchestrator.py`, `web/app.py`, `celery_app.py`, and `test_pipeline_flow.py` point to `crawllmer.core.observability`
- [ ] `make check` passes with no import errors

## Notes

_Any additional context or decisions made during execution._
