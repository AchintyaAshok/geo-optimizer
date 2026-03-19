# PRD 006: Core Module — Error Handling and Observability Events

## Overview

Introduce a `core/` package to crawllmer that centralises three cross-cutting concerns currently scattered across the codebase:

1. **Logging configuration** — add a `log_level` setting (default `DEBUG`) to `config.py` and wire it into the OTEL telemetry bootstrap so log severity is configurable.
2. **Custom error hierarchy** — replace all generic `Exception` / `ValueError` catches with typed, well-documented exception classes in `core/errors.py`.
3. **Structured event metadata + business metrics** — define an abstract `EventMetadata` base and concrete event classes in `core/observability/events.py`, plus run-level OTEL metrics (pages indexed, crawl duration, llmstxt size) that complement the existing stage-level `PipelineTelemetry`.

The existing `application/observability.py` and `application/telemetry_setup.py` move into `core/observability/` as part of this restructure.

## Linked Tickets

| Ticket | Title | Status |
|--------|-------|--------|
| - | - | - |

## Measures of Success

- [ ] `make check` passes (format, lint, test) after all changes
- [ ] No generic `Exception` or bare `ValueError` catches remain in `src/crawllmer/` (excluding `retry.py` which must catch broadly by design, and third-party/framework-mandated patterns)
- [ ] `log_level` setting is honoured: setting `CRAWLLMER_LOG_LEVEL=WARNING` suppresses DEBUG/INFO output
- [ ] Business metrics (`crawllmer_pages_indexed_total`, `crawllmer_run_duration_seconds`, `crawllmer_llmstxt_size_bytes`) appear in console exporter output during a test run
- [ ] All existing tests continue to pass with no import errors
- [ ] `.env.example` and `CLAUDE.md` environment variable table include `CRAWLLMER_LOG_LEVEL`
- [ ] `docs/design_decisions.md` has new sections for Observability Events and Error Handling

## Low Effort Version

This is the target — all three concerns addressed in a single pass:

### 1. Config: `log_level` setting

Add to `Settings` in `config.py`:

```python
from typing import Literal

log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG"
```

Using `Literal` means Pydantic will reject invalid values like `CRAWLLMER_LOG_LEVEL=VERBOSE` at startup rather than silently falling back.

In `telemetry_setup.py`, after adding the OTEL `LoggingHandler`, set the `crawllmer` logger level from this setting:

```python
from crawllmer.config import get_settings

settings = get_settings()
logger = logging.getLogger("crawllmer")
logger.setLevel(getattr(logging, settings.log_level))
logger.addHandler(handler)
```

The OTEL handler stays at `NOTSET` (pass-through). The logger itself gates what severity flows into the pipeline.

Update `.env.example` and the `CLAUDE.md` environment variable table to include `CRAWLLMER_LOG_LEVEL`.

### 2. Directory restructure

```
src/crawllmer/core/
├── __init__.py                    # Re-exports all error classes for convenience:
│                                  #   from crawllmer.core import RunNotFoundError
├── errors.py                      # Custom exception hierarchy
└── observability/
    ├── __init__.py                # Re-exports: log_event, PipelineTelemetry, setup_telemetry,
    │                              #   BusinessMetrics, EventMetadata, and all concrete events
    ├── events.py                  # Abstract EventMetadata + concrete events + BusinessMetrics
    ├── pipeline_telemetry.py      # Moved from application/observability.py
    └── telemetry_setup.py         # Moved from application/telemetry_setup.py
```

Delete `application/observability.py` and `application/telemetry_setup.py` after moving.

Update all imports across the codebase:
- `crawllmer.application.observability` → `crawllmer.core.observability`
- `crawllmer.application.telemetry_setup` → `crawllmer.core.observability`

