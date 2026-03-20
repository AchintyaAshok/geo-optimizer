from __future__ import annotations

from celery import Celery

from crawllmer.domain.ports import QueuePublisher


def build_celery_app(
    broker_url: str,
    result_backend: str,
    app_name: str = "crawllmer",
) -> Celery:
    """Construct a configured Celery application instance."""
    from crawllmer.core.config import get_settings

    settings = get_settings()
    app = Celery(app_name, broker=broker_url, backend=result_backend)
    app.conf.task_routes = {"crawllmer.discovery": {"queue": "discovery"}}

    # -- Reliability settings --
    # acks_late: acknowledge tasks AFTER completion, not before. If a worker
    # crashes mid-task, the message stays in the broker and gets redelivered
    # to another worker. Safe because our pipeline stages are idempotent
    # (upserts, not inserts).
    app.conf.task_acks_late = settings.celery_task_acks_late

    # reject_on_worker_lost: if the worker process is killed (OOM, SIGKILL),
    # reject the task back to the queue instead of silently acking it.
    app.conf.task_reject_on_worker_lost = settings.celery_task_reject_on_worker_lost

    # visibility_timeout (Redis only): if a task isn't acknowledged within
    # this window, Redis automatically redelivers it. Must be longer than
    # the longest expected crawl. Default 3600s (1 hour).
    #
    # NOTE: These settings protect against WORKER failures (crash, OOM,
    # restart). They do NOT protect against BROKER failures (Redis restart,
    # data loss). If the broker loses messages, runs stuck in queued/running
    # in the database become orphans. Recovering those requires a separate
    # stale-run-recovery mechanism (database scan + re-enqueue).
    if broker_url.startswith("redis"):
        app.conf.broker_transport_options = {
            "visibility_timeout": settings.celery_broker_visibility_timeout,
        }
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
