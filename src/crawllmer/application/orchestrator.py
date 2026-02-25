from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID

from crawllmer.application.observability import PipelineTelemetry, log_event
from crawllmer.application.retry import RetryPolicy
from crawllmer.application.scheduler import HostRateLimiter
from crawllmer.application.workers import (
    canonicalize_and_dedup,
    discover_urls,
    extract_metadata,
    generate_llms_txt,
    score_pages,
)
from crawllmer.domain.models import (
    CrawlRun,
    GenerationArtifact,
    RunStatus,
    WorkItem,
    WorkItemState,
    WorkStage,
)
from crawllmer.domain.ports import CrawlRepository, QueuePublisher


class CrawlPipeline:
    def __init__(
        self,
        repository: CrawlRepository,
        queue: QueuePublisher,
        retry_policy: RetryPolicy | None = None,
        rate_limiter: HostRateLimiter | None = None,
        telemetry: PipelineTelemetry | None = None,
    ) -> None:
        self.repository = repository
        self.queue = queue
        self.retry = retry_policy or RetryPolicy()
        self.rate_limiter = rate_limiter or HostRateLimiter()
        self.telemetry = telemetry or PipelineTelemetry()

    def enqueue_run(self, url: str) -> CrawlRun:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("invalid URL")

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
        run = self.repository.get_run(run_id)
        if run is None:
            raise ValueError("run not found")

        with self.telemetry.run_span(str(run.id), run.target_url):
            run.status = RunStatus.running
            self.repository.update_run(run)
            log_event("pipeline.run.start", run_id=run.id, target_url=run.target_url)

            try:
                self.rate_limiter.wait(run.hostname)

                discovered = self._run_stage(
                    run=run,
                    stage=WorkStage.discovery,
                    fn=lambda: self.retry.run(lambda: discover_urls(run.target_url)),
                )
                self.repository.add_discovered_urls(run.id, discovered)

                validators = {
                    url: self.repository.get_validator(url)
                    for url, _ in self.repository.get_discovered_urls(run.id)
                }
                pages, new_validators = self._run_stage(
                    run=run,
                    stage=WorkStage.extraction,
                    fn=lambda: self.retry.run(
                        lambda: extract_metadata(
                            run.id,
                            self.repository.get_discovered_urls(run.id),
                            validators,
                        )
                    ),
                )
                self.repository.upsert_extracted_pages(pages)
                for url, (etag, last_modified) in new_validators.items():
                    self.repository.set_validator(url, etag, last_modified)

                canonical_pages = self._run_stage(
                    run=run,
                    stage=WorkStage.canonicalization,
                    fn=lambda: canonicalize_and_dedup(
                        self.repository.get_extracted_pages(run.id)
                    ),
                )
                self.repository.upsert_extracted_pages(canonical_pages)

                score = self._run_stage(
                    run=run,
                    stage=WorkStage.scoring,
                    fn=lambda: score_pages(canonical_pages),
                )
                run.score = score["total"]
                run.score_breakdown = score

                llms_txt = self._run_stage(
                    run=run,
                    stage=WorkStage.generation,
                    fn=lambda: generate_llms_txt(run.hostname, canonical_pages),
                )
                self.repository.save_artifact(
                    GenerationArtifact(run_id=run.id, llms_txt=llms_txt)
                )

                run.artifact_path = f"artifact:{run.id}"
                run.completed_at = datetime.now(UTC)
                run.status = RunStatus.completed
                self.repository.update_run(run)
                self.telemetry.record_run_outcome("success")
                log_event("pipeline.run.completed", run_id=run.id, score=run.score)
                return run
            except Exception as exc:  # noqa: BLE001
                run.status = RunStatus.failed
                run.notes["processing_error"] = str(exc)
                run.completed_at = datetime.now(UTC)
                self.repository.update_run(run)
                self.telemetry.record_run_outcome("failure")
                log_event("pipeline.run.failed", run_id=run.id, error=str(exc))
                raise

    def _run_stage(self, run: CrawlRun, stage: WorkStage, fn):
        item = self._new_item(run.id, stage, run.target_url)
        with self.telemetry.stage_span(str(run.id), stage.value) as span:
            log_event("pipeline.stage.start", run_id=run.id, stage=stage.value)
            try:
                result = fn()
                self._complete_item(item)
                self.telemetry.record_stage_outcome(stage.value, "success")
                span.set_attribute("stage.outcome", "success")
                log_event("pipeline.stage.completed", run_id=run.id, stage=stage.value)
                return result
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
                raise

    def _new_item(self, run_id: UUID, stage: WorkStage, url: str) -> WorkItem:
        item = WorkItem(run_id=run_id, stage=stage, url=url)
        self.repository.create_work_item(item)
        self.telemetry.track_state_transition(None, WorkItemState.queued.value)
        previous = item.state.value
        item.transition(WorkItemState.processing)
        item.attempt_count += 1
        self.repository.update_work_item(item)
        self.telemetry.track_state_transition(previous, WorkItemState.processing.value)
        return item

    def _complete_item(self, item: WorkItem) -> None:
        previous = item.state.value
        item.transition(WorkItemState.completed)
        self.repository.update_work_item(item)
        self.telemetry.track_state_transition(previous, WorkItemState.completed.value)

    def _fail_item(self, item: WorkItem, error: str) -> None:
        previous = item.state.value
        item.last_error = error
        item.transition(WorkItemState.failed)
        self.repository.update_work_item(item)
        self.telemetry.track_state_transition(previous, WorkItemState.failed.value)