Affected files (imports):
- `application/orchestrator.py` — imports `PipelineTelemetry`, `log_event`
- `web/app.py` — imports `log_event`, `setup_telemetry`
- `celery_app.py` — imports `setup_telemetry`
- `web/streamlit_app.py` — catches `ValueError` from pipeline, needs `InvalidInputError`
- `tests/integration/test_pipeline_flow.py` — imports `PipelineTelemetry`
- `tests/unit/test_orchestrator.py` — asserts on `ValueError` for unknown runs, needs `RunNotFoundError`

### 3. Error hierarchy — `core/errors.py`

Each error class has an explicit `__init__` that stores structured attributes and produces a human-readable message via `super().__init__()`. This ensures both programmatic access (`exc.stage`) and readable tracebacks.

**Approved exception to the no-generic-catches rule**: `retry.py` must catch bare `Exception` by design — a generic retry wrapper cannot know what exceptions its callable may raise. This is the only file exempt from the rule.

```python
from __future__ import annotations

from uuid import UUID


class CrawllmerError(Exception):
    """Base exception for all crawllmer errors.

    All project-specific exceptions inherit from this class so callers
    can catch broadly when they don't need to distinguish failure modes.
    """


class MissingConfigError(CrawllmerError):
    """A required configuration value is absent or empty.

    Raised when a module attempts to use a Settings field that has no
    usable value — either because the environment variable was never set
    and there is no default, or because the value is present but invalid
    for the module's needs (e.g. an empty string where a URL is required).
    """

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name
        super().__init__(f"missing or invalid config: {field_name}")


class InvalidInputError(CrawllmerError):
    """User-supplied input fails validation.

    Raised at the API / pipeline boundary when input data cannot be
    processed — for example, a malformed URL passed to enqueue_run().
    Replaces the generic ValueError currently used for input validation.
    """

    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"invalid {field}: {reason}")


class RunNotFoundError(CrawllmerError):
    """A requested crawl run does not exist in the repository.

    Raised when a run_id is passed to process_run(), get_run(), or any
    operation that requires an existing run, but no matching record is
    found. Distinct from InvalidInputError because the input format is
    valid — the resource simply doesn't exist.
    """

    def __init__(self, run_id: UUID) -> None:
        self.run_id = run_id
        super().__init__(f"run not found: {run_id}")


class PipelineProcessingError(CrawllmerError):
    """A named pipeline stage failed during execution.

    Raised by the orchestrator when a stage (discovery, extraction,
    canonicalization, scoring, or generation) encounters an unrecoverable
    error after retries are exhausted. Wraps the original exception as
    __cause__ so the full error chain is preserved for debugging.
    """

    def __init__(self, stage: str, run_id: UUID, cause: Exception) -> None:
        self.stage = stage
        self.run_id = run_id
        super().__init__(f"stage '{stage}' failed for run {run_id}: {cause}")
        self.__cause__ = cause


class CrawlFetchError(CrawllmerError):
    """An HTTP request to a target website failed.

    Raised during the discovery or extraction stages when an HTTP request
    returns an unexpected status code, times out, or encounters a
    connection error. Carries the URL and status code (if available) so
    callers can decide whether to retry, skip, or abort.
    """

    def __init__(
        self, url: str, status_code: int | None = None, reason: str = ""
    ) -> None:
        self.url = url
        self.status_code = status_code
        self.reason = reason
        detail = f"status {status_code}" if status_code else reason
        super().__init__(f"fetch failed for {url}: {detail}")


class ContentExtractionError(CrawllmerError):
    """HTML or metadata parsing failed for a fetched page.

    Raised when a page was successfully fetched (HTTP 200) but the
    content could not be parsed — for example, malformed HTML that
    crashes BeautifulSoup, or a page that returns non-HTML content
    (PDF, image) despite a text/html Content-Type header.
    """

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"extraction failed for {url}: {reason}")


class GenerationError(CrawllmerError):
    """llms.txt assembly failed after extraction completed.

    Raised during the generation stage when the extracted pages cannot
    be assembled into a valid llms.txt document — for example, if zero
    pages survived canonicalization, or if the document builder
    encounters an internal inconsistency.
    """

    def __init__(self, run_id: UUID, reason: str) -> None:
        self.run_id = run_id
        self.reason = reason
        super().__init__(f"generation failed for run {run_id}: {reason}")
```

