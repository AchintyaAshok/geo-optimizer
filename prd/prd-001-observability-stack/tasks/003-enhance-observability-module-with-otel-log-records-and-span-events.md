---
parent_prd: ../prd-001-observability-stack/prd.md
prd_name: "PRD 001: Observability Stack"
prd_id: 001
task_id: 003
created: 2026-03-18
state: pending
---

# Task 003: Enhance observability module with OTEL log records and span events

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

Enhance the existing `observability.py` so that `log_event()` produces OTEL LogRecords (with trace/span context automatically attached), and add domain-specific span events to the pipeline stages for richer trace detail. No breaking changes to the `PipelineTelemetry` public API.

## Inputs

- Tasks 001-002 complete (OTEL providers configured, LoggerProvider with handler active)
- Existing `observability.py` with `log_event()` and `PipelineTelemetry`
- `orchestrator.py` and `workers.py` (callers of `log_event()` and telemetry)

## Outputs

- Updated `log_event()` that emits structured OTEL log records with trace context
- Span events added to pipeline stage spans (page discovered, metadata extracted, llms.txt generated, etc.)
- Structured logs include `trace_id` and `span_id` when emitted within a traced context

## Steps

1. Update `log_event()`:
   - The stdlib `logging.Handler` bridge from Task 001 already routes log records through the OTEL LoggerProvider — verify that `log_event()` calls (which use `LOGGER.info(json.dumps(...))`) are captured
   - Ensure the JSON payload is set as the log body, not double-serialized
   - Verify `trace_id` and `span_id` are automatically attached by the OTEL LoggingHandler when called inside a span context
2. Add span events to `PipelineTelemetry`:
   - In `stage_span()` context manager, expose a way to add events (or just use the yielded span directly — callers already have access)
   - Add convenience methods or document the pattern: `span.add_event("page.discovered", {"url": url, "strategy": strategy})`
3. Add span events in `workers.py` at key points:
   - `page.discovered` — when a URL is found during discovery (with URL and discovery strategy)
   - `metadata.extracted` — when metadata is successfully extracted from a page (with URL and confidence score)
   - `llms_txt.generated` — when the final llms.txt document is produced (with entry count and byte size)
4. Add span events in `orchestrator.py`:
   - `pipeline.stage.transition` — when a work item transitions state
5. Write tests verifying log_event produces records with trace context
6. Run `make check`

## Done Criteria

- [ ] `log_event()` output includes `trace_id` and `span_id` when called inside a span
- [ ] Span events appear on pipeline stage spans in traces (visible in Jaeger once stack is running)
- [ ] `PipelineTelemetry` public API is unchanged — existing callers work without modification
- [ ] `make check` passes

## Notes

- The key insight: the OTEL `LoggingHandler` from Task 001 does the heavy lifting. `log_event()` just needs to keep calling `LOGGER.info()` and the handler will attach trace context and route through the OTEL pipeline.
- Span events are lightweight — they attach to the current span and appear inline in the trace waterfall. Good for "something happened" without creating a new child span.
