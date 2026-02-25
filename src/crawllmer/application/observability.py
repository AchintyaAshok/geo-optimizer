from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from time import perf_counter
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.trace import Span

LOGGER = logging.getLogger("crawllmer.pipeline")


def log_event(event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    LOGGER.info(json.dumps(payload, default=str, sort_keys=True))


class PipelineTelemetry:
    def __init__(self) -> None:
        meter = metrics.get_meter("crawllmer.pipeline")
        self.state_count = meter.create_up_down_counter(
            "crawllmer_pipeline_processing_state_count",
            description="Current number of work items in each processing state",
        )
        self.run_counter = meter.create_counter(
            "crawllmer_pipeline_runs_total",
            description="Count of pipeline runs by outcome",
        )
        self.stage_counter = meter.create_counter(
            "crawllmer_pipeline_stage_events_total",
            description="Count of stage execution outcomes",
        )
        self.stage_duration = meter.create_histogram(
            "crawllmer_pipeline_stage_duration_seconds",
            description="Duration per stage execution",
            unit="s",
        )
        self._tracer = trace.get_tracer("crawllmer.pipeline")

    @contextmanager
    def run_span(self, run_id: str, target_url: str):
        with self._tracer.start_as_current_span("crawl_pipeline.run") as span:
            span.set_attribute("run.id", run_id)
            span.set_attribute("run.target_url", target_url)
            yield span

    @contextmanager
    def stage_span(self, run_id: str, stage: str):
        start = perf_counter()
        with self._tracer.start_as_current_span(
            f"crawl_pipeline.stage.{stage}"
        ) as span:
            span.set_attribute("run.id", run_id)
            span.set_attribute("pipeline.stage", stage)
            yield span
            duration = perf_counter() - start
            self.stage_duration.record(duration, {"stage": stage})

    def track_state_transition(self, from_state: str | None, to_state: str) -> None:
        if from_state is not None:
            self.state_count.add(-1, {"state": from_state})
        self.state_count.add(1, {"state": to_state})

    def record_stage_outcome(self, stage: str, outcome: str) -> None:
        self.stage_counter.add(1, {"stage": stage, "outcome": outcome})

    def record_run_outcome(self, outcome: str) -> None:
        self.run_counter.add(1, {"outcome": outcome})

    @staticmethod
    def mark_error(span: Span, error: Exception) -> None:
        span.record_exception(error)
        span.set_attribute("error", True)
        span.set_attribute("error.message", str(error))
