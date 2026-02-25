from __future__ import annotations

from abc import ABC, abstractmethod

from crawllmer.domain.models import CrawlRun, StrategyResult, WebsiteTarget


class Strategy(ABC):
    id: str
    version: str = "v1"

    @abstractmethod
    def can_handle(self, target: WebsiteTarget, context: dict) -> bool: ...

    @abstractmethod
    def execute(self, target: WebsiteTarget, context: dict) -> StrategyResult: ...

    def cost_hint(self) -> int:
        return 100


class CrawlRunRepository(ABC):
    @abstractmethod
    def create_run(self, run: CrawlRun) -> CrawlRun: ...

    @abstractmethod
    def update_run(self, run: CrawlRun) -> CrawlRun: ...

    @abstractmethod
    def latest_runs(
        self, hostname: str | None = None, limit: int = 20
    ) -> list[CrawlRun]: ...

    @abstractmethod
    def strategy_history(self, hostname: str) -> list[str]: ...