### 4. Events — `core/observability/events.py`

Event classes use `@dataclass(slots=True)` to match the project's existing convention (`StageExecution`, `RetryPolicy`).

**Abstract base class:**

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


@dataclass(slots=True)
class EventMetadata(ABC):
    """Base for structured event data emitted during pipeline execution.

    Subclasses represent specific pipeline milestones. Each event can
    serialise itself to OTEL-compatible attributes via to_attributes()
    and is emitted through log_event() for structured logging. The same
    event data drives business-level OTEL metric recording, ensuring a
    single emission point with no double-counting.
    """

    run_id: UUID
    event_name: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @abstractmethod
    def to_attributes(self) -> dict[str, str | int | float]:
        """Return OTEL span/log-compatible key-value pairs."""
        ...
```

**Concrete event classes:**

```python
@dataclass(slots=True)
class DiscoveryCompletedEvent(EventMetadata):
    """Emitted when the discovery stage completes for a run."""

    event_name: str = "discovery.completed"
    pages_discovered: int = 0
    strategies_used: list[str] = field(default_factory=list)

    def to_attributes(self) -> dict[str, str | int | float]:
        return {
            "run.id": str(self.run_id),
            "discovery.pages_discovered": self.pages_discovered,
            "discovery.strategies_used": ",".join(self.strategies_used),
        }


@dataclass(slots=True)
class ExtractionCompletedEvent(EventMetadata):
    """Emitted when the extraction stage completes for a run."""

    event_name: str = "extraction.completed"
    pages_extracted: int = 0
    pages_skipped: int = 0

    def to_attributes(self) -> dict[str, str | int | float]:
        return {
            "run.id": str(self.run_id),
            "extraction.pages_extracted": self.pages_extracted,
            "extraction.pages_skipped": self.pages_skipped,
        }


@dataclass(slots=True)
class GenerationCompletedEvent(EventMetadata):
    """Emitted when llms.txt generation completes for a run."""

    event_name: str = "generation.completed"
    llmstxt_size_bytes: int = 0
    entry_count: int = 0

    def to_attributes(self) -> dict[str, str | int | float]:
        return {
            "run.id": str(self.run_id),
            "generation.llmstxt_size_bytes": self.llmstxt_size_bytes,
            "generation.entry_count": self.entry_count,
        }


@dataclass(slots=True)
class RunCompletedEvent(EventMetadata):
    """Emitted when a full pipeline run completes (success or failure)."""

    event_name: str = "run.completed"
    total_pages_indexed: int = 0
    duration_seconds: float = 0.0
    llmstxt_size_bytes: int = 0

    def to_attributes(self) -> dict[str, str | int | float]:
        return {
            "run.id": str(self.run_id),
            "run.total_pages_indexed": self.total_pages_indexed,
            "run.duration_seconds": self.duration_seconds,
            "run.llmstxt_size_bytes": self.llmstxt_size_bytes,
        }
```

**Business-level OTEL metrics** (on a `crawllmer.business` meter, separate from `crawllmer.pipeline`):

| Metric Name | Type | Description |
|-------------|------|-------------|
| `crawllmer_pages_indexed_total` | Counter | Total pages indexed per run |
| `crawllmer_run_duration_seconds` | Histogram | End-to-end run duration |
| `crawllmer_llmstxt_size_bytes` | Histogram | Size of generated llms.txt |

These complement the existing stage-level metrics in `PipelineTelemetry`. Stage metrics track execution mechanics (stage duration, stage outcomes). Business metrics track run-level outcomes that matter to users.

A `BusinessMetrics` class lives in `events.py` alongside the event dataclasses. It is instantiated once (like `PipelineTelemetry`) and injected into the orchestrator. It registers the three instruments above and provides methods that accept event objects:

```python
class BusinessMetrics:
    """Run-level OTEL metrics driven by structured event objects."""

    def __init__(self) -> None:
        meter = metrics.get_meter("crawllmer.business")
        self._pages_indexed = meter.create_counter(
            "crawllmer_pages_indexed_total",
            description="Total pages indexed per run",
        )
        self._run_duration = meter.create_histogram(
            "crawllmer_run_duration_seconds",
            description="End-to-end run duration",
            unit="s",
        )
        self._llmstxt_size = meter.create_histogram(
            "crawllmer_llmstxt_size_bytes",
            description="Size of generated llms.txt",
            unit="By",
        )

    def record_run_completed(self, event: RunCompletedEvent) -> None:
        self._pages_indexed.add(event.total_pages_indexed)
        self._run_duration.record(event.duration_seconds)
        self._llmstxt_size.record(event.llmstxt_size_bytes)
