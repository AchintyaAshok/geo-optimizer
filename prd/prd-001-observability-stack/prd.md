# PRD 001: Observability Stack

## Overview

Add production-grade observability to crawllmer using OpenTelemetry as the single telemetry protocol for traces, metrics, and structured logs. The project already has a thin OTEL instrumentation layer (`observability.py`) with a meter, tracer, and `log_event()` helper — but no exporters are configured, no collector exists, and there is no way to actually view any telemetry data.

This PRD covers:
1. **Bootstrapping OTEL SDK** — configure exporters for traces, metrics, and logs so telemetry actually leaves the process.
2. **Structured logging** — replace raw `json.dumps` log calls with the OTEL Logs SDK so logs carry trace context and flow through the same pipeline.
3. **Auto-instrumentation** — add OTEL instrumentation for FastAPI, httpx, Celery, and SQLModel/SQLite so every request, outbound HTTP call, task execution, and DB query produces spans automatically.
4. **Custom events & enrichment** — enhance the existing `log_event()` to emit OTEL log records with span context, and add domain-specific span events (page discovered, metadata extracted, llms.txt generated).
5. **OTEL Collector config** — a `otel-collector-config.yaml` that receives OTLP, processes telemetry, and exports to Jaeger (traces), Prometheus (metrics), and optionally Loki (logs).
6. **Docker Compose observability stack** — a `docker-compose.observability.yml` overlay that runs the OTEL Collector, Jaeger, Prometheus, and Grafana with pre-configured datasources.
7. **Dual-runtime support** — local (non-Docker) development sends OTLP to `localhost:4317`; Dockerized runtime sends to `otel-collector:4317`. Controlled by a single env var.

### Why now

The crawl pipeline is multi-stage and async (Celery). Without distributed tracing, debugging a failed run requires correlating logs across the API process and worker process manually. Metrics (stage durations, error rates, queue depths) exist in code but are never exported. This work closes the gap between "instrumented" and "observable."

## Linked Tickets

| Ticket | Title | Status |
|--------|-------|--------|
| - | - | - |

## Measures of Success

- [ ] Running `make check` passes — no regressions in existing tests
- [ ] `docker compose -f docker-compose.yml -f docker-compose.observability.yml up` starts the full stack (app + worker + collector + Jaeger + Prometheus + Grafana) with no manual config
- [ ] A crawl run produces end-to-end traces visible in Jaeger spanning API → Celery task → each pipeline stage
- [ ] Prometheus scrapes OTEL Collector and shows `crawllmer_pipeline_*` metrics
- [ ] Grafana loads with pre-configured datasources (Jaeger + Prometheus) — no manual datasource setup
- [ ] Local `make run-api` with `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317` sends telemetry to a locally running collector
- [ ] Structured logs include `trace_id` and `span_id` fields when emitted inside a traced context
- [ ] Auto-instrumentation spans appear for FastAPI requests, httpx calls, and Celery task execution

## Low Effort Version

The minimum that delivers real observability value:

### 1. OTEL SDK bootstrap module (`src/crawllmer/application/telemetry_setup.py`)
- Configure `TracerProvider`, `MeterProvider`, and `LoggerProvider` with **dual-mode exporter selection**:
  - **OTLP mode** (when `OTEL_EXPORTER_OTLP_ENDPOINT` is set): OTLP gRPC exporters for traces, metrics, and logs — sends to collector
  - **Console mode** (when env var is unset or empty): `ConsoleSpanExporter`, `ConsoleMetricExporter`, `ConsoleLogExporter` — structured telemetry printed to stdout for local dev without any infra
- Wire a Python `logging.Handler` that bridges stdlib logging → OTEL Logs SDK (so `log_event()` output flows through OTEL with trace context)
- Call `setup_telemetry()` once at app startup (FastAPI lifespan) and worker startup (Celery `worker_init` signal)
- Set `service.name=crawllmer-api` / `crawllmer-worker` resource attribute to distinguish processes in Jaeger
- **Important**: Without this dual-mode design, OTLP exporters pointing at a non-running collector silently drop all telemetry after retries — the OTEL SDK is designed to be non-intrusive but this means zero visibility. Console mode ensures `make run-api` always produces readable trace/metric/log output in the terminal

