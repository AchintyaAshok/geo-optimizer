from __future__ import annotations

from urllib.parse import urlparse

from crawllmer.adapters.storage import default_repository
from crawllmer.adapters.strategies import (
    BrowserAssistedStrategy,
    DirectLlmsTxtStrategy,
    MetadataExtractionStrategy,
    RobotsHintStrategy,
    WebArchiveAssistStrategy,
)
from crawllmer.application.orchestrator import CrawlOrchestrator
from crawllmer.domain.models import StrategyResult, WebsiteTarget

repo = default_repository()
orchestrator = CrawlOrchestrator(
    strategies=[
        DirectLlmsTxtStrategy(),
        RobotsHintStrategy(),
        MetadataExtractionStrategy(),
        BrowserAssistedStrategy(),
        WebArchiveAssistStrategy(),
    ],
    repository=repo,
)
LATEST: dict[str, str] = {}


def run_crawl(url: str):
    parsed = urlparse(url)
    target = WebsiteTarget(url=url, hostname=parsed.hostname or "")
    run, result = orchestrator.process(target)
    if result and isinstance(result, StrategyResult) and result.document:
        LATEST[str(run.id)] = result.document.to_text()
    return run, result
