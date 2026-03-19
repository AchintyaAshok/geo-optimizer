---
parent_prd: ../prd-006-core-module-error-handling-and-observability-events/prd.md
prd_name: "PRD 006: Core Module — Error Handling and Observability Events"
prd_id: 006
task_id: 005
created: 2026-03-19
state: pending
---

# Task 005: Wire errors into orchestrator and web layer

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

Replace all generic `Exception`/`ValueError` catches in the orchestrator, web layer, Streamlit app, and Celery task boundary with the typed error classes from `core/errors.py`. Update tests to assert on the new exception types and verify the `PipelineProcessingError` causal chain.

## Inputs

- `src/crawllmer/core/errors.py` (from Task 1)
- `src/crawllmer/application/orchestrator.py` (existing, uses `ValueError` and bare `Exception`)
- `src/crawllmer/web/app.py` (existing, generic catches)
- `src/crawllmer/web/streamlit_app.py` (existing, catches `ValueError`)
- `src/crawllmer/celery_app.py` (existing, no try/except around pipeline call)
- `tests/unit/test_orchestrator.py` (existing, asserts `ValueError`)
- `tests/integration/test_pipeline_flow.py` (existing, asserts `RuntimeError`)

## Outputs

- Modified: `src/crawllmer/application/orchestrator.py` — raises `InvalidInputError`, `RunNotFoundError`, `PipelineProcessingError`
- Modified: `src/crawllmer/web/app.py` — catches typed errors, maps to HTTP status codes (422, 404, 500)
- Modified: `src/crawllmer/web/streamlit_app.py` — catches `InvalidInputError` instead of `ValueError`
- Modified: `src/crawllmer/celery_app.py` — try/except `PipelineProcessingError` with structured logging
- Modified: `tests/unit/test_orchestrator.py` — asserts `RunNotFoundError`
- Modified: `tests/integration/test_pipeline_flow.py` — asserts `PipelineProcessingError` with `exc.stage` and `exc.__cause__`

## Steps

1. Update `test_orchestrator.py`: `test_pipeline_rejects_unknown_run` catches `RunNotFoundError` instead of `ValueError`, import from `crawllmer.core`
2. Update `test_pipeline_flow.py`: `test_pipeline_failure_path_marks_failed_stage_and_run` catches `PipelineProcessingError`, asserts `exc.stage == "discovery"` and `isinstance(exc.__cause__, RuntimeError)`
3. Run tests — confirm they fail (orchestrator still raises old exceptions)
4. Update `orchestrator.py`:
   - Import `InvalidInputError`, `RunNotFoundError`, `PipelineProcessingError` from `crawllmer.core`
   - `enqueue_run()`: replace `raise ValueError("invalid URL")` with `raise InvalidInputError("url", "invalid URL")`
   - `process_run()`: replace `raise ValueError("run not found")` with `raise RunNotFoundError(run_id)`
   - `_run_stage()`: in the except block, after telemetry/logging, `raise PipelineProcessingError(stage=stage.value, run_id=run.id, cause=exc) from exc`
   - `process_run()`: change `except Exception` to `except PipelineProcessingError`
5. Run tests — confirm they pass
6. Update `web/app.py`:
   - Import `InvalidInputError`, `RunNotFoundError`, `PipelineProcessingError` from `crawllmer.core`
   - `crawl_api()`: catch `InvalidInputError` -> 422
   - `process_run()`: remove manual `repo.get_run()` pre-check (redundant), catch `RunNotFoundError` -> 404, catch `PipelineProcessingError` -> 500, remove duplicate failure-marking logic
7. Update `web/streamlit_app.py` line ~581: `except InvalidInputError as exc:` instead of `except ValueError as exc:`
8. Update `celery_app.py`: add `try/except PipelineProcessingError` around `pipeline.process_run()` that logs structured error and re-raises
9. Run `make check`

## Done Criteria

- [ ] No generic `ValueError` or bare `Exception` catches remain in orchestrator, web layer, or celery_app (excluding `retry.py`)
- [ ] `orchestrator.py` raises `InvalidInputError`, `RunNotFoundError`, `PipelineProcessingError` in the correct places
- [ ] `web/app.py` maps `InvalidInputError` -> 422, `RunNotFoundError` -> 404, `PipelineProcessingError` -> 500
- [ ] `web/app.py` no longer duplicates run-failure state mutation (orchestrator handles it)
- [ ] `streamlit_app.py` catches `InvalidInputError` instead of `ValueError`
- [ ] `celery_app.py` has try/except `PipelineProcessingError` with structured logging around `pipeline.process_run()`
- [ ] `test_orchestrator.py` asserts `RunNotFoundError` for unknown run
- [ ] `test_pipeline_flow.py` asserts `PipelineProcessingError` with correct `stage` and `__cause__`
- [ ] `make check` passes

## Notes

_Any additional context or decisions made during execution._
