from __future__ import annotations

from crawllmer.domain.ports import QueuePublisher


class CeleryQueuePublisher(QueuePublisher):
    """Celery publisher with configurable broker and SQL/Redis result backend."""

    def __init__(
        self,
        broker_url: str,
        result_backend: str,
        task_name_prefix: str = "crawllmer",
    ) -> None:
        self.broker_url = broker_url
        self.result_backend = result_backend
        self.task_name_prefix = task_name_prefix

    def publish(self, queue_name: str, payload: dict) -> None:
        try:
            from celery import Celery
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("celery not installed") from exc

        app = Celery(
            "crawllmer",
            broker=self.broker_url,
            backend=self.result_backend,
        )
        task_name = f"{self.task_name_prefix}.{queue_name}"
        app.send_task(task_name, kwargs=payload, queue=queue_name)
