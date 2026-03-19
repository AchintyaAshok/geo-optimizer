from __future__ import annotations

from fastapi.testclient import TestClient

from crawllmer.web.app import app


class FakeResponse:
    def __init__(
        self, status_code: int, text: str = "", headers: dict | None = None
    ) -> None:
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_enqueue_and_process_run(monkeypatch) -> None:
    class FakeHttpClient:
        def __init__(self, timeout: float = 8.0) -> None:  # noqa: ARG002
            pass

        def get(self, url: str, headers: dict | None = None):  # noqa: ARG002
            if url.endswith("/llms.txt"):
                return FakeResponse(200, "- [Home](https://api-example.com/)")
            if url.endswith("/robots.txt"):
                return FakeResponse(200, "User-agent: *")
            return FakeResponse(
                200,
                (
                    "<html><head><title>Home</title>"
                    '<meta name="description" content="Desc" /></head></html>'
                ),
                {"etag": '"123"'},
            )

    monkeypatch.setattr("crawllmer.application.workers.httpx.Client", FakeHttpClient)
    client = TestClient(app)

    enqueue = client.post("/api/v1/crawls", json={"url": "https://api-example.com"})
    assert enqueue.status_code == 200
    run_id = enqueue.json()["run_id"]

    process = client.post(f"/api/v1/crawls/{run_id}/process")
    assert process.status_code == 200
    assert process.json()["status"] == "completed"

    llms = client.get(f"/api/v1/crawls/{run_id}/llms.txt")
    assert llms.status_code == 200
    assert "# llms.txt for api-example.com" in llms.text


def test_crawl_events_are_persisted_and_retrievable(monkeypatch) -> None:
    class FakeHttpClient:
        def __init__(self, timeout: float = 8.0) -> None:  # noqa: ARG002
            pass

        def get(self, url: str, headers: dict | None = None):  # noqa: ARG002
            if url.endswith("/llms.txt"):
                return FakeResponse(200, "- [Home](https://events-example.com/)")
            if url.endswith("/robots.txt"):
                return FakeResponse(200, "User-agent: *")
            return FakeResponse(
                200,
                (
                    "<html><head><title>Home</title>"
                    '<meta name="description" content="Desc" /></head></html>'
                ),
            )

    monkeypatch.setattr("crawllmer.application.workers.httpx.Client", FakeHttpClient)
    client = TestClient(app)

    enqueue = client.post("/api/v1/crawls", json={"url": "https://events-example.com"})
    run_id = enqueue.json()["run_id"]
    client.post(f"/api/v1/crawls/{run_id}/process")

    response = client.get(f"/api/v1/crawls/{run_id}/events")
    assert response.status_code == 200
    events = response.json()
    # 1 run-level + 5 stage events + per-page extraction sub-events
    assert len(events) >= 7
    systems = [e["system"] for e in events]
    assert "discovery" in systems
    assert "extraction" in systems
    assert "pipeline" in systems
    # Verify per-page extraction sub-events exist
    names = [e["name"] for e in events]
    assert "extraction.page_extracted" in names
    # All events should have duration (completed)
    for event in events:
        assert event["duration"] is not None
        assert event["duration"] >= 0


def test_invalid_url_validation() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/crawls", json={"url": "notaurl"})
    assert response.status_code == 422
