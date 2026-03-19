---
parent_prd: ../prd-001-observability-stack/prd.md
prd_name: "PRD 001: Observability Stack"
prd_id: 001
task_id: 006
created: 2026-03-18
state: pending
---

# Task 006: Integration verification and documentation

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

End-to-end verification that all observability components work together. Run the full stack, execute a crawl, and verify traces appear in Jaeger, metrics in Prometheus, and datasources load in Grafana. Fix any integration issues discovered. Update CLAUDE.md with new make targets and observability architecture notes.

## Inputs

- Tasks 001-005 complete
- Full Docker Compose stack runnable via `make run-observability`

## Outputs

- Verified end-to-end observability pipeline
- Any integration bugfixes
- Updated CLAUDE.md with observability section

## Steps

1. Run `make check` — ensure all tests pass
2. Run `make run-observability` — verify all containers start healthy
3. Execute a crawl via the API:
   ```bash
   curl -X POST http://localhost:8000/api/v1/crawls \
     -H 'content-type: application/json' \
     -d '{"url":"https://example.com"}'
   ```
4. Verify in Jaeger (http://localhost:16686):
   - Service `crawllmer-api` appears
   - Service `crawllmer-worker` appears
   - A trace spans from API request → Celery task → pipeline stages
   - Span events (page.discovered, metadata.extracted, etc.) are visible
5. Verify in Prometheus (http://localhost:9090):
   - `crawllmer_pipeline_runs_total` metric exists
   - `crawllmer_pipeline_stage_duration_seconds` histogram has data
   - `crawllmer_pipeline_stage_events_total` counter increments
6. Verify in Grafana (http://localhost:3000):
   - Jaeger datasource is provisioned and connectable
   - Prometheus datasource is provisioned and connectable
   - Can query traces and metrics through Grafana Explore
7. Verify console fallback:
   - Stop the observability stack
   - Run `make run-api` (no collector running, no OTEL_EXPORTER_OTLP_ENDPOINT set)
   - Confirm structured trace/metric/log output appears in terminal stdout
8. Fix any issues discovered during verification
9. Update CLAUDE.md:
   - Add `make run-observability` to Commands section
   - Add brief observability architecture note (OTEL Collector → Jaeger/Prometheus/Grafana)
   - Document the dual-mode exporter behavior
10. Final `make check`

## Done Criteria

- [ ] All containers start and pass health checks via `make run-observability`
- [ ] End-to-end traces visible in Jaeger spanning API → Worker → Pipeline stages
- [ ] Prometheus shows `crawllmer_pipeline_*` metrics with data
- [ ] Grafana datasources (Jaeger + Prometheus) are auto-provisioned and functional
- [ ] Console fallback works — `make run-api` without collector prints telemetry to stdout
- [ ] CLAUDE.md updated with new commands and architecture notes
- [ ] `make check` passes

## Notes

- This task is primarily verification, not new code. Most time will be spent running the stack and debugging integration issues.
- If Celery trace propagation doesn't work with the SQLite broker, document the limitation and note that Redis broker is recommended for full distributed tracing.
- The console fallback test is important — this is the default developer experience when running locally without Docker.
