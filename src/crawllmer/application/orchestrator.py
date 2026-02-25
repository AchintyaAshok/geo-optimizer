from __future__ import annotations

import logging

from crawllmer.application.retry import RetryPolicy
from crawllmer.domain.models import CrawlRun, CrawlStatus, StrategyResult, WebsiteTarget
from crawllmer.domain.ports import CrawlRunRepository, Strategy

logger = logging.getLogger(__name__)


class CrawlOrchestrator:
    def __init__(
        self,
        strategies: list[Strategy],
        repository: CrawlRunRepository,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._strategies = strategies
        self._repository = repository
        self._retry = retry_policy or RetryPolicy()

    def process(self, target: WebsiteTarget) -> tuple[CrawlRun, StrategyResult | None]:
        ordered_strategies = self._order_strategies(target.hostname)
        run = CrawlRun(target=target, status=CrawlStatus.running)
        run = self._repository.create_run(run)
        context: dict = {"run_id": str(run.id)}
        result: StrategyResult | None = None

        for strategy in ordered_strategies:
            if not strategy.can_handle(target, context):
                continue

            run.strategy_attempts.append(strategy.id)
            logger.info(
                "strategy.start",
                extra={"strategy": strategy.id, "host": target.hostname},
            )
            try:
                current = self._retry.run(lambda: strategy.execute(target, context))
            except Exception as exc:  # noqa: BLE001
                run.diagnostics[strategy.id] = {"error": str(exc)}
                logger.warning(
                    "strategy.error", extra={"strategy": strategy.id, "error": str(exc)}
                )
                continue

            run.diagnostics[strategy.id] = current.diagnostics
            if current.success:
                run.status = CrawlStatus.succeeded
                result = current
                break

        if run.status != CrawlStatus.succeeded:
            run.status = CrawlStatus.failed

        run = self._repository.update_run(run)
        return run, result

    def _order_strategies(self, hostname: str) -> list[Strategy]:
        historical = self._repository.strategy_history(hostname)
        ranking = {name: idx for idx, name in enumerate(historical)}
        return sorted(
            self._strategies,
            key=lambda strategy: (ranking.get(strategy.id, 1000), strategy.cost_hint()),
        )
