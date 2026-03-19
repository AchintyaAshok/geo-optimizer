---
parent_prd: ../prd-006-core-module-error-handling-and-observability-events/prd.md
prd_name: "PRD 006: Core Module — Error Handling and Observability Events"
prd_id: 006
task_id: 004
created: 2026-03-19
state: pending
---

# Task 004: Create core/observability/events.py - event classes and BusinessMetrics

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

Create `core/observability/events.py` with the abstract `EventMetadata` base class, four concrete event dataclasses (`DiscoveryCompletedEvent`, `ExtractionCompletedEvent`, `GenerationCompletedEvent`, `RunCompletedEvent`), and the `BusinessMetrics` class that records run-level OTEL metrics (`crawllmer_pages_indexed_total`, `crawllmer_run_duration_seconds`, `crawllmer_llmstxt_size_bytes`).

## Inputs

- Event class spec from PRD section 4 (code listings for `EventMetadata`, concrete events, `BusinessMetrics`)
- `src/crawllmer/core/observability/__init__.py` (from Task 2, needs re-export updates)

## Outputs

- Created: `src/crawllmer/core/observability/events.py` — `EventMetadata` ABC, 4 concrete event classes, `BusinessMetrics`
- Modified: `src/crawllmer/core/observability/__init__.py` — re-exports all new names
- Created: `tests/unit/test_events.py`

## Steps

1. Write tests for `EventMetadata` subclasses: each concrete event stores fields, `to_attributes()` returns correct dict with correct types
2. Write test for `BusinessMetrics`: mock OTEL meter, call `record_run_completed(event)`, verify counter/histogram `.add()`/`.record()` called with correct values
3. Run tests — confirm they fail
4. Implement `EventMetadata` ABC as `@dataclass(slots=True)` with `run_id`, `event_name`, `timestamp` fields
5. Implement `DiscoveryCompletedEvent`, `ExtractionCompletedEvent`, `GenerationCompletedEvent`, `RunCompletedEvent` as `@dataclass(slots=True)` subclasses
6. Implement `BusinessMetrics` class with `crawllmer.business` meter and `record_run_completed()` method
7. Update `core/observability/__init__.py` to re-export all new names
8. Run tests — confirm they pass
9. Run `make check`

## Done Criteria

- [ ] `EventMetadata` ABC exists with `run_id`, `event_name`, `timestamp` fields and abstract `to_attributes()` method
- [ ] All 4 concrete event classes are `@dataclass(slots=True)` subclasses with correct fields and `to_attributes()` implementations
- [ ] `BusinessMetrics` registers 3 OTEL instruments on `crawllmer.business` meter: counter `crawllmer_pages_indexed_total`, histogram `crawllmer_run_duration_seconds`, histogram `crawllmer_llmstxt_size_bytes`
- [ ] `BusinessMetrics.record_run_completed()` calls `.add()` and `.record()` with correct values from `RunCompletedEvent`
- [ ] `core/observability/__init__.py` re-exports `EventMetadata`, all 4 event classes, and `BusinessMetrics`
- [ ] Tests in `tests/unit/test_events.py` pass
- [ ] `make check` passes

## Notes

_Any additional context or decisions made during execution._
