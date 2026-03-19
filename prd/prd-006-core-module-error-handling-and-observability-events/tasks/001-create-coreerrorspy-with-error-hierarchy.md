---
parent_prd: ../prd-006-core-module-error-handling-and-observability-events/prd.md
prd_name: "PRD 006: Core Module — Error Handling and Observability Events"
prd_id: 006
task_id: 001
created: 2026-03-19
state: pending
---

# Task 001: Create core/errors.py with error hierarchy

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

Create the `core/` package with a typed error hierarchy in `core/errors.py`. All 7 error classes (`CrawllmerError`, `MissingConfigError`, `InvalidInputError`, `RunNotFoundError`, `PipelineProcessingError`, `CrawlFetchError`, `ContentExtractionError`, `GenerationError`) are implemented per the spec in PRD section 3, with structured attributes and human-readable messages.

## Inputs

- Error hierarchy spec from PRD section 3 (`core/errors.py` code listing)
- No existing `src/crawllmer/core/` directory yet

## Outputs

- `src/crawllmer/core/__init__.py` — re-exports all error classes
- `src/crawllmer/core/errors.py` — all 7 error classes per spec
- `tests/unit/test_errors.py` — tests for each error class

## Steps

1. Write tests for each error class in `tests/unit/test_errors.py`: verify `__init__` stores attributes, `str()` produces expected message, `PipelineProcessingError.__cause__` is set, all inherit from `CrawllmerError`
2. Run tests — confirm they fail (classes don't exist yet)
3. Implement `core/errors.py` with all 7 error classes per the spec (PRD section 3)
4. Implement `core/__init__.py` re-exporting all error classes
5. Run tests — confirm they pass
6. Run `make check`

## Done Criteria

- [ ] All 7 error classes exist in `src/crawllmer/core/errors.py` matching the PRD spec
- [ ] `src/crawllmer/core/__init__.py` re-exports all error classes (e.g. `from crawllmer.core import RunNotFoundError` works)
- [ ] Each error class stores structured attributes and produces a human-readable `str()` message
- [ ] `PipelineProcessingError.__cause__` is set correctly
- [ ] All error classes inherit from `CrawllmerError`
- [ ] Tests in `tests/unit/test_errors.py` pass
- [ ] `make check` passes

## Notes

_Any additional context or decisions made during execution._
