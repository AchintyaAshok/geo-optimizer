---
parent_prd: ../prd-001-observability-stack/prd.md
prd_name: "PRD 001: Observability Stack"
prd_id: 001
task_id: 001
created: 2026-03-18
state: pending
---

# Task 001: OTEL SDK bootstrap with dual-mode exporters

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

Create `src/crawllmer/application/telemetry_setup.py` — the single entrypoint for bootstrapping the OTEL SDK across all crawllmer processes. Configures TracerProvider, MeterProvider, and LoggerProvider with dual-mode exporter selection (OTLP when a collector is available, console fallback when it isn't). Add required OTEL dependencies to `pyproject.toml`.

## Inputs

- Existing `observability.py` (uses `metrics.get_meter()` and `trace.get_tracer()` — these must pick up the providers we configure)
- `pyproject.toml` (already has `opentelemetry-api` and `opentelemetry-sdk`)
- `web/app.py` (FastAPI app — needs lifespan hook)
- `celery_app.py` / `worker.py` (Celery — needs `worker_init` signal)

## Outputs

- `src/crawllmer/application/telemetry_setup.py` — `setup_telemetry(service_name: str)` function
- Updated `pyproject.toml` with new OTEL exporter dependencies
- FastAPI lifespan calls `setup_telemetry("crawllmer-api")` on startup
- Celery worker calls `setup_telemetry("crawllmer-worker")` on `worker_init`
- Updated `.env.example` with `OTEL_EXPORTER_OTLP_ENDPOINT`

## Steps

1. Add dependencies to `pyproject.toml`:
   - `opentelemetry-exporter-otlp-proto-grpc` (OTLP exporter)
   - `opentelemetry-sdk` (already present — verify version)
2. Create `telemetry_setup.py` with `setup_telemetry(service_name: str)`:
   - Build a `Resource` with `service.name` and `service.version`
   - Check `os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")`
   - If set: create `OTLPSpanExporter`, `OTLPMetricExporter`, `OTLPLogExporter` pointed at the endpoint
   - If unset: create `ConsoleSpanExporter`, `ConsoleMetricExporter`, `ConsoleLogExporter`
   - Configure and set global `TracerProvider` with a `BatchSpanProcessor`
   - Configure and set global `MeterProvider` with a `PeriodicExportingMetricReader`
   - Configure and set global `LoggerProvider` with a `BatchLogRecordProcessor`
   - Attach a `LoggingHandler` to the root Python logger (or the `crawllmer` logger) so stdlib log records flow through the OTEL Logs pipeline
3. Wire into FastAPI: add/update lifespan in `web/app.py` to call `setup_telemetry("crawllmer-api")`
4. Wire into Celery: add a `worker_init` signal handler in `celery_app.py` to call `setup_telemetry("crawllmer-worker")`
5. Update `.env.example` with `OTEL_EXPORTER_OTLP_ENDPOINT=` (commented out, with explanation)
6. Write unit tests for `setup_telemetry()` — verify providers are configured, verify console vs OTLP mode selection
7. Run `make check` to ensure no regressions

## Done Criteria

- [ ] `setup_telemetry("crawllmer-api")` configures OTEL providers and is called at FastAPI startup
- [ ] `setup_telemetry("crawllmer-worker")` is called at Celery worker init
- [ ] When `OTEL_EXPORTER_OTLP_ENDPOINT` is set, OTLP gRPC exporters are used
- [ ] When `OTEL_EXPORTER_OTLP_ENDPOINT` is unset, console exporters are used (telemetry visible in stdout)
- [ ] Existing `PipelineTelemetry` class continues to work (its `get_meter`/`get_tracer` calls pick up the configured providers)
- [ ] `make check` passes

## Notes

- The OTEL SDK's `set_tracer_provider()` / `set_meter_provider()` are global — call `setup_telemetry()` exactly once per process.
- Console exporters print human-readable spans/metrics/logs to stdout — useful for local dev without any infra.
- The `LoggingHandler` bridge means any `logging.info()` call inside a traced context will automatically include `trace_id` and `span_id`.
