from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


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


class DiscoverySource(StrEnum):
    llms = "llms"
    robots = "robots"
    sitemap = "sitemap"
    crawl = "crawl"


class WebsiteTarget(BaseModel):
    url: HttpUrl
    hostname: str


class LlmsTxtEntry(BaseModel):
    title: str
    url: HttpUrl
    description: str | None = None


class LlmsTxtDocument(BaseModel):
    source_url: HttpUrl
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    entries: list[LlmsTxtEntry] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)

    def to_text(self) -> str:
        sorted_entries = sorted(self.entries, key=lambda item: str(item.url))
        lines = [f"# llms.txt for {self.source_url.host}", ""]
        for entry in sorted_entries:
            line = f"- [{entry.title}]({entry.url})"
            if entry.description:
                line += f": {entry.description}"
            lines.append(line)
        return "\n".join(lines).strip() + "\n"


class SitemapUrl(BaseModel):
    loc: HttpUrl


class SitemapDocument(BaseModel):
    urls: list[SitemapUrl] = Field(default_factory=list)
    children: list[HttpUrl] = Field(default_factory=list)


class StrategyInput(BaseModel):
    target: WebsiteTarget
    run_id: UUID
    discovered: list[tuple[HttpUrl, DiscoverySource]] = Field(default_factory=list)


class StrategyOutput(BaseModel):
    strategy_id: str
    success: bool
    discovered: list[tuple[HttpUrl, DiscoverySource]] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


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
class CrawlEvent:
    id: UUID = field(default_factory=uuid4)
    run_id: UUID | None = None
    name: str = ""
    system: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float | None:
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()


@dataclass(slots=True)
class GenerationArtifact:
    run_id: UUID
    llms_txt: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
