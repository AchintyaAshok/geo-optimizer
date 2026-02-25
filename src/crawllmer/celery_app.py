from __future__ import annotations

import os
from uuid import UUID

from crawllmer.adapters.storage import default_repository
from crawllmer.application.orchestrator import CrawlPipeline
from crawllmer.application.queueing import CeleryQueuePublisher, build_celery_app

BROKER = os.getenv("CRAWLLMER_CELERY_BROKER_URL", "sqla+sqlite:///./celery-broker.db")
RESULT_BACKEND = os.getenv(
    "CRAWLLMER_CELERY_RESULT_BACKEND", "db+sqlite:///./celery-results.db"
)
DB_URL = os.getenv("CRAWLLMER_DB_URL", "sqlite:///./crawllmer.db")

celery_app = build_celery_app(BROKER, RESULT_BACKEND)


@celery_app.task(name="crawllmer.discovery")
def process_run_task(run_id: str, work_item_id: str | None = None) -> dict:  # noqa: ARG001
    """Celery entrypoint for processing an enqueued crawl run."""
    repository = default_repository(db_url=DB_URL)
    queue = CeleryQueuePublisher(broker_url=BROKER, result_backend=RESULT_BACKEND)
    pipeline = CrawlPipeline(repository=repository, queue=queue)
    run = pipeline.process_run(UUID(run_id))
    return {"run_id": str(run.id), "status": run.status.value}
