# Design Decisions

Key technical decisions and the trade-offs behind them.

## Hexagonal Architecture

**Decision**: Organize code into domain, application, adapters, and web layers with abstract ports.

**Why**: The assignment asks for a crawl → extract → generate pipeline. Putting that logic behind abstract interfaces (`CrawlRepository`, `QueuePublisher`) means we can test the pipeline with in-memory stubs, swap SQLite for Postgres later, or replace Celery with another queue — all without changing business logic. The indirection cost is minimal for a project this size and pays for itself immediately in testability.

**Trade-off**: More files and directories than a flat structure. Worth it for the separation of concerns.

## Hierarchical Discovery Strategy

**Decision**: Check `/llms.txt` first, then `robots.txt`, then `sitemap.xml`, then fall back to a BFS spider crawl.

**Why**: If a site already publishes an `llms.txt` file, that's the canonical source and we should respect it. The robots → sitemap fallback chain gives broad page coverage. When none of these exist, a bounded BFS spider follows `<a href>` links from the seed URL, building an in-link count map to rank pages by importance. The top-N pages (configurable via `CRAWLLMER_SPIDER_MAX_INDEX_PAGES`) are indexed.

**Trade-off**: The spider adds crawl time (10-30s for moderate sites) but produces far better results than the previous single-page fallback. Depth and page limits prevent unbounded crawling.

## Confidence-Scored Metadata Extraction

**Decision**: Every title and description extraction carries a confidence score (0.0–1.0) based on its HTML source.

**Why**: Not all metadata sources are equal. A `<title>` tag (1.0) is more reliable than an Open Graph tag (0.8), which is more reliable than JSON-LD (0.6). During canonicalization, when multiple pages resolve to the same URL, the highest-confidence extraction wins. The scores also flow into the overall quality score, giving users a transparent signal about result quality.

**Trade-off**: The confidence values are hand-tuned heuristics, not learned from data. They're reasonable defaults that work well in practice.

## SQLite for Everything

**Decision**: Use SQLite as the app database, Celery broker, and result backend.

**Why**: Zero external dependencies for local development. A developer can `make sync && make run-dev` and have a working system without installing Redis, Postgres, or any other service. SQLite is more than sufficient for the single-user, moderate-throughput use case this app targets.

**Trade-off**: SQLite has write concurrency limitations. For production, we support Postgres (`CRAWLLMER_STORAGE_BACKEND=pgsql`) with Redis for the Celery broker. Docker Compose profiles (`redis`, `distributed`) make it easy to switch. SQLite remains the default for zero-dependency local development.

## Celery Task Queue

**Decision**: Use Celery for async pipeline execution, even though the current API processes synchronously.

**Why**: The pipeline involves network I/O (fetching pages) that can take seconds to minutes. Celery gives us:
- A worker process that can run independently of the API
- Task retries with the infrastructure built in
- A path to horizontal scaling (add more workers)
- Redis support when SQLite's broker limitations are reached

The `/process` endpoint currently runs the pipeline synchronously (blocking the request), but the Celery infrastructure is in place for true async processing where the API enqueues and the worker executes.

**Trade-off**: Celery adds dependency weight. We mitigate this by using the SQLite broker (no Redis required by default), which makes the operational footprint identical to a simple web app.

## Deterministic Output

**Decision**: Sort `llms.txt` entries by URL.

**Why**: The same input should produce the same output. Sorting makes the output diffable, testable, and reproducible. Users can re-run a crawl and easily see what changed. Tests can assert exact output without worrying about ordering.

**Trade-off**: None meaningful. Sorting a list of URLs is trivial.

## Work-Item State Machine

**Decision**: Track each pipeline stage as a `WorkItem` with explicit state transitions and an event audit trail.

**Why**: Visibility into pipeline execution. The state machine (`queued → processing → completed/failed`) enforces valid transitions at the domain level — you can't go from `queued` directly to `completed`, for example. The audit trail (`WorkItemEventRecord`) records every transition with timestamps, which powers the event timeline in the Streamlit UI and aids debugging.

**Trade-off**: More database writes per pipeline run. The overhead is negligible for the throughput we need.

## Dual UI (FastAPI + Streamlit)

**Decision**: Provide both a REST API and a Streamlit UI.

**Why**: Different users have different needs. The REST API is for programmatic access, integrations, and CI/CD pipelines. The Streamlit UI is for interactive use — paste a URL, watch stages progress, inspect results. The UI delegates all operations to the API via an HTTP client (`api_client.py`) — it has no direct database or broker access.

