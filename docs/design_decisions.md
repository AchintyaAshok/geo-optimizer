# Design Decisions

Key technical decisions and the trade-offs behind them.

## Hexagonal Architecture

**Decision**: Organize code into domain, application, adapters, and web layers with abstract ports.

**Why**: The assignment asks for a crawl → extract → generate pipeline. Putting that logic behind abstract interfaces (`CrawlRepository`, `QueuePublisher`) means we can test the pipeline with in-memory stubs, swap SQLite for Postgres later, or replace Celery with another queue — all without changing business logic. The indirection cost is minimal for a project this size and pays for itself immediately in testability.

**Trade-off**: More files and directories than a flat structure. Worth it for the separation of concerns.

## Hierarchical Discovery Strategy

**Decision**: Check `/llms.txt` first, then `robots.txt`, then `sitemap.xml`, then fall back to the seed URL.

**Why**: If a site already publishes an `llms.txt` file, that's the canonical source and we should respect it. The robots → sitemap → seed fallback chain gives us broad page coverage even when `llms.txt` doesn't exist. This order minimizes unnecessary HTTP requests — most sites will hit on one of the first two strategies.

**Trade-off**: We don't do deep recursive crawling. This is intentional: the goal is to produce a useful `llms.txt` quickly, not to spider an entire website. The sitemap strategy handles large sites well, and the fallback seed ensures we always have at least one page.

## Confidence-Scored Metadata Extraction

**Decision**: Every title and description extraction carries a confidence score (0.0–1.0) based on its HTML source.

**Why**: Not all metadata sources are equal. A `<title>` tag (1.0) is more reliable than an Open Graph tag (0.8), which is more reliable than JSON-LD (0.6). During canonicalization, when multiple pages resolve to the same URL, the highest-confidence extraction wins. The scores also flow into the overall quality score, giving users a transparent signal about result quality.

**Trade-off**: The confidence values are hand-tuned heuristics, not learned from data. They're reasonable defaults that work well in practice.

## SQLite for Everything

**Decision**: Use SQLite as the app database, Celery broker, and result backend.

**Why**: Zero external dependencies for local development. A developer can `make sync && make run-dev` and have a working system without installing Redis, Postgres, or any other service. SQLite is more than sufficient for the single-user, moderate-throughput use case this app targets.

**Trade-off**: SQLite has write concurrency limitations. For multi-worker production deployments, we provide a Redis compose extension that swaps the Celery broker and result backend to Redis. The app database stays SQLite because SQLModel handles it well and the read/write patterns are simple.

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

**Why**: Different users have different needs. The REST API is for programmatic access, integrations, and CI/CD pipelines. The Streamlit UI is for interactive use — paste a URL, watch stages progress, inspect results. Both share the same backend (`runtime.py` initializes shared repository and pipeline instances).

**Trade-off**: Two UI surfaces to maintain. Streamlit is low-maintenance by design (it's a single Python file), and the API is thin (routes delegate to the pipeline orchestrator).

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
