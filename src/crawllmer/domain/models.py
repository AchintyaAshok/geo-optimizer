from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class RunStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class WorkStage(StrEnum):
    discovery = "discovery"
    extraction = "extraction"
    canonicalization = "canonicalization"
    scoring = "scoring"
    generation = "generation"


class WorkItemState(StrEnum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


@dataclass(slots=True)
class CrawlRun:
    id: UUID = field(default_factory=uuid4)
    target_url: str = ""
    hostname: str = ""
    status: RunStatus = RunStatus.queued
    score: float | None = None
    score_breakdown: dict[str, float] = field(default_factory=dict)
    artifact_path: str | None = None
    notes: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


@dataclass(slots=True)
class WorkItem:
    id: UUID = field(default_factory=uuid4)
    run_id: UUID | None = None
    stage: WorkStage = WorkStage.discovery
    state: WorkItemState = WorkItemState.queued
    url: str = ""
    attempt_count: int = 0
    last_error: str | None = None
    priority: int = 100
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def transition(self, next_state: WorkItemState) -> None:
        allowed = {
            WorkItemState.queued: {WorkItemState.processing, WorkItemState.failed},
            WorkItemState.processing: {WorkItemState.completed, WorkItemState.failed},
            WorkItemState.completed: set(),
            WorkItemState.failed: set(),
        }
        if next_state not in allowed[self.state]:
            msg = f"invalid transition {self.state} -> {next_state}"
            raise ValueError(msg)
        self.state = next_state
        self.updated_at = datetime.now(UTC)


@dataclass(slots=True)
class ExtractedPage:
    run_id: UUID
    url: str
    title: str | None = None
    description: str | None = None
    provenance: dict[str, str] = field(default_factory=dict)
    confidence: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class GenerationArtifact:
    run_id: UUID
    llms_txt: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