**Trade-off**: Two UI surfaces to maintain. Streamlit is low-maintenance by design (it's a single Python file), and the API is thin (routes delegate to the pipeline orchestrator). The UI-as-API-client architecture means the UI service only needs one config var (`CRAWLLMER_API_BASE_URL`).

## Retry Policy with Exponential Backoff

**Decision**: Wrap stage execution in a retry policy with 2 retries, 50ms base delay, and 2× multiplier.

**Why**: Network requests fail. Transient errors (timeouts, 503s) are common when crawling websites. The retry policy handles these without manual intervention. The backoff is aggressive (50ms → 100ms → 200ms) because we're crawling external sites and don't want to overwhelm them, but we also don't want to wait forever.

**Trade-off**: A failed stage takes ~350ms before giving up (50 + 100 + 200ms of delays plus the actual requests). This is acceptable for a batch processing pipeline.

## Per-Host Rate Limiting

**Decision**: Implement a `HostRateLimiter` that enforces minimum delays between requests to the same host.

**Why**: Polite crawling. We don't want to hammer a single website with concurrent requests. The rate limiter tracks the last request time per host and blocks until the minimum delay (10ms) has elapsed. An adaptive penalty (50ms) is applied after receiving throttling signals.

**Trade-off**: Slower crawling of individual hosts. This is the right trade-off — we prioritize being a good citizen over speed.

## OpenTelemetry Observability

**Decision**: Instrument the pipeline with OpenTelemetry metrics and spans.

**Why**: The pipeline has multiple stages with network I/O, and debugging failures requires knowing what happened at each stage. OTel provides:
- Counters for state transitions, run outcomes, and stage outcomes
- Histograms for stage durations
- Spans with attributes that nest inside a run-level parent span
- Structured JSON logging via `log_event()`

This is wired up but doesn't require an OTel collector to run — it degrades gracefully to local metrics.

**Trade-off**: The `opentelemetry-api` and `opentelemetry-sdk` dependencies. These are lightweight and don't impact runtime performance when no exporter is configured.

## Observability Events (Business Metrics)

**Decision**: Separate business-level metrics from stage-level pipeline telemetry, using structured event dataclasses as the single emission point.

**Why**: The existing `PipelineTelemetry` tracks execution mechanics — stage durations, state transitions, outcome counters. These are useful for debugging but don't answer product-level questions like "how many pages did we index?" or "how big was the output?". Business metrics (`crawllmer_pages_indexed_total`, `crawllmer_run_duration_seconds`, `crawllmer_llmstxt_size_bytes`) live on a separate `crawllmer.business` OTEL meter and track run-level outcomes that matter to users.

Each pipeline milestone is represented by a typed `EventMetadata` subclass (e.g. `DiscoveryCompletedEvent`, `RunCompletedEvent`). The event's `to_attributes()` method serialises its fields into OTEL-compatible key-value pairs. The same event object drives both structured log emission (via `log_event()`) and metric recording (via `BusinessMetrics`), ensuring a single emission point with no double-counting.

**Trade-off**: More classes and a second OTEL meter. The separation keeps concerns clear — stage telemetry is internal debugging; business metrics are user-facing. The event dataclasses add a small amount of code but make the emission contract explicit and testable.

## Error Handling

**Decision**: Replace all generic `Exception` and `ValueError` catches with a typed exception hierarchy rooted in `CrawllmerError`.

**Why**: The codebase previously caught bare `Exception` in the orchestrator and web layer, making it impossible to distinguish between a bad user URL, a missing run, a network failure, and an internal bug. Typed exceptions enable:
- Precise HTTP status mapping in the web layer (`InvalidInputError` → 422, `RunNotFoundError` → 404, `PipelineProcessingError` → 500)
- Structured error attributes (stage name, URL, status code) that flow into logs and traces
- `PipelineProcessingError` wraps the original exception as `__cause__`, preserving the full causal chain for debugging while giving callers a single type to catch at the boundary

Each error class has an explicit `__init__` that stores structured attributes and produces a human-readable `str()`. This makes errors both programmatically inspectable (`exc.stage`, `exc.url`) and readable in tracebacks.

**Approved exception**: `retry.py` retains a bare `except Exception` because a generic retry wrapper cannot know what exceptions its callable may raise. This is the only file exempt from the typed-exceptions rule.

## Fresh Extraction (No Cached Validators)

**Decision**: New crawl runs always fetch pages fresh — cached ETag/If-Modified-Since validators are not used.

**Why**: The validator system stores `ETag` and `Last-Modified` headers from previous fetches. On subsequent requests, it sends conditional headers and skips pages that return `304 Not Modified`. This is correct for incremental re-crawls but wrong for new llms.txt generation — a user submitting a URL expects a complete result, not one that skips pages because they haven't changed since a previous run. In production, this caused empty llms.txt output on re-crawls of the same site.

**What we keep**: Validators are still stored after each fetch (for future incremental re-crawl support). They're just not loaded when building a new run's extraction plan.

**Trade-off**: Every run re-downloads all pages, even if unchanged. This is the correct default for a generation tool. Incremental re-crawl (using validators to skip unchanged pages) is a future optimization that would need explicit user opt-in.

## Task Reliability (acks_late + reject_on_worker_lost)

**Decision**: Configure Celery to acknowledge tasks after completion and reject them on worker loss.

**Why**: The default Celery behavior acknowledges tasks before execution starts. If a worker crashes mid-crawl, the task is lost — the run stays in `queued`/`running` in the database forever. With `acks_late=True`, the broker retains the message until the worker explicitly acknowledges it after completion. If the worker dies, the broker automatically redelivers the task to another worker.

**What this protects against**: Worker crashes, OOM kills, graceful restarts — any scenario where the worker process dies but the broker (Redis) is healthy.

**What this does NOT protect against**: Broker failures (Redis restart, data loss). If the broker loses messages, runs stuck in `queued`/`running` in the database become orphans with no corresponding task in the queue. Recovering those requires a separate stale-run-recovery mechanism (database scan + re-enqueue) which is not yet implemented.

**Why it's safe**: Our pipeline stages are idempotent — they use upserts, not inserts. Re-executing a partially completed run overwrites previous results and fills in gaps. The only side effect is duplicate event records (append-only audit trail), which is harmless.

**Trade-off**: Tasks can be executed more than once on worker failure. This is acceptable because of the idempotent design. The `visibility_timeout` (default 1 hour for Redis) must be longer than the longest expected crawl to avoid premature redelivery.

## UI as API Client

The Streamlit UI delegates all data operations to the REST API via an HTTP client (`api_client.py`) — no direct database or broker access. In production the UI service needs only `CRAWLLMER_API_BASE_URL`. This makes deployment simpler and keeps the API as the single gateway to the backend. The trade-off is ~1-5ms latency per request, negligible on the same network.

## Module Organisation: `app/{api, web, indexer}`

Three application runtimes live as sibling packages under `app/`, with shared business logic in `core/` and persistence in `adapters/`. The original `application/` grab-bag (orchestrator + queueing + workers + scheduling) was eliminated — orchestration logic moved to `core/`, Celery infrastructure to `app/indexer/`. Each `app/*` package maps to an independently deployable service.

## Pluggable Storage Backend

A `CRAWLLMER_STORAGE_BACKEND` Literal enum (`sqlite` | `pgsql`) selects the backend at startup. Backend-specific repository subclasses (`SqliteStorageRepository`, `PgSqlStorageRepository`) configure their own engine kwargs — `check_same_thread=False` for SQLite, `pool_pre_ping=True` + `pool_size=5` for Postgres. A `get_storage()` factory function instantiates the right one. Postgres credentials can be provided as individual `PG_*` env vars or a single `DATABASE_URL`.

## Two-Phase Spider with In-Link Ranking

The fallback spider (tier 4 discovery) runs in two phases: Phase 1 BFS-scans the site to build a link graph and rank pages by in-link count (PageRank intuition); Phase 2 indexes the top-N pages via the task queue. BFS over DFS because we want breadth — top-level pages (`/docs`, `/blog`, `/api`) matter more than deeply nested sub-pages. Bounds are config-driven: `max_depth=3`, `max_scan_pages=100`, `max_index_pages=50`.

## Extension Allowlist Filtering

The spider only indexes pages with extensions in a configurable allowlist (`.html`, `.htm`, `.txt`, `.md`, and extensionless paths). Assets (`.css`, `.js`, `.png`, `.pdf`) are skipped. An allowlist is safer than a blocklist — we only index what we know is content. Extensionless paths are included because modern frameworks serve HTML at clean URLs.

## Pipeline Event Auditability

Every spider and extraction decision is recorded as a `CrawlEvent` — which pages were scanned, which links were followed or skipped and why, which pages returned errors. The existing `GET /api/v1/crawls/{id}/events` endpoint serves the full audit trail. Large crawls produce 1000+ events; the UI shows the last 8 as a live log with a collapsible dataframe for the full set.

## Single Dockerfile, Multiple Services

One `Dockerfile` builds all three services (API, UI, Worker). The entrypoint is overridden per service via Docker Compose `command` or Railway `railway.toml`. All services share the same codebase and dependencies, ensuring identical code at deploy time with no drift risk.
