---
parent_prd: ../prd-006-core-module-error-handling-and-observability-events/prd.md
prd_name: "PRD 006: Core Module — Error Handling and Observability Events"
prd_id: 006
task_id: 006
created: 2026-03-19
state: pending
---

# Task 006: Wire events and BusinessMetrics into orchestrator

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

Wire the structured event classes and `BusinessMetrics` into the orchestrator so that pipeline execution emits `DiscoveryCompletedEvent`, `ExtractionCompletedEvent`, `GenerationCompletedEvent`, and `RunCompletedEvent` at the appropriate points, and business-level OTEL metrics are recorded on run completion.

## Inputs

- `src/crawllmer/core/observability/events.py` (from Task 4 — event classes and `BusinessMetrics`)
- `src/crawllmer/application/orchestrator.py` (modified in Task 5 — typed errors wired in)
- `tests/integration/test_pipeline_flow.py` (existing integration tests)

## Outputs

- Modified: `src/crawllmer/application/orchestrator.py` — emits events and records business metrics
- Modified: `tests/integration/test_pipeline_flow.py` — verifies business metrics are emitted

## Steps

1. Add test to `test_pipeline_flow.py`: after happy-path run, assert `crawllmer_pages_indexed_total`, `crawllmer_run_duration_seconds`, `crawllmer_llmstxt_size_bytes` appear in metric reader output
2. Run test — confirm it fails (metrics not emitted yet)
3. Update `CrawlPipeline.__init__` to accept optional `business_metrics: BusinessMetrics | None = None` parameter, default to `BusinessMetrics()`
4. In `_build_stage_plan`:
   - After `run_discovery`: emit `DiscoveryCompletedEvent` via `log_event` with `event.to_attributes()`
   - After `run_extraction`: emit `ExtractionCompletedEvent`
   - After `run_generation`: emit `GenerationCompletedEvent`
5. In `process_run`, after successful completion: create `RunCompletedEvent` with `total_pages_indexed`, `duration_seconds`, `llmstxt_size_bytes`, call `self.business_metrics.record_run_completed(event)`, and `log_event` with `event.to_attributes()`
6. Run tests — confirm they pass
7. Run `make check`

## Done Criteria

- [ ] `CrawlPipeline.__init__` accepts optional `business_metrics` parameter, defaults to `BusinessMetrics()`
- [ ] `DiscoveryCompletedEvent` emitted after discovery stage via `log_event`
- [ ] `ExtractionCompletedEvent` emitted after extraction stage via `log_event`
- [ ] `GenerationCompletedEvent` emitted after generation stage via `log_event`
- [ ] `RunCompletedEvent` emitted after successful run completion with `total_pages_indexed`, `duration_seconds`, `llmstxt_size_bytes`
- [ ] `BusinessMetrics.record_run_completed()` called with the `RunCompletedEvent`
- [ ] Integration test verifies `crawllmer_pages_indexed_total`, `crawllmer_run_duration_seconds`, `crawllmer_llmstxt_size_bytes` appear in metric output
- [ ] `make check` passes

## Notes

_Any additional context or decisions made during execution._
