from __future__ import annotations

import os
from time import sleep

from crawllmer.adapters.storage import default_repository
from crawllmer.application.orchestrator import CrawlPipeline
from crawllmer.application.queueing import CeleryQueuePublisher


def run_loop() -> None:
    db_url = os.getenv("CRAWLLMER_DB_URL", "sqlite:///./crawllmer.db")
    broker = os.getenv(
        "CRAWLLMER_CELERY_BROKER_URL", "sqla+sqlite:///./celery-broker.db"
    )
    result_backend = os.getenv(
        "CRAWLLMER_CELERY_RESULT_BACKEND", "db+sqlite:///./celery-results.db"
    )
    repository = default_repository(db_url)
    queue = CeleryQueuePublisher(broker_url=broker, result_backend=result_backend)

    pipeline = CrawlPipeline(repository=repository, queue=queue)
    poll_seconds = float(os.getenv("CRAWLLMER_WORKER_POLL_SECONDS", "2"))

    while True:
        pending_runs = [
            run
            for run in repository.list_runs(limit=100)
            if run.status.value == "queued"
        ]
        for run in pending_runs:
            pipeline.process_run(run.id)
        sleep(poll_seconds)


def main() -> None:
    run_loop()


if __name__ == "__main__":
    main()
