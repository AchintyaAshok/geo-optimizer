---
parent_prd: ../prd-006-railway-production-deployment/prd.md
prd_name: "PRD 006: Railway Production Deployment"
prd_id: 006
task_id: 005
created: 2026-03-19
state: pending
---

# Task 005: Wire OTEL collector and Jaeger on Railway

## Metadata

| Field | Value |
|-------|-------|
| PRD | [PRD 006: Railway Production Deployment](../prd.md) |
| Created | 2026-03-19 |
| State | pending |

## Changelog

| Date | Change |
|------|--------|
| 2026-03-19 | Task created |

## Objective

Deploy OTEL Collector and Jaeger as Railway services. Configure the collector to forward traces to Jaeger. Set `OTEL_EXPORTER_OTLP_ENDPOINT` on API and Worker services so traces flow end-to-end.

## Inputs

- Existing `infra/otel-collector-config.yaml` (gRPC receiver on :4317, exports to Jaeger + Prometheus)
- Existing `docker-compose.observability.yml` for reference
- Running Railway project from Task 004

## Outputs

- OTEL Collector service on Railway (private, :4317)
- Jaeger service on Railway (public dashboard on :16686)
- API and Worker services emitting traces to collector
- Traces visible in Jaeger UI

## Steps

1. Deploy Jaeger service on Railway:
   - Docker image: `jaegertracing/jaeger:2`
   - Expose port 16686 (public domain for UI)
   - Expose port 4317 on private network (for OTLP gRPC from collector)
2. Deploy OTEL Collector service on Railway:
   - Docker image: `otel/opentelemetry-collector-contrib:0.120.0`
   - Mount or embed `infra/otel-collector-config.yaml`
   - Update Jaeger endpoint in config to use Railway private DNS:
     `endpoint: ${{Jaeger.RAILWAY_PRIVATE_DOMAIN}}:4317`
   - Expose port 4317 on private network (for app services to send telemetry)
3. Set `OTEL_EXPORTER_OTLP_ENDPOINT` on API service:
   - `http://${{OTEL Collector.RAILWAY_PRIVATE_DOMAIN}}:4317`
   - `OTEL_SERVICE_NAME=crawllmer-api`
4. Set `OTEL_EXPORTER_OTLP_ENDPOINT` on Worker service:
   - Same endpoint
   - `OTEL_SERVICE_NAME=crawllmer-worker`
5. Trigger a crawl via the API or UI
6. Open Jaeger UI and verify traces appear with pipeline spans

## Done Criteria

- [ ] OTEL Collector service running on Railway
- [ ] Jaeger service running with public dashboard URL
- [ ] API and Worker have `OTEL_EXPORTER_OTLP_ENDPOINT` configured
- [ ] Triggering a crawl produces traces visible in Jaeger
- [ ] Traces show `crawl_pipeline.run` and `crawl_pipeline.stage.*` spans

## Notes

The collector config may need adjustment for Railway's environment — Docker Compose uses service names (`jaeger:4317`) while Railway uses private DNS (`*.railway.internal:4317`). Consider using environment variable substitution in the collector config or creating a Railway-specific variant.

Prometheus is deferred — Jaeger alone satisfies the observability deliverable.
