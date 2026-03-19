from __future__ import annotations

import logging
from uuid import UUID

from celery.signals import worker_init

from crawllmer.adapters.storage import default_repository
from crawllmer.app.indexer.queueing import CeleryQueuePublisher, build_celery_app
from crawllmer.core import PipelineProcessingError
from crawllmer.core.config import get_settings
from crawllmer.core.observability import setup_telemetry
from crawllmer.core.orchestrator import CrawlPipeline

logger = logging.getLogger("crawllmer.celery")

_settings = get_settings()

celery_app = build_celery_app(
    _settings.celery_broker_url, _settings.celery_result_backend
)


@worker_init.connect
def init_telemetry(**kwargs):  # noqa: ARG001
    """Bootstrap OTEL SDK when the Celery worker process starts."""
    setup_telemetry("crawllmer-worker")


@celery_app.task(name="crawllmer.discovery")
def process_run_task(run_id: str, work_item_id: str | None = None) -> dict:  # noqa: ARG001
    """Celery entrypoint for processing an enqueued crawl run."""
    repository = default_repository(db_url=_settings.db_url)
    queue = CeleryQueuePublisher(
        broker_url=_settings.celery_broker_url,
        result_backend=_settings.celery_result_backend,
    )
    pipeline = CrawlPipeline(repository=repository, queue=queue)
    try:
        run = pipeline.process_run(UUID(run_id))
    except PipelineProcessingError as exc:
        logger.error(
            "pipeline failed: stage=%s run_id=%s cause=%s",
            exc.stage,
            exc.run_id,
            exc.__cause__,
        )
        raise
    return {"run_id": str(run.id), "status": run.status.value}
