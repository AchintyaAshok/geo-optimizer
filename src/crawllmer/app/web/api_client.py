"""HTTP client for the crawllmer REST API.

The Streamlit UI uses this to delegate all data operations to the API
instead of accessing the database or Celery broker directly.
"""

from __future__ import annotations

from typing import Any

import httpx


class CrawllmerApiClient:
    """Thin wrapper around the crawllmer REST API."""

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> Any:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.base_url}{path}")
            resp.raise_for_status()
            return resp.json()

    def _get_text(self, path: str) -> str | None:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.base_url}{path}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.text

    def _post(self, path: str, data: dict) -> Any:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}{path}",
                json=data,
            )
            resp.raise_for_status()
            return resp.json()

    def health(self) -> dict:
        return self._get("/health")

    def enqueue_crawl(self, url: str) -> dict:
        """POST /api/v1/crawls — returns {"run_id": ..., "status": ...}."""
        return self._post("/api/v1/crawls", {"url": url})

    def get_run(self, run_id: str) -> dict | None:
        """GET /api/v1/crawls/{run_id}."""
        try:
            return self._get(f"/api/v1/crawls/{run_id}")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

    def get_llms_txt(self, run_id: str) -> str | None:
        """GET /api/v1/crawls/{run_id}/llms.txt."""
        return self._get_text(f"/api/v1/crawls/{run_id}/llms.txt")

    def get_events(self, run_id: str) -> list[dict]:
        """GET /api/v1/crawls/{run_id}/events."""
        try:
            return self._get(f"/api/v1/crawls/{run_id}/events")
        except httpx.HTTPStatusError:
            return []

    def get_work_items(self, run_id: str) -> list[dict]:
        """GET /api/v1/crawls/{run_id}/work-items."""
        try:
            return self._get(f"/api/v1/crawls/{run_id}/work-items")
        except httpx.HTTPStatusError:
            return []

    def list_runs(self, limit: int = 50) -> list[dict]:
        """GET /api/v1/history."""
        return self._get(f"/api/v1/history?limit={limit}")
