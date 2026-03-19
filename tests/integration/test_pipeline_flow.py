from __future__ import annotations

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from crawllmer.adapters.storage import SqliteStorageRepository
from crawllmer.core import PipelineProcessingError
from crawllmer.core.observability import PipelineTelemetry
from crawllmer.core.orchestrator import CrawlPipeline
from crawllmer.domain.models import RunStatus, WorkItemState
from crawllmer.domain.ports import QueuePublisher


class StubQueuePublisher(QueuePublisher):
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict]] = []

    def publish(self, queue_name: str, payload: dict) -> None:
        self.messages.append((queue_name, payload))


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


def _success_http_client() -> type:
    pages = {
        "https://site.test/llms.txt": FakeResponse(
            200,
            "- [Home](https://site.test/)\n- [Docs](https://site.test/docs)",
        ),
        "https://site.test/robots.txt": FakeResponse(
            200,
            "User-agent: *\nSitemap: https://site.test/sitemap.xml",
        ),
        "https://site.test/sitemap.xml": FakeResponse(
            200,
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            "<url><loc>https://site.test/</loc></url>\n"
            "<url><loc>https://site.test/docs</loc></url>\n"
            "</urlset>",
        ),
        "https://site.test/": FakeResponse(
            200,
            (
                "<html><head><title>Home</title>"
                '<meta name="description" content="Welcome" /></head></html>'
            ),
            {"etag": '"a1"', "last-modified": "Mon, 10 Feb 2025 09:00:00 GMT"},
        ),
        "https://site.test/docs": FakeResponse(
            200,
            (
                '<html><head><meta property="og:title" content="Docs" />'
                '<meta property="og:description" content="Docs page" /></head></html>'
            ),
            {"etag": '"b2"', "last-modified": "Mon, 10 Feb 2025 09:00:00 GMT"},
        ),
    }

    class FakeHttpClient:
        def __init__(self, timeout: float = 8.0) -> None:  # noqa: ARG002
            pass

        def get(self, url: str, headers: dict | None = None):
            return pages.get(url, FakeResponse(404))

    return FakeHttpClient


def _failing_http_client() -> type:
    class FakeHttpClient:
        def __init__(self, timeout: float = 8.0) -> None:  # noqa: ARG002
            pass

        def get(self, url: str, headers: dict | None = None):  # noqa: ARG002
            if url.endswith("/llms.txt"):
                raise RuntimeError("network failure")
            return FakeResponse(404)

    return FakeHttpClient


def _setup_otel():
    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    metric_reader = InMemoryMetricReader()
    meter_provider = MeterProvider(metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    return span_exporter, metric_reader


def test_pipeline_happy_path_emits_spans_and_metrics(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "crawllmer.app.indexer.workers.httpx.Client", _success_http_client()
    )
    span_exporter, metric_reader = _setup_otel()

    repo = SqliteStorageRepository(db_url=f"sqlite:///{tmp_path}/happy.db")
    telemetry = PipelineTelemetry()
    pipeline = CrawlPipeline(
        repository=repo,
        queue=StubQueuePublisher(),
        telemetry=telemetry,
    )

    run = pipeline.enqueue_run("https://site.test")
    result = pipeline.process_run(run.id)

    assert result.status == RunStatus.completed
    assert repo.get_artifact(run.id) is not None

    spans = span_exporter.get_finished_spans()
    span_names = {span.name for span in spans}
    assert "crawl_pipeline.run" in span_names
    assert "crawl_pipeline.stage.discovery" in span_names
    assert "crawl_pipeline.stage.extraction" in span_names
    assert "crawl_pipeline.stage.generation" in span_names

    metric_data = metric_reader.get_metrics_data()
    metric_names = {
        metric.name
        for resource_metric in metric_data.resource_metrics
        for scope_metric in resource_metric.scope_metrics
        for metric in scope_metric.metrics
    }
    assert "crawllmer_pipeline_runs_total" in metric_names
    assert "crawllmer_pipeline_stage_duration_seconds" in metric_names
    assert "crawllmer_pipeline_processing_state_count" in metric_names
    # Business-level metrics
    assert "crawllmer_pages_indexed_total" in metric_names
    assert "crawllmer_run_duration_seconds" in metric_names
    assert "crawllmer_llmstxt_size_bytes" in metric_names


def test_pipeline_failure_path_marks_failed_stage_and_run(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "crawllmer.app.indexer.workers.httpx.Client", _failing_http_client()
    )
    _setup_otel()

    repo = SqliteStorageRepository(db_url=f"sqlite:///{tmp_path}/fail.db")
    pipeline = CrawlPipeline(
        repository=repo,
        queue=StubQueuePublisher(),
        telemetry=PipelineTelemetry(),
    )

    run = pipeline.enqueue_run("https://broken.test")

    try:
        pipeline.process_run(run.id)
    except PipelineProcessingError as exc:
        assert exc.stage == "discovery"
        assert isinstance(exc.__cause__, RuntimeError)
        assert "network failure" in str(exc.__cause__)
    else:
        raise AssertionError("expected PipelineProcessingError")

    saved = repo.get_run(run.id)
    assert saved is not None
    assert saved.status == RunStatus.failed

    states = [item.state for item in repo.list_work_items(run.id)]
    assert WorkItemState.failed in states
