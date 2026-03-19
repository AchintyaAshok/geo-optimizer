---
parent_prd: ../prd-001-observability-stack/prd.md
prd_name: "PRD 001: Observability Stack"
prd_id: 001
task_id: 004
created: 2026-03-18
state: pending
---

# Task 004: OTEL Collector config and infra provisioning files

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

Create the OTEL Collector configuration and supporting provisioning files for Prometheus and Grafana. These are static config files — no application code changes. The collector receives OTLP from app processes and fans out to Jaeger (traces), Prometheus (metrics), and debug/console (logs).

## Inputs

- Understanding of the metrics emitted by `PipelineTelemetry` (counter, histogram, up-down-counter names)
- Knowledge of Jaeger OTLP receiver (port 4317)
- Prometheus scrape model (pull-based from collector's Prometheus exporter endpoint)

## Outputs

- `infra/otel-collector-config.yaml`
- `infra/prometheus/prometheus.yml`
- `infra/grafana/provisioning/datasources/datasources.yaml`

## Steps

1. Create `infra/` directory structure:
   ```
   infra/
   ├── otel-collector-config.yaml
   ├── prometheus/
   │   └── prometheus.yml
   └── grafana/
       └── provisioning/
           └── datasources/
               └── datasources.yaml
   ```
2. Write `otel-collector-config.yaml`:
   - **Receivers**: `otlp` with gRPC (0.0.0.0:4317) and HTTP (0.0.0.0:4318)
   - **Processors**: `batch` (5s timeout, 1024 batch size)
   - **Exporters**:
     - `otlp/jaeger`: forward traces to `jaeger:4317` (insecure TLS)
     - `prometheus`: expose metrics on `0.0.0.0:8889` with `crawllmer` namespace
     - `debug`: logs to collector stdout (for log pipeline — Loki deferred to High Effort)
   - **Pipelines**:
     - `traces`: otlp → batch → otlp/jaeger
     - `metrics`: otlp → batch → prometheus
     - `logs`: otlp → batch → debug
3. Write `infra/prometheus/prometheus.yml`:
   - Global scrape interval: 15s
   - Scrape job `otel-collector` targeting `otel-collector:8889`
4. Write `infra/grafana/provisioning/datasources/datasources.yaml`:
   - Datasource 1: Jaeger at `http://jaeger:16686` (type: jaeger)
   - Datasource 2: Prometheus at `http://prometheus:9090` (type: prometheus, default: true)
5. Validate YAML syntax (no runtime test yet — that's Task 005)

## Done Criteria

- [ ] `infra/otel-collector-config.yaml` is valid and defines traces, metrics, and logs pipelines
- [ ] `infra/prometheus/prometheus.yml` scrapes the collector's Prometheus exporter
- [ ] `infra/grafana/provisioning/datasources/datasources.yaml` auto-provisions Jaeger + Prometheus datasources
- [ ] All YAML files pass syntax validation
- [ ] `make check` passes (no app code changed)

## Notes

- Using `otel/opentelemetry-collector-contrib` image (not the core image) because we need the `prometheus` exporter which is in contrib.
- Jaeger 2.x natively accepts OTLP — no need for the deprecated Jaeger exporter in the collector. We forward traces as OTLP to Jaeger's own OTLP receiver.
- Logs go to `debug` exporter (collector stdout) for now. Loki integration is deferred to the High Effort version.
