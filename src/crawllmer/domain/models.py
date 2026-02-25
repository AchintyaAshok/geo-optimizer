from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class CrawlStatus(StrEnum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class WebsiteTarget(BaseModel):
    url: HttpUrl
    hostname: str


class DocumentSource(BaseModel):
    url: HttpUrl
    retrieval_method: str
    mime_type: str = "text/html"
    status_code: int | None = None


class PageMetadata(BaseModel):
    url: HttpUrl
    title: str | None = None
    description: str | None = None
    language: str | None = None
    priority: int = 0


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


class StrategyResult(BaseModel):
    strategy_id: str
    success: bool
    document: LlmsTxtDocument | None = None
    pages: list[PageMetadata] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class CrawlRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    target: WebsiteTarget
    status: CrawlStatus = CrawlStatus.pending
    strategy_attempts: list[str] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
