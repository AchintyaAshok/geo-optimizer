from crawllmer.application.orchestrator import CrawlOrchestrator
from crawllmer.domain.models import (
    CrawlRun,
    CrawlStatus,
    LlmsTxtDocument,
    LlmsTxtEntry,
    StrategyResult,
    WebsiteTarget,
)
from crawllmer.domain.ports import CrawlRunRepository, Strategy


class InMemoryRepo(CrawlRunRepository):
    def __init__(self) -> None:
        self.runs: list[CrawlRun] = []

    def create_run(self, run: CrawlRun) -> CrawlRun:
        self.runs.append(run)
        return run

    def update_run(self, run: CrawlRun) -> CrawlRun:
        return run

    def latest_runs(
        self, hostname: str | None = None, limit: int = 20
    ) -> list[CrawlRun]:
        return self.runs[-limit:]

    def strategy_history(self, hostname: str) -> list[str]:
        return []


class FailStrategy(Strategy):
    id = "fail"

    def can_handle(self, target: WebsiteTarget, context: dict) -> bool:
        return True

    def execute(self, target: WebsiteTarget, context: dict) -> StrategyResult:
        return StrategyResult(strategy_id=self.id, success=False)


class SuccessStrategy(Strategy):
    id = "success"

    def can_handle(self, target: WebsiteTarget, context: dict) -> bool:
        return True

    def execute(self, target: WebsiteTarget, context: dict) -> StrategyResult:
        return StrategyResult(
            strategy_id=self.id,
            success=True,
            document=LlmsTxtDocument(
                source_url=target.url,
                entries=[LlmsTxtEntry(title="Home", url=target.url)],
            ),
        )


def test_orchestrator_short_circuits_on_success() -> None:
    orchestrator = CrawlOrchestrator(
        strategies=[FailStrategy(), SuccessStrategy(), FailStrategy()],
        repository=InMemoryRepo(),
    )
    run, result = orchestrator.process(
        WebsiteTarget(url="https://example.com", hostname="example.com")
    )

    assert run.status == CrawlStatus.succeeded
    assert run.strategy_attempts == ["fail", "success"]
    assert result is not None
    assert result.success is True
