from __future__ import annotations

from crawllmer.adapters.storage import default_repository
from crawllmer.application.orchestrator import CrawlPipeline
from crawllmer.application.queueing import CeleryQueuePublisher
from crawllmer.config import get_settings

_settings = get_settings()

repo = default_repository(db_url=_settings.db_url)
queue = CeleryQueuePublisher(
    broker_url=_settings.celery_broker_url,
    result_backend=_settings.celery_result_backend,
)
pipeline = CrawlPipeline(repository=repo, queue=queue)
