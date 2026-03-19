from __future__ import annotations

from uuid import uuid4

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from crawllmer.core.observability import (
    BusinessMetrics,
    DiscoveryCompletedEvent,
    ExtractionCompletedEvent,
    GenerationCompletedEvent,
    RunCompletedEvent,
)


class TestDiscoveryCompletedEvent:
    def test_stores_fields(self) -> None:
        rid = uuid4()
        event = DiscoveryCompletedEvent(
            run_id=rid, pages_discovered=5, strategies_used=["llms", "sitemap"]
        )
        assert event.run_id == rid
        assert event.pages_discovered == 5
        assert event.event_name == "discovery.completed"

    def test_to_attributes(self) -> None:
        event = DiscoveryCompletedEvent(
            run_id=uuid4(), pages_discovered=3, strategies_used=["llms", "robots"]
        )
        attrs = event.to_attributes()
        assert attrs["discovery.pages_discovered"] == 3
        assert attrs["discovery.strategies_used"] == "llms,robots"


class TestExtractionCompletedEvent:
    def test_stores_fields(self) -> None:
        event = ExtractionCompletedEvent(
            run_id=uuid4(), pages_extracted=10, pages_skipped=2
        )
        assert event.pages_extracted == 10
        assert event.pages_skipped == 2
        assert event.event_name == "extraction.completed"

    def test_to_attributes(self) -> None:
        event = ExtractionCompletedEvent(
            run_id=uuid4(), pages_extracted=8, pages_skipped=1
        )
        attrs = event.to_attributes()
        assert attrs["extraction.pages_extracted"] == 8
        assert attrs["extraction.pages_skipped"] == 1


class TestGenerationCompletedEvent:
    def test_stores_fields(self) -> None:
        event = GenerationCompletedEvent(
            run_id=uuid4(), llmstxt_size_bytes=4096, entry_count=12
        )
        assert event.llmstxt_size_bytes == 4096
        assert event.entry_count == 12

    def test_to_attributes(self) -> None:
        event = GenerationCompletedEvent(
            run_id=uuid4(), llmstxt_size_bytes=2048, entry_count=6
        )
        attrs = event.to_attributes()
        assert attrs["generation.llmstxt_size_bytes"] == 2048
        assert attrs["generation.entry_count"] == 6


class TestRunCompletedEvent:
    def test_stores_fields(self) -> None:
        event = RunCompletedEvent(
            run_id=uuid4(),
            total_pages_indexed=20,
            duration_seconds=5.5,
            llmstxt_size_bytes=8192,
        )
        assert event.total_pages_indexed == 20
        assert event.duration_seconds == 5.5
        assert event.llmstxt_size_bytes == 8192

    def test_to_attributes(self) -> None:
        rid = uuid4()
        event = RunCompletedEvent(
            run_id=rid,
            total_pages_indexed=15,
            duration_seconds=3.2,
            llmstxt_size_bytes=4000,
        )
        attrs = event.to_attributes()
        assert attrs["run.id"] == str(rid)
        assert attrs["run.total_pages_indexed"] == 15
        assert attrs["run.duration_seconds"] == 3.2


class TestBusinessMetrics:
    def test_record_run_completed_emits_metrics(self) -> None:
        reader = InMemoryMetricReader()
        provider = MeterProvider(metric_readers=[reader])
        # Use the provider directly to avoid global set_meter_provider conflicts
        original_get_meter = metrics.get_meter

        def patched_get_meter(name, *a, **kw):
            return provider.get_meter(name, *a, **kw)

        metrics.get_meter = patched_get_meter
        try:
            bm = BusinessMetrics()
            event = RunCompletedEvent(
                run_id=uuid4(),
                total_pages_indexed=10,
                duration_seconds=2.5,
                llmstxt_size_bytes=1024,
            )
            bm.record_run_completed(event)

            data = reader.get_metrics_data()
            names = {
                m.name
                for rm in data.resource_metrics
                for sm in rm.scope_metrics
                for m in sm.metrics
            }
            assert "crawllmer_pages_indexed_total" in names
            assert "crawllmer_run_duration_seconds" in names
            assert "crawllmer_llmstxt_size_bytes" in names
        finally:
            metrics.get_meter = original_get_meter
