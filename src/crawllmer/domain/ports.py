from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from uuid import UUID

from crawllmer.domain.models import (
    CrawlRun,
    ExtractedPage,
    GenerationArtifact,
    WorkItem,
)


class CrawlRepository(ABC):
    @abstractmethod
    def create_run(self, run: CrawlRun) -> CrawlRun: ...

    @abstractmethod
    def update_run(self, run: CrawlRun) -> CrawlRun: ...

    @abstractmethod
    def get_run(self, run_id: UUID) -> CrawlRun | None: ...

    @abstractmethod
    def list_runs(
        self, hostname: str | None = None, limit: int = 50
    ) -> list[CrawlRun]: ...

    @abstractmethod
    def create_work_item(self, item: WorkItem) -> WorkItem: ...

    @abstractmethod
    def update_work_item(self, item: WorkItem) -> WorkItem: ...

    @abstractmethod
    def list_work_items(self, run_id: UUID) -> list[WorkItem]: ...

    @abstractmethod
    def add_discovered_urls(
        self, run_id: UUID, urls: Iterable[tuple[str, str]]
    ) -> list[str]: ...

    @abstractmethod
    def get_discovered_urls(self, run_id: UUID) -> list[tuple[str, str]]: ...

    @abstractmethod
    def upsert_extracted_pages(self, pages: Iterable[ExtractedPage]) -> None: ...

    @abstractmethod
    def get_extracted_pages(self, run_id: UUID) -> list[ExtractedPage]: ...

    @abstractmethod
    def set_validator(
        self, url: str, etag: str | None, last_modified: str | None
    ) -> None: ...

    @abstractmethod
    def get_validator(self, url: str) -> tuple[str | None, str | None]: ...

    @abstractmethod
    def save_artifact(self, artifact: GenerationArtifact) -> None: ...

    @abstractmethod
    def get_artifact(self, run_id: UUID) -> GenerationArtifact | None: ...


class QueuePublisher(ABC):
    @abstractmethod
    def publish(self, queue_name: str, payload: dict) -> None: ...
