from __future__ import annotations

from crawllmer.app.indexer.app import celery_app
from crawllmer.core.config import get_settings


def main() -> None:
    """Run a Celery worker bound to the crawl discovery queue."""
    settings = get_settings()
    celery_app.worker_main(
        [
            "worker",
            "--loglevel=INFO",
            "--queues=discovery",
            f"--pool={settings.celery_worker_pool}",
            f"--concurrency={settings.celery_worker_concurrency}",
        ]
    )


if __name__ == "__main__":
    main()
