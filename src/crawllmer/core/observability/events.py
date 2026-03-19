"""Structured event metadata and business-level OTEL metrics.

Event classes represent pipeline milestones.  Each serialises itself to
OTEL-compatible attributes via ``to_attributes()`` and drives business
metric recording through :class:`BusinessMetrics`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from opentelemetry import metrics


@dataclass(slots=True)
class EventMetadata(ABC):
    """Base for structured event data emitted during pipeline execution.

    Subclasses represent specific pipeline milestones.  Each event can
    serialise itself to OTEL-compatible attributes via ``to_attributes()``
    and is emitted through ``log_event()`` for structured logging.  The same
    event data drives business-level OTEL metric recording, ensuring a
    single emission point with no double-counting.
    """

    run_id: UUID
    event_name: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @abstractmethod
    def to_attributes(self) -> dict[str, str | int | float]:
        """Return OTEL span/log-compatible key-value pairs."""
        ...


@dataclass(slots=True)
class DiscoveryCompletedEvent(EventMetadata):
    """Emitted when the discovery stage completes for a run."""

    event_name: str = "discovery.completed"
    pages_discovered: int = 0
    strategies_used: list[str] = field(default_factory=list)

    def to_attributes(self) -> dict[str, str | int | float]:
        return {
            "run.id": str(self.run_id),
            "discovery.pages_discovered": self.pages_discovered,
            "discovery.strategies_used": ",".join(self.strategies_used),
        }


@dataclass(slots=True)
class ExtractionCompletedEvent(EventMetadata):
    """Emitted when the extraction stage completes for a run."""

    event_name: str = "extraction.completed"
    pages_extracted: int = 0
    pages_skipped: int = 0

    def to_attributes(self) -> dict[str, str | int | float]:
        return {
            "run.id": str(self.run_id),
            "extraction.pages_extracted": self.pages_extracted,
            "extraction.pages_skipped": self.pages_skipped,
        }


@dataclass(slots=True)
class GenerationCompletedEvent(EventMetadata):
    """Emitted when llms.txt generation completes for a run."""

    event_name: str = "generation.completed"
    llmstxt_size_bytes: int = 0
    entry_count: int = 0

    def to_attributes(self) -> dict[str, str | int | float]:
        return {
            "run.id": str(self.run_id),
            "generation.llmstxt_size_bytes": self.llmstxt_size_bytes,
            "generation.entry_count": self.entry_count,
        }


@dataclass(slots=True)
class RunCompletedEvent(EventMetadata):
    """Emitted when a full pipeline run completes (success or failure)."""

    event_name: str = "run.completed"
    total_pages_indexed: int = 0
    duration_seconds: float = 0.0
    llmstxt_size_bytes: int = 0

    def to_attributes(self) -> dict[str, str | int | float]:
        return {
            "run.id": str(self.run_id),
            "run.total_pages_indexed": self.total_pages_indexed,
            "run.duration_seconds": self.duration_seconds,
            "run.llmstxt_size_bytes": self.llmstxt_size_bytes,
        }


class BusinessMetrics:
    """Run-level OTEL metrics driven by structured event objects.

    Registers instruments on a ``crawllmer.business`` meter (separate from
    the stage-level ``crawllmer.pipeline`` meter in
    :class:`PipelineTelemetry`).  Methods accept event dataclasses so that
    metric recording is co-located with event emission.
    """

    def __init__(self) -> None:
        meter = metrics.get_meter("crawllmer.business")
        self._pages_indexed = meter.create_counter(
            "crawllmer_pages_indexed_total",
            description="Total pages indexed per run",
        )
        self._run_duration = meter.create_histogram(
            "crawllmer_run_duration_seconds",
            description="End-to-end run duration",
            unit="s",
        )
        self._llmstxt_size = meter.create_histogram(
            "crawllmer_llmstxt_size_bytes",
            description="Size of generated llms.txt",
            unit="By",
        )

    def record_run_completed(self, event: RunCompletedEvent) -> None:
        """Record business metrics from a completed pipeline run."""
        self._pages_indexed.add(event.total_pages_indexed)
        self._run_duration.record(event.duration_seconds)
        self._llmstxt_size.record(event.llmstxt_size_bytes)
