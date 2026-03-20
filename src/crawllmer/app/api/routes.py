from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, HttpUrl

from crawllmer.adapters.storage import get_storage
from crawllmer.app.indexer.queueing import CeleryQueuePublisher
from crawllmer.core import InvalidInputError, PipelineProcessingError, RunNotFoundError
from crawllmer.core.config import get_settings
from crawllmer.core.observability import log_event, setup_telemetry
from crawllmer.core.orchestrator import CrawlPipeline

_settings = get_settings()
repo = get_storage()
queue = CeleryQueuePublisher(
    broker_url=_settings.celery_broker_url,
    result_backend=_settings.celery_result_backend,
)
pipeline = CrawlPipeline(repository=repo, queue=queue)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_telemetry("crawllmer-api")
    yield


app = FastAPI(title="crawllmer", lifespan=lifespan)


class CrawlRequest(BaseModel):
    url: HttpUrl


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/crawls")
def crawl_api(payload: CrawlRequest):
    try:
        run = pipeline.enqueue_run(str(payload.url))
    except InvalidInputError as exc:
        log_event("api.crawl.enqueue.failed", url=str(payload.url), error=str(exc))
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    log_event("api.crawl.enqueued", run_id=run.id, status=run.status.value)
    return {
        "run_id": str(run.id),
        "status": run.status,
    }


@app.post("/api/v1/crawls/{run_id}/process")
def process_run(run_id: UUID):
    try:
        run = pipeline.process_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PipelineProcessingError as exc:
        log_event("api.crawl.process.failed", run_id=run_id, error=str(exc))
        raise HTTPException(status_code=500, detail="processing failed") from exc

    log_event("api.crawl.process.completed", run_id=run.id, score=run.score)
    return {
        "run_id": str(run.id),
        "status": run.status,
        "score": run.score,
        "score_breakdown": run.score_breakdown,
    }


@app.get("/api/v1/crawls/{run_id}")
def crawl_status(run_id: UUID):
    run = repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {
        "run_id": str(run.id),
        "host": run.hostname,
        "status": run.status,
        "score": run.score,
        "score_breakdown": run.score_breakdown,
        "created_at": run.created_at.isoformat(),
    }


@app.get("/api/v1/crawls/{run_id}/llms.txt", response_class=PlainTextResponse)
def crawl_llms_txt(run_id: UUID):
    artifact = repo.get_artifact(run_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="llms.txt not found")
    return artifact.llms_txt


@app.get("/api/v1/crawls/{run_id}/work-items")
def crawl_work_items(run_id: UUID):
    run = repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    items = repo.list_work_items(run_id)
    return [
        {
            "id": str(item.id),
            "run_id": str(item.run_id),
            "stage": item.stage.value,
            "state": item.state.value,
            "url": item.url,
            "attempt_count": item.attempt_count,
            "last_error": item.last_error,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }
        for item in items
    ]


@app.get("/api/v1/crawls/{run_id}/events")
def crawl_events(run_id: UUID):
    run = repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    events = repo.list_events(run_id)
    return [
        {
            "id": str(event.id),
            "run_id": str(event.run_id),
            "name": event.name,
            "system": event.system,
            "started_at": event.started_at.isoformat(),
            "completed_at": (
                event.completed_at.isoformat() if event.completed_at else None
            ),
            "duration": event.duration,
            "metadata": event.metadata,
        }
        for event in events
    ]


@app.get("/api/v1/history")
def history(host: str | None = None, limit: int = 50):
    runs = repo.list_runs(hostname=host, limit=limit)
    return [
        {
            "run_id": str(run.id),
            "host": run.hostname,
            "status": run.status,
            "score": run.score,
        }
        for run in runs
    ]