```

This keeps metric emission co-located with event emission — one call, no duplication.

### 5. Integration points

**Orchestrator changes** (`application/orchestrator.py`):
- `enqueue_run()`: raise `InvalidInputError("url", "invalid URL")` instead of `ValueError("invalid URL")`
- `process_run()`: raise `RunNotFoundError(run_id)` instead of `ValueError("run not found")`
- `_run_stage()`: the exception wrapping chain works as follows:
  1. Stage callable raises any exception (e.g. `CrawlFetchError`, `ContentExtractionError`, `httpx.TimeoutException`)
  2. `_run_stage()` catches it, does telemetry/logging, then wraps and re-raises: `raise PipelineProcessingError(stage=stage.value, run_id=run.id, cause=exc) from exc`
  3. `process_run()` catches `PipelineProcessingError` specifically (not bare `Exception`), marks the run as failed, logs it, and re-raises
  4. The web layer or Celery task catches `PipelineProcessingError` at the boundary
- After discovery: emit `DiscoveryCompletedEvent`, record `pages_indexed_total`
- After extraction: emit `ExtractionCompletedEvent`
- After generation: emit `GenerationCompletedEvent`, record `llmstxt_size_bytes`
- After full run: emit `RunCompletedEvent`, record `run_duration_seconds`

**Celery task boundary** (`celery_app.py`):
- `process_run_task()` currently has no try/except and lets exceptions propagate to Celery.
- Add a `try/except PipelineProcessingError` that logs the structured error (stage, cause) and re-raises so Celery marks the task as failed. This gives us structured logging at the boundary without swallowing the error. Celery's built-in retry/failure handling continues to work.

**Web layer changes** (`web/app.py`):
- Catch `InvalidInputError` → 422
- Catch `RunNotFoundError` → 404
- Catch `PipelineProcessingError` → 500 (access `exc.stage` and `exc.__cause__` for detail)
- Remove generic `Exception` catches
- **Important**: the `process_run` endpoint currently duplicates run-failure logic (setting `run.status = RunStatus.failed`, calling `repo.update_run`). After this change, the orchestrator's `process_run()` already handles failure marking before re-raising. The web layer should only translate the error into an HTTP response — remove the duplicate state mutation.

**Streamlit changes** (`web/streamlit_app.py`):
- Replace `except ValueError` with `except InvalidInputError` where pipeline is called

**Worker-level errors** (`application/workers.py`):
- The `CrawlFetchError` and `ContentExtractionError` classes are defined in this PRD but **worker functions are not updated to raise them in this pass**. Currently workers silently skip non-200 responses and let parsing errors propagate as stdlib exceptions. Wiring workers to raise typed errors is a natural follow-up but is deferred to keep this PRD focused on the structural changes (module layout, error hierarchy, events). The orchestrator's `_run_stage` wrapping will still catch whatever workers raise and wrap it in `PipelineProcessingError`.

**Test changes**:
- `tests/unit/test_orchestrator.py`: `test_pipeline_rejects_unknown_run` catches `RunNotFoundError` instead of `ValueError`
- `tests/integration/test_pipeline_flow.py`: update import path for `PipelineTelemetry`; failure tests catch `PipelineProcessingError` instead of `RuntimeError`, and assert `exc.__cause__` is the original `RuntimeError("network failure")` to verify the wrapping chain

### 6. Design choices documentation

Add two new sections to `docs/design_decisions.md`:

**Observability Events** — why we separate stage-level telemetry from business-level metrics, the single-emission-point principle, and the `EventMetadata` abstraction.

**Error Handling** — why typed exceptions over generic catches, the hierarchy design rationale, and how `PipelineProcessingError` preserves the causal chain.

## High Effort Version

Everything in Low Effort, plus:

- **Correlation IDs**: Inject trace IDs into all log records for request-level correlation
- **Per-logger configuration**: Allow different log levels for different modules (e.g. `crawllmer.pipeline=DEBUG`, `crawllmer.web=INFO`)
- **Error recovery strategies**: Each error class carries a suggested recovery action (retry, skip, abort) that the orchestrator can use for automatic recovery
- **Metric dashboards**: Pre-built Grafana dashboard JSON for the new business metrics

These are deferred — the low effort version delivers the core value.

## Possible Future Extensions

- Circuit breaker pattern using `CrawlFetchError` frequency per host
- Error rate alerting thresholds based on `PipelineProcessingError` counts
- Event replay / audit log powered by the structured `EventMetadata` records
- Custom metric dimensions (by hostname, by discovery strategy)

## Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans to implement task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Introduce `core/` package with typed errors, structured observability events, business metrics, and configurable log level.

**Architecture:** New `core/` layer sits alongside `domain/`, `application/`, `adapters/`, `web/`. Error classes are cross-cutting. Observability modules move from `application/` into `core/observability/`. Orchestrator and web layer updated to use typed errors and emit structured events.

**Tech Stack:** Python 3.12, pydantic-settings, OpenTelemetry SDK, dataclasses, pytest

---

### Task 1: Create `core/errors.py` with error hierarchy

**Files:**
- Create: `src/crawllmer/core/__init__.py`
- Create: `src/crawllmer/core/errors.py`
- Create: `tests/unit/test_errors.py`

Steps:
- [ ] Write tests for each error class: verify `__init__` stores attributes, `str()` produces expected message, `PipelineProcessingError.__cause__` is set, all inherit from `CrawllmerError`
- [ ] Run tests — confirm they fail (classes don't exist yet)
- [ ] Implement `core/errors.py` with all 7 error classes per the spec (section 3)
- [ ] Implement `core/__init__.py` re-exporting all error classes
- [ ] Run tests — confirm they pass
- [ ] Run `make check`
- [ ] Commit: `feat(core): add typed error hierarchy`

---

### Task 2: Create `core/observability/` package (move existing modules)

**Files:**
- Create: `src/crawllmer/core/observability/__init__.py`
- Create: `src/crawllmer/core/observability/pipeline_telemetry.py` (move from `application/observability.py`)
- Create: `src/crawllmer/core/observability/telemetry_setup.py` (move from `application/telemetry_setup.py`)
- Delete: `src/crawllmer/application/observability.py`
- Delete: `src/crawllmer/application/telemetry_setup.py`
- Modify: `src/crawllmer/application/orchestrator.py` — update imports
- Modify: `src/crawllmer/web/app.py` — update imports
- Modify: `src/crawllmer/celery_app.py` — update imports
- Modify: `tests/integration/test_pipeline_flow.py` — update imports

Steps:
- [ ] Create `core/observability/pipeline_telemetry.py` — copy contents of `application/observability.py` verbatim
- [ ] Create `core/observability/telemetry_setup.py` — copy contents of `application/telemetry_setup.py` verbatim
- [ ] Create `core/observability/__init__.py` — re-export `log_event`, `PipelineTelemetry`, `setup_telemetry`
- [ ] Update imports in `orchestrator.py`: `from crawllmer.core.observability import PipelineTelemetry, log_event`
- [ ] Update imports in `web/app.py`: `from crawllmer.core.observability import log_event, setup_telemetry`
- [ ] Update imports in `celery_app.py`: `from crawllmer.core.observability import setup_telemetry`
- [ ] Update imports in `tests/integration/test_pipeline_flow.py`: `from crawllmer.core.observability import PipelineTelemetry`
- [ ] Delete `application/observability.py` and `application/telemetry_setup.py`
- [ ] Run `make check` — all tests pass with new import paths
- [ ] Commit: `refactor(core): move observability modules into core/ package`

---

### Task 3: Add `log_level` config setting

**Files:**
- Modify: `src/crawllmer/config.py` — add `log_level` field
- Modify: `src/crawllmer/core/observability/telemetry_setup.py` — wire log level
- Modify: `.env.example` — add `CRAWLLMER_LOG_LEVEL`
- Create: `tests/unit/test_config_log_level.py`

Steps:
- [ ] Write test: create `Settings` with `CRAWLLMER_LOG_LEVEL=WARNING`, assert `settings.log_level == "WARNING"`
- [ ] Write test: create `Settings` with invalid log level, assert Pydantic `ValidationError`
- [ ] Run tests — confirm they fail
- [ ] Add `log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG"` to `Settings` in `config.py` (add `from typing import Literal` import)
- [ ] Run tests — confirm they pass
- [ ] Update `telemetry_setup.py`: import `get_settings`, set `logging.getLogger("crawllmer").setLevel(getattr(logging, get_settings().log_level))` after adding the handler
- [ ] Add `CRAWLLMER_LOG_LEVEL=DEBUG` entry to `.env.example` with comment
- [ ] Run `make check`
- [ ] Commit: `feat(config): add configurable log_level setting`

