from __future__ import annotations

from celery import Celery

from crawllmer.domain.ports import QueuePublisher


def build_celery_app(
    broker_url: str,
    result_backend: str,
    app_name: str = "crawllmer",
) -> Celery:
    """Construct a configured Celery application instance."""
    app = Celery(app_name, broker=broker_url, backend=result_backend)
    app.conf.task_routes = {"crawllmer.discovery": {"queue": "discovery"}}
    return app


class CeleryQueuePublisher(QueuePublisher):
    """Publisher that dispatches queue messages via Celery send_task."""

    def __init__(
        self,
        broker_url: str,
        result_backend: str,
        task_name_prefix: str = "crawllmer",
    ) -> None:
        self.task_name_prefix = task_name_prefix
        self.app = build_celery_app(
            broker_url=broker_url, result_backend=result_backend
        )

    def publish(self, queue_name: str, payload: dict) -> None:
        task_name = f"{self.task_name_prefix}.{queue_name}"
        self.app.send_task(task_name, kwargs=payload, queue=queue_name)