### 2. Auto-instrumentation
- Add `opentelemetry-instrumentation-fastapi` — auto-instruments all endpoints
- Add `opentelemetry-instrumentation-httpx` — auto-instruments outbound crawl requests
- Add `opentelemetry-instrumentation-celery` — auto-instruments task send/receive with trace propagation
- Add `opentelemetry-instrumentation-sqlite3` — auto-instruments DB queries
- Activate instrumentors in `setup_telemetry()`

### 3. Enhance existing `observability.py`
- `log_event()` emits an OTEL LogRecord (via the configured LoggerProvider) in addition to stdlib logging, automatically inheriting trace/span context
- Add span events to existing stage spans (e.g., `span.add_event("page.discovered", {"url": url})`)
- No breaking changes — `PipelineTelemetry` API stays the same

### 4. OTEL Collector config (`infra/otel-collector-config.yaml`)
```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 5s
    send_batch_size: 1024

exporters:
  otlp/jaeger:
    endpoint: jaeger:4317
    tls:
      insecure: true
  prometheus:
    endpoint: 0.0.0.0:8889
    namespace: crawllmer

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/jaeger]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus]
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug]
```

### 5. Docker Compose observability overlay (`docker-compose.observability.yml`)
- **otel-collector** — `otel/opentelemetry-collector-contrib`, port 4317 (gRPC), 4318 (HTTP), 8889 (Prometheus scrape)
- **jaeger** — `jaegertracing/jaeger:2`, port 16686 (UI), receives OTLP on 4317
- **prometheus** — `prom/prometheus`, port 9090, scrapes collector :8889
- **grafana** — `grafana/grafana`, port 3000, provisioned datasources for Jaeger + Prometheus
- Override `api` and `worker` services to set `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317`

### 6. Provisioning files
- `infra/prometheus/prometheus.yml` — scrape config targeting `otel-collector:8889`
- `infra/grafana/provisioning/datasources/datasources.yaml` — auto-provisions Jaeger + Prometheus datasources

### 7. Makefile targets
- `make run-observability` — `docker compose -f docker-compose.yml -f docker-compose.observability.yml up --build`
- Update `.env.example` with `OTEL_EXPORTER_OTLP_ENDPOINT`

## High Effort Version

Everything in Low Effort, plus:

- **Loki** for log aggregation — add Loki to the compose stack, add OTEL Collector `loki` exporter, Grafana datasource provisioned
- **Pre-built Grafana dashboards** — JSON dashboard definitions for pipeline metrics (stage durations, error rates, throughput), request latency (p50/p95/p99), and Celery task metrics
- **Exemplars** — link Prometheus metrics to Jaeger traces via exemplars on histograms
- **Custom metrics** — add `crawllmer_http_requests_total`, `crawllmer_pages_discovered_total`, `crawllmer_llms_txt_generated_total` counters
- **Baggage propagation** — propagate `run_id` as OTEL baggage so it appears on all downstream spans without explicit passing
- **Health check spans** — exclude `/health` endpoint from tracing to reduce noise
- **Alerting rules** — Prometheus alerting rules for error rate > 5%, stage duration > 30s, worker queue backlog

## Possible Future Extensions

- **Continuous profiling** via Pyroscope integration
- **SLO dashboards** tracking error budgets
- **Deployment to cloud-managed OTEL** (AWS X-Ray, GCP Cloud Trace, Datadog) by swapping collector exporters — zero app code changes
- **Synthetic monitoring** — scheduled crawls with Grafana Synthetic Monitoring
- **Log-to-trace correlation** in Grafana Explore (requires Loki + Tempo/Jaeger linking)

## Approval State

| Status | Date | Notes |
|--------|------|-------|
| Draft | 2026-03-18 | Initial draft |
| Approved | 2026-03-18 | User approved — proceeding to task breakdown |