---

### Task 4: Create `core/observability/events.py` — event classes and BusinessMetrics

**Files:**
- Create: `src/crawllmer/core/observability/events.py`
- Modify: `src/crawllmer/core/observability/__init__.py` — add re-exports
- Create: `tests/unit/test_events.py`

Steps:
- [ ] Write tests for `EventMetadata` subclasses: each concrete event stores fields, `to_attributes()` returns correct dict with correct types
- [ ] Write test for `BusinessMetrics`: mock OTEL meter, call `record_run_completed(event)`, verify counter/histogram `.add()`/`.record()` called with correct values
- [ ] Run tests — confirm they fail
- [ ] Implement `EventMetadata` ABC as `@dataclass(slots=True)` with `run_id`, `event_name`, `timestamp` fields
- [ ] Implement `DiscoveryCompletedEvent`, `ExtractionCompletedEvent`, `GenerationCompletedEvent`, `RunCompletedEvent` as `@dataclass(slots=True)` subclasses
- [ ] Implement `BusinessMetrics` class with `crawllmer.business` meter and `record_run_completed()` method
- [ ] Update `core/observability/__init__.py` to re-export all new names
- [ ] Run tests — confirm they pass
- [ ] Run `make check`
- [ ] Commit: `feat(core): add structured event metadata and business metrics`

