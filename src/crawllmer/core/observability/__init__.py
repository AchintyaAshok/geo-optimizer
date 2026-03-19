"""Observability: telemetry bootstrap, pipeline metrics, and structured events."""

from crawllmer.core.observability.events import (
    BusinessMetrics,
    DiscoveryCompletedEvent,
    EventMetadata,
    ExtractionCompletedEvent,
    GenerationCompletedEvent,
    RunCompletedEvent,
)
from crawllmer.core.observability.pipeline_telemetry import (
    PipelineTelemetry,
    log_event,
)
from crawllmer.core.observability.telemetry_setup import setup_telemetry

__all__ = [
    "BusinessMetrics",
    "DiscoveryCompletedEvent",
    "EventMetadata",
    "ExtractionCompletedEvent",
    "GenerationCompletedEvent",
    "PipelineTelemetry",
    "RunCompletedEvent",
    "log_event",
    "setup_telemetry",
]
