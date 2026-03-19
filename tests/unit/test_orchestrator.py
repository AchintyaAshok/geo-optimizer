from __future__ import annotations

from uuid import UUID

from crawllmer.adapters.storage import SqliteStorageRepository
from crawllmer.core import RunNotFoundError
from crawllmer.core.orchestrator import CrawlPipeline
from crawllmer.domain.ports import QueuePublisher


class StubQueuePublisher(QueuePublisher):
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict]] = []

    def publish(self, queue_name: str, payload: dict) -> None:
        self.messages.append((queue_name, payload))


class FakeResponse:
    def __init__(
        self, status_code: int, text: str = "", headers: dict | None = None
    ) -> None:
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


def _fake_http_client() -> type:
    pages = {
        "https://example.com/llms.txt": FakeResponse(
            200,
            "- [Home](https://example.com/)\n- [About](https://example.com/about)",
        ),
        "https://example.com/robots.txt": FakeResponse(
            200,
            "User-agent: *\nSitemap: https://example.com/sitemap.xml",
        ),
        "https://example.com/sitemap.xml": FakeResponse(
            200,
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            "<url><loc>https://example.com/</loc></url>\n"
            "<url><loc>https://example.com/about/</loc></url>\n"
            "</urlset>",
        ),
        "https://example.com/": FakeResponse(
            200,
            (
                "<html><head><title>Home</title>"
                '<meta name="description" content="Welcome" /></head></html>'
            ),
            {"etag": '"abc"', "last-modified": "Mon, 10 Feb 2025 09:00:00 GMT"},
        ),
        "https://example.com/about": FakeResponse(
            200,
            (
                '<html><head><meta property="og:title" content="About" />'
                '<meta property="og:description" content="About us" /></head></html>'
            ),
            {"etag": '"def"', "last-modified": "Mon, 10 Feb 2025 09:00:00 GMT"},
        ),
    }

    class FakeHttpClient:
        def __init__(self, timeout: float = 8.0) -> None:  # noqa: ARG002
            pass

        def get(self, url: str, headers: dict | None = None):
            headers = headers or {}
            response = pages.get(url)
            if response is None:
                return FakeResponse(404)
            if headers.get("If-None-Match") == response.headers.get("etag"):
                return FakeResponse(304)
            return response

    return FakeHttpClient


def test_pipeline_completes_and_generates_deterministic_artifact(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "crawllmer.app.indexer.workers.httpx.Client", _fake_http_client()
    )
    repo = SqliteStorageRepository(db_url=f"sqlite:///{tmp_path}/test.db")
    pipeline = CrawlPipeline(repository=repo, queue=StubQueuePublisher())

    run = pipeline.enqueue_run("https://example.com")
    processed = pipeline.process_run(run.id)

    assert processed.score is not None
    artifact = repo.get_artifact(processed.id)
    assert artifact is not None
    assert "example.com" in artifact.llms_txt
    assert "## Home" in artifact.llms_txt

    second = pipeline.enqueue_run("https://example.com")
    processed_second = pipeline.process_run(second.id)
    assert processed_second.status.value == "completed"


def test_pipeline_rejects_unknown_run(tmp_path) -> None:
    repo = SqliteStorageRepository(db_url=f"sqlite:///{tmp_path}/test.db")
    pipeline = CrawlPipeline(repository=repo, queue=StubQueuePublisher())
    unknown = UUID("00000000-0000-0000-0000-000000000000")
    try:
        pipeline.process_run(unknown)
    except RunNotFoundError as exc:
        assert exc.run_id == unknown
        assert "run not found" in str(exc)
    else:
        raise AssertionError("expected RunNotFoundError")