---

### Task 5: Wire errors into orchestrator and web layer

**Files:**
- Modify: `src/crawllmer/application/orchestrator.py`
- Modify: `src/crawllmer/web/app.py`
- Modify: `src/crawllmer/web/streamlit_app.py` (line ~581)
- Modify: `src/crawllmer/celery_app.py`
- Modify: `tests/unit/test_orchestrator.py`
- Modify: `tests/integration/test_pipeline_flow.py`

Steps:
- [ ] Update `test_orchestrator.py`: `test_pipeline_rejects_unknown_run` catches `RunNotFoundError` instead of `ValueError`, import from `crawllmer.core`
- [ ] Update `test_pipeline_flow.py`: `test_pipeline_failure_path_marks_failed_stage_and_run` catches `PipelineProcessingError`, asserts `exc.stage == "discovery"` and `isinstance(exc.__cause__, RuntimeError)`
- [ ] Run tests — confirm they fail (orchestrator still raises old exceptions)
- [ ] Update `orchestrator.py`:
  - Import `InvalidInputError`, `RunNotFoundError`, `PipelineProcessingError` from `crawllmer.core`
  - `enqueue_run()`: replace `raise ValueError("invalid URL")` with `raise InvalidInputError("url", "invalid URL")`
  - `process_run()`: replace `raise ValueError("run not found")` with `raise RunNotFoundError(run_id)`
  - `_run_stage()`: in the except block, after telemetry/logging, `raise PipelineProcessingError(stage=stage.value, run_id=run.id, cause=exc) from exc`
  - `process_run()`: change `except Exception` to `except PipelineProcessingError`
