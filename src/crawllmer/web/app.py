from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, HttpUrl

from crawllmer.web.runtime import LATEST, repo, run_crawl

app = FastAPI(title="crawllmer")


class CrawlRequest(BaseModel):
    url: HttpUrl


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/crawls")
def crawl_api(payload: CrawlRequest):
    run, result = run_crawl(str(payload.url))
    return {
        "run_id": str(run.id),
        "status": run.status,
        "strategy_attempts": run.strategy_attempts,
        "llms_txt": result.document.to_text() if result and result.document else None,
    }


@app.get("/api/v1/crawls/{run_id}")
def crawl_status(run_id: str):
    for run in repo.latest_runs(limit=200):
        if str(run.id) == run_id:
            return {
                "run_id": run_id,
                "status": run.status,
                "strategy_attempts": run.strategy_attempts,
                "diagnostics": run.diagnostics,
            }
    raise HTTPException(status_code=404, detail="run not found")


@app.get("/api/v1/crawls/{run_id}/llms.txt", response_class=PlainTextResponse)
def crawl_llms_txt(run_id: str):
    llms = LATEST.get(run_id)
    if not llms:
        raise HTTPException(status_code=404, detail="llms.txt not found")
    return llms


@app.get("/api/v1/history")
def history(host: str | None = None):
    runs = repo.latest_runs(hostname=host, limit=50)
    return [
        {
            "run_id": str(run.id),
            "host": run.target.hostname,
            "status": run.status,
            "strategy_attempts": run.strategy_attempts,
        }
        for run in runs
    ]
