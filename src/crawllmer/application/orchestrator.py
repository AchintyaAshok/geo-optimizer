from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from urllib.parse import urlparse
from uuid import UUID

from opentelemetry import trace

from crawllmer.application.retry import RetryPolicy
from crawllmer.application.scheduler import HostRateLimiter
from crawllmer.application.workers import (
    canonicalize_and_dedup,
    discover_urls,
    extract_metadata,
    generate_llms_txt,
    score_pages,
)
from crawllmer.core import InvalidInputError, PipelineProcessingError, RunNotFoundError
from crawllmer.core.observability import (
    BusinessMetrics,
    DiscoveryCompletedEvent,
    ExtractionCompletedEvent,
    GenerationCompletedEvent,
    PipelineTelemetry,
    RunCompletedEvent,
    log_event,
)
from crawllmer.domain.models import (
    CrawlEvent,
    CrawlRun,
    GenerationArtifact,
    RunStatus,
    WorkItem,
    WorkItemState,
    WorkStage,
)
from crawllmer.domain.ports import CrawlRepository, QueuePublisher


@dataclass(slots=True)
class StageExecution:
    """A configured stage callable that mutates run/repository state."""

    stage: WorkStage
    execute: Callable[[CrawlRun], None]


class CrawlPipeline:
    """Coordinates crawl run lifecycle and stage execution.

    The pipeline builds a sequence of stage executions from run context and
    executes them in order while applying retries, telemetry and state updates.
    """

    def __init__(
        self,
        repository: CrawlRepository,
        queue: QueuePublisher,
        retry_policy: RetryPolicy | None = None,
        rate_limiter: HostRateLimiter | None = None,
        telemetry: PipelineTelemetry | None = None,
        business_metrics: BusinessMetrics | None = None,
    ) -> None:
        self.repository = repository
        self.queue = queue
        self.retry = retry_policy or RetryPolicy()
        self.rate_limiter = rate_limiter or HostRateLimiter()
        self.telemetry = telemetry or PipelineTelemetry()
        self.business_metrics = business_metrics or BusinessMetrics()

    def enqueue_run(self, url: str) -> CrawlRun:
        """Validate input URL, persist queued run/work-item, and publish task."""
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise InvalidInputError("url", "invalid URL")

        run = CrawlRun(target_url=url, hostname=parsed.netloc, status=RunStatus.queued)
        self.repository.create_run(run)
        work_item = WorkItem(
            run_id=run.id,
            stage=WorkStage.discovery,
            state=WorkItemState.queued,
            url=url,
        )
        self.repository.create_work_item(work_item)
        self.telemetry.track_state_transition(None, WorkItemState.queued.value)
        self.queue.publish(
            "discovery", {"run_id": str(run.id), "work_item_id": str(work_item.id)}
        )
        log_event("pipeline.enqueue", run_id=run.id, url=url, state=run.status.value)
        return run

    def process_run(self, run_id: UUID) -> CrawlRun:
        """Load a run and execute the registered stage plan for that run."""
        run = self.repository.get_run(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        run_event = CrawlEvent(
            run_id=run.id,
            name="pipeline.run",
            system="pipeline",
            metadata={"target_url": run.target_url},
        )
        with self.telemetry.run_span(str(run.id), run.target_url):
            run.status = RunStatus.running
            self.repository.update_run(run)
            log_event("pipeline.run.start", run_id=run.id, target_url=run.target_url)
            run_start = perf_counter()
            try:
                self.rate_limiter.wait(run.hostname)
                for stage_execution in self._build_stage_plan(run):
                    self._run_stage(run, stage_execution)
                run.completed_at = datetime.now(UTC)
                run.status = RunStatus.completed
                self.repository.update_run(run)
                self.telemetry.record_run_outcome("success")

                # Emit business-level event and metrics
                pages = self.repository.get_extracted_pages(run.id)
                artifact = self.repository.get_artifact(run.id)
                llmstxt_size = len(artifact.llms_txt.encode()) if artifact else 0
                run_completed = RunCompletedEvent(
                    run_id=run.id,
                    total_pages_indexed=len(pages),
                    duration_seconds=perf_counter() - run_start,
                    llmstxt_size_bytes=llmstxt_size,
                )
                self.business_metrics.record_run_completed(run_completed)
                log_event(
                    "pipeline.run.completed",
                    run_id=run.id,
                    score=run.score,
                    **run_completed.to_attributes(),
                )

                run_event.completed_at = datetime.now(UTC)
                run_event.metadata["outcome"] = "success"
                run_event.metadata["score"] = run.score
                self.repository.create_event(run_event)
                return run
            except PipelineProcessingError as exc:
                run.status = RunStatus.failed
                run.notes["processing_error"] = str(exc)
                run.completed_at = datetime.now(UTC)
                self.repository.update_run(run)
                self.telemetry.record_run_outcome("failure")
                log_event("pipeline.run.failed", run_id=run.id, error=str(exc))
                run_event.completed_at = datetime.now(UTC)
                run_event.metadata["outcome"] = "failure"
                run_event.metadata["error"] = str(exc)
                self.repository.create_event(run_event)
                raise

    def _build_stage_plan(self, run: CrawlRun) -> list[StageExecution]:
        """Create ordered stage plan from current run context."""

        def run_discovery(current_run: CrawlRun) -> None:
            discovered = self.retry.run(lambda: discover_urls(current_run.target_url))
            self.repository.add_discovered_urls(current_run.id, discovered)
            strategies = list({source for _, source in discovered})
            event = DiscoveryCompletedEvent(
                run_id=current_run.id,
                pages_discovered=len(discovered),
                strategies_used=strategies,
            )
            log_event(event.event_name, **event.to_attributes())
            span = trace.get_current_span()
            span.add_event("pages.discovered", event.to_attributes())

        def run_extraction(current_run: CrawlRun) -> None:
            def on_page_event(name: str, data: dict) -> None:
                span = trace.get_current_span()
                span.add_event(name, {"url": data.get("url", "")})
                self.repository.create_event(
                    CrawlEvent(
                        run_id=current_run.id,
                        name=name,
                        system="extraction",
                        started_at=data.get("started_at", datetime.now(UTC)),
                        completed_at=data.get("completed_at"),
                        metadata={
                            k: v
                            for k, v in data.items()
                            if k not in ("started_at", "completed_at")
                        },
                    )
                )

            validators = {
                url: self.repository.get_validator(url)
                for url, _ in self.repository.get_discovered_urls(current_run.id)
            }
            pages, new_validators = self.retry.run(
                lambda: extract_metadata(
                    current_run.id,
                    self.repository.get_discovered_urls(current_run.id),
                    validators,
                    on_page_event=on_page_event,
                )
            )
            self.repository.upsert_extracted_pages(pages)
            for url, (etag, last_modified) in new_validators.items():
                self.repository.set_validator(url, etag, last_modified)
            urls_attempted = self.repository.get_discovered_urls(current_run.id)
            event = ExtractionCompletedEvent(
                run_id=current_run.id,
                pages_extracted=len(pages),
                pages_skipped=len(urls_attempted) - len(pages),
            )
            log_event(event.event_name, **event.to_attributes())
            span = trace.get_current_span()
            span.add_event("metadata.extracted", event.to_attributes())

        def run_canonicalization(current_run: CrawlRun) -> None:
            canonical_pages = canonicalize_and_dedup(
                self.repository.get_extracted_pages(current_run.id)
            )
            self.repository.upsert_extracted_pages(canonical_pages)

        def run_scoring(current_run: CrawlRun) -> None:
            pages = self.repository.get_extracted_pages(current_run.id)
            score = score_pages(pages)
            current_run.score = score["total"]
            current_run.score_breakdown = score
            self.repository.update_run(current_run)

        def run_generation(current_run: CrawlRun) -> None:
            pages = self.repository.get_extracted_pages(current_run.id)
            discovered = self.repository.get_discovered_urls(current_run.id)

            # Use homepage metadata for site title and description
            root = f"https://{current_run.hostname}"
            home = next(
                (p for p in pages if p.url.rstrip("/") == root.rstrip("/")),
                None,
            )

            llms_txt = generate_llms_txt(
                current_run.hostname,
                pages,
                site_title=home.title if home else None,
                site_description=home.description if home else None,
                links_discovered=len(discovered),
            )
            self.repository.save_artifact(
                GenerationArtifact(run_id=current_run.id, llms_txt=llms_txt)
            )
            current_run.artifact_path = f"artifact:{current_run.id}"
            self.repository.update_run(current_run)
            gen_event = GenerationCompletedEvent(
                run_id=current_run.id,
                llmstxt_size_bytes=len(llms_txt.encode()),
                entry_count=len(pages),
            )
            log_event(gen_event.event_name, **gen_event.to_attributes())
            span = trace.get_current_span()
            span.add_event("llms_txt.generated", gen_event.to_attributes())

        return [
            StageExecution(WorkStage.discovery, run_discovery),
            StageExecution(WorkStage.extraction, run_extraction),
            StageExecution(WorkStage.canonicalization, run_canonicalization),
            StageExecution(WorkStage.scoring, run_scoring),
            StageExecution(WorkStage.generation, run_generation),
        ]

    def _run_stage(self, run: CrawlRun, stage_execution: StageExecution) -> None:
        """Execute a single stage with work-item + telemetry transition handling."""
        item = self._new_item(run.id, stage_execution.stage, run.target_url)
        stage = stage_execution.stage
        event = CrawlEvent(
            run_id=run.id,
            name=f"stage.{stage.value}",
            system=stage.value,
        )
        with self.telemetry.stage_span(str(run.id), stage.value) as span:
            log_event("pipeline.stage.start", run_id=run.id, stage=stage.value)
            try:
                stage_execution.execute(run)
                self._complete_item(item)
                self.telemetry.record_stage_outcome(stage.value, "success")
                span.set_attribute("stage.outcome", "success")
                log_event("pipeline.stage.completed", run_id=run.id, stage=stage.value)
                event.completed_at = datetime.now(UTC)
                event.metadata["outcome"] = "success"
            except Exception as exc:  # noqa: BLE001
                self._fail_item(item, str(exc))
                self.telemetry.record_stage_outcome(stage.value, "failure")
                self.telemetry.mark_error(span, exc)
                log_event(
                    "pipeline.stage.failed",
                    run_id=run.id,
                    stage=stage.value,
                    error=str(exc),
                )
                event.completed_at = datetime.now(UTC)
                event.metadata["outcome"] = "failure"
                event.metadata["error"] = str(exc)
                raise PipelineProcessingError(
                    stage=stage.value, run_id=run.id, cause=exc
                ) from exc
            finally:
                self.repository.create_event(event)

    def _new_item(self, run_id: UUID, stage: WorkStage, url: str) -> WorkItem:
        """Create and transition a work item into processing state."""
        item = WorkItem(run_id=run_id, stage=stage, url=url)
        self.repository.create_work_item(item)
        self.telemetry.track_state_transition(None, WorkItemState.queued.value)
        previous = item.state.value
        item.transition(WorkItemState.processing)
        item.attempt_count += 1
        self.repository.update_work_item(item)
        self.telemetry.track_state_transition(previous, WorkItemState.processing.value)
        span = trace.get_current_span()
        span.add_event(
            "work_item.state_transition",
            {"from_state": previous, "to_state": "processing", "stage": stage.value},
        )
        return item

    def _complete_item(self, item: WorkItem) -> None:
        """Transition work item to completed."""
        previous = item.state.value
        item.transition(WorkItemState.completed)
        self.repository.update_work_item(item)
        self.telemetry.track_state_transition(previous, WorkItemState.completed.value)

    def _fail_item(self, item: WorkItem, error: str) -> None:
        """Transition work item to failed and attach failure reason."""
        previous = item.state.value
        item.last_error = error
        item.transition(WorkItemState.failed)
        self.repository.update_work_item(item)
        self.telemetry.track_state_transition(previous, WorkItemState.failed.value)