- [ ] Run tests — confirm they pass
- [ ] Update `web/app.py`:
  - Import `InvalidInputError`, `RunNotFoundError`, `PipelineProcessingError` from `crawllmer.core`
  - `crawl_api()`: catch `InvalidInputError` → 422
  - `process_run()`: remove manual `repo.get_run()` pre-check (redundant), catch `RunNotFoundError` → 404, catch `PipelineProcessingError` → 500, remove duplicate failure-marking logic
- [ ] Update `web/streamlit_app.py` line ~581: `except InvalidInputError as exc:` instead of `except ValueError as exc:`
- [ ] Update `celery_app.py`: add `try/except PipelineProcessingError` around `pipeline.process_run()` that logs structured error and re-raises
- [ ] Run `make check`
- [ ] Commit: `refactor: replace generic exceptions with typed error hierarchy`

---

### Task 6: Wire events and BusinessMetrics into orchestrator

**Files:**
- Modify: `src/crawllmer/application/orchestrator.py`
- Modify: `tests/integration/test_pipeline_flow.py` — verify business metrics emitted

Steps:
- [ ] Add test to `test_pipeline_flow.py`: after happy-path run, assert `crawllmer_pages_indexed_total`, `crawllmer_run_duration_seconds`, `crawllmer_llmstxt_size_bytes` appear in metric reader output
- [ ] Run test — confirm it fails (metrics not emitted yet)
- [ ] Update `CrawlPipeline.__init__` to accept optional `business_metrics: BusinessMetrics | None = None` parameter, default to `BusinessMetrics()`
- [ ] In `_build_stage_plan`:
  - After `run_discovery`: emit `DiscoveryCompletedEvent` via `log_event` with `event.to_attributes()`
  - After `run_extraction`: emit `ExtractionCompletedEvent`
  - After `run_generation`: emit `GenerationCompletedEvent`
- [ ] In `process_run`, after successful completion: create `RunCompletedEvent` with `total_pages_indexed`, `duration_seconds`, `llmstxt_size_bytes`, call `self.business_metrics.record_run_completed(event)`, and `log_event` with `event.to_attributes()`
- [ ] Run tests — confirm they pass
- [ ] Run `make check`
- [ ] Commit: `feat: emit structured events and business metrics from pipeline`

---

### Task 7: Update documentation

**Files:**
- Modify: `docs/design_decisions.md`
- Modify: `CLAUDE.md`

Steps:
- [ ] Add "Error Handling" section to `docs/design_decisions.md`: typed exceptions over generic catches, hierarchy rationale, `PipelineProcessingError` causal chain, `retry.py` exemption
- [ ] Add "Observability Events" section to `docs/design_decisions.md`: stage-level vs business-level metrics separation, single-emission-point principle, `EventMetadata` abstraction
- [ ] Update `CLAUDE.md` environment variable table: add `CRAWLLMER_LOG_LEVEL` row
- [ ] Update `CLAUDE.md` Architecture section: add `core/` to the directory tree
- [ ] Commit: `docs: add error handling and observability event design decisions`

---

## Approval State

| Status | Date | Notes |
|--------|------|-------|
| Draft | 2026-03-19 | Initial draft |
| Approved | 2026-03-19 | Approved after two spec review passes |
