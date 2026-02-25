from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, HttpUrl

from crawllmer.application.observability import log_event
from crawllmer.domain.models import RunStatus
from crawllmer.web.runtime import pipeline, repo

app = FastAPI(title="crawllmer")


class CrawlRequest(BaseModel):
    url: HttpUrl


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/crawls")
def crawl_api(payload: CrawlRequest):
    try:
        run = pipeline.enqueue_run(str(payload.url))
    except ValueError as exc:
        log_event("api.crawl.enqueue.failed", url=str(payload.url), error=str(exc))
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    log_event("api.crawl.enqueued", run_id=run.id, status=run.status.value)
    return {
        "run_id": str(run.id),
        "status": run.status,
    }


@app.post("/api/v1/crawls/{run_id}/process")
def process_run(run_id: UUID):
    run = repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    try:
        run = pipeline.process_run(run_id)
    except Exception as exc:  # noqa: BLE001
        run.status = RunStatus.failed
        run.notes["processing_error"] = str(exc)
        repo.update_run(run)
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
        "status": run.status,
        "score": run.score,
        "score_breakdown": run.score_breakdown,
    }


@app.get("/api/v1/crawls/{run_id}/llms.txt", response_class=PlainTextResponse)
def crawl_llms_txt(run_id: UUID):
    artifact = repo.get_artifact(run_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="llms.txt not found")
    return artifact.llms_txt


@app.get("/api/v1/history")
def history(host: str | None = None):
    runs = repo.list_runs(hostname=host, limit=50)
    return [
        {
            "run_id": str(run.id),
            "host": run.hostname,
            "status": run.status,
            "score": run.score,
        }
        for run in runs
    ]
