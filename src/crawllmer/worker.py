from __future__ import annotations

from crawllmer.celery_app import celery_app


def main() -> None:
    """Run a Celery worker bound to the crawl discovery queue."""
    celery_app.worker_main(
        [
            "worker",
            "--loglevel=INFO",
            "--queues=discovery",
            "--pool=solo",
        ]
    )


if __name__ == "__main__":
    main()
