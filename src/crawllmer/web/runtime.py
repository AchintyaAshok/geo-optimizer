from __future__ import annotations

import os

from crawllmer.adapters.storage import default_repository
from crawllmer.application.orchestrator import CrawlPipeline
from crawllmer.application.queueing import CeleryQueuePublisher

DB_URL = os.getenv("CRAWLLMER_DB_URL", "sqlite:///./crawllmer.db")
CELERY_BROKER_URL = os.getenv(
    "CRAWLLMER_CELERY_BROKER_URL", "sqla+sqlite:///./celery-broker.db"
)
CELERY_RESULT_BACKEND = os.getenv(
    "CRAWLLMER_CELERY_RESULT_BACKEND", "db+sqlite:///./celery-results.db"
)

repo = default_repository(db_url=DB_URL)
queue = CeleryQueuePublisher(
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
)
pipeline = CrawlPipeline(repository=repo, queue=queue)
