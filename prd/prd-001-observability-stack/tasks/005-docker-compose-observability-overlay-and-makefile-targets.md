---
parent_prd: ../prd-001-observability-stack/prd.md
prd_name: "PRD 001: Observability Stack"
prd_id: 001
task_id: 005
created: 2026-03-18
state: pending
---

# Task 005: Docker Compose observability overlay and Makefile targets

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

Create `docker-compose.observability.yml` as a Compose overlay that adds the full observability stack (OTEL Collector, Jaeger, Prometheus, Grafana) and overrides the `api` and `worker` services to send OTLP telemetry to the collector. Add a `make run-observability` target for one-command startup.

## Inputs

- Task 004 complete (infra config files exist)
- Existing `docker-compose.yml` (api + worker services)
- Existing `docker-compose.redis.yml` (overlay pattern established)

## Outputs

- `docker-compose.observability.yml`
- Updated `Makefile` with `run-observability` target
- Updated `.env.example` documentation

## Steps

1. Create `docker-compose.observability.yml` with these services:
   - **otel-collector**:
     - Image: `otel/opentelemetry-collector-contrib:latest`
     - Volumes: `./infra/otel-collector-config.yaml:/etc/otelcol-contrib/config.yaml`
     - Ports: `4317:4317` (gRPC), `4318:4318` (HTTP), `8889:8889` (Prometheus exporter)
     - Healthcheck on port 13133 (collector health endpoint)
   - **jaeger**:
     - Image: `jaegertracing/jaeger:2`
     - Ports: `16686:16686` (UI)
     - Environment: `COLLECTOR_OTLP_GRPC_HOST_PORT=0.0.0.0:4317`
     - Depends on: otel-collector
   - **prometheus**:
     - Image: `prom/prometheus:latest`
     - Volumes: `./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml`
     - Ports: `9090:9090`
     - Depends on: otel-collector
   - **grafana**:
     - Image: `grafana/grafana:latest`
     - Volumes: `./infra/grafana/provisioning:/etc/grafana/provisioning`
     - Ports: `3000:3000`
     - Environment: `GF_SECURITY_ADMIN_PASSWORD=admin`, `GF_AUTH_ANONYMOUS_ENABLED=true`, `GF_AUTH_ANONYMOUS_ORG_ROLE=Admin`
     - Depends on: prometheus, jaeger
2. Add service overrides for `api` and `worker`:
   - Set `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317`
   - Add `depends_on: otel-collector` (service_healthy)
3. Add to `Makefile`:
   ```makefile
   run-observability:
       docker compose -f docker-compose.yml -f docker-compose.observability.yml up --build
   ```
4. Update `.env.example` with `OTEL_EXPORTER_OTLP_ENDPOINT` documentation
5. Test that `docker compose -f docker-compose.yml -f docker-compose.observability.yml config` produces valid merged config
6. Run `make check` (no app code changes)

## Done Criteria

- [ ] `docker compose -f docker-compose.yml -f docker-compose.observability.yml config` validates successfully
- [ ] `make run-observability` target exists and uses the correct compose file combination
- [ ] OTEL Collector, Jaeger (UI on :16686), Prometheus (:9090), and Grafana (:3000) are defined
- [ ] `api` and `worker` services get `OTEL_EXPORTER_OTLP_ENDPOINT` override
- [ ] Grafana starts with Jaeger + Prometheus datasources auto-provisioned (no manual setup)
- [ ] `.env.example` documents `OTEL_EXPORTER_OTLP_ENDPOINT`
- [ ] `make check` passes

## Notes

- Follow the existing overlay pattern from `docker-compose.redis.yml` — the base `docker-compose.yml` stays unchanged.
- Grafana anonymous admin access is intentional for local dev — no login friction.
- The compose overlay is composable: `docker-compose.yml` + `docker-compose.redis.yml` + `docker-compose.observability.yml` all stack together.
