from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx

from crawllmer.domain.models import (
    LlmsTxtDocument,
    LlmsTxtEntry,
    StrategyResult,
    WebsiteTarget,
)
from crawllmer.domain.ports import Strategy


class DirectLlmsTxtStrategy(Strategy):
    id = "direct_llms_txt"

    def can_handle(self, target: WebsiteTarget, context: dict) -> bool:
        return True

    def execute(self, target: WebsiteTarget, context: dict) -> StrategyResult:
        response = httpx.get(
            f"{target.url.scheme}://{target.hostname}/llms.txt", timeout=5.0
        )
        if response.status_code == 200 and response.text.strip():
            entries: list[LlmsTxtEntry] = []
            for line in response.text.splitlines():
                match = re.search(r"\[(?P<title>[^\]]+)\]\((?P<url>[^\)]+)\)", line)
                if not match:
                    continue
                entries.append(
                    LlmsTxtEntry(
                        title=match.group("title"),
                        url=match.group("url"),
                    )
                )
            document = LlmsTxtDocument(
                source_url=target.url,
                entries=entries,
                provenance={"strategy": self.id, "source": "/llms.txt"},
            )
            return StrategyResult(strategy_id=self.id, success=True, document=document)
        return StrategyResult(
            strategy_id=self.id,
            success=False,
            diagnostics={"status_code": response.status_code},
        )

    def cost_hint(self) -> int:
        return 1


class RobotsHintStrategy(Strategy):
    id = "robots_hints"

    def can_handle(self, target: WebsiteTarget, context: dict) -> bool:
        return True

    def execute(self, target: WebsiteTarget, context: dict) -> StrategyResult:
        robots_url = f"{target.url.scheme}://{target.hostname}/robots.txt"
        response = httpx.get(robots_url, timeout=5.0)
        if response.status_code != 200:
            return StrategyResult(
                strategy_id=self.id,
                success=False,
                diagnostics={"status_code": response.status_code},
            )

        llms_url = None
        for line in response.text.splitlines():
            if line.lower().startswith("llms:"):
                llms_url = line.split(":", 1)[1].strip()
                break
        if not llms_url:
            return StrategyResult(strategy_id=self.id, success=False)

        fetched = httpx.get(urljoin(str(target.url), llms_url), timeout=5.0)
        if fetched.status_code != 200:
            return StrategyResult(
                strategy_id=self.id,
                success=False,
                diagnostics={"llms_status": fetched.status_code},
            )
        document = LlmsTxtDocument(
            source_url=target.url,
            entries=[
                LlmsTxtEntry(
                    title="Hinted llms", url=urljoin(str(target.url), llms_url)
                )
            ],
            provenance={"strategy": self.id, "source": robots_url},
        )
        return StrategyResult(strategy_id=self.id, success=True, document=document)

    def cost_hint(self) -> int:
        return 2


class MetadataExtractionStrategy(Strategy):
    id = "metadata_extraction"

    def can_handle(self, target: WebsiteTarget, context: dict) -> bool:
        return True

    def execute(self, target: WebsiteTarget, context: dict) -> StrategyResult:
        response = httpx.get(
            str(target.url),
            timeout=8.0,
            headers={"User-Agent": "Mozilla/5.0 crawllmer"},
        )
        if response.status_code != 200:
            return StrategyResult(
                strategy_id=self.id,
                success=False,
                diagnostics={"status_code": response.status_code},
            )

        title_match = re.search(
            r"<title>(.*?)</title>", response.text, flags=re.IGNORECASE | re.DOTALL
        )
        title = title_match.group(1).strip() if title_match else target.hostname
        desc_match = re.search(
            r'<meta\s+name="description"\s+content="(.*?)"\s*/?>',
            response.text,
            flags=re.IGNORECASE,
        )
        description = desc_match.group(1).strip() if desc_match else None
        document = LlmsTxtDocument(
            source_url=target.url,
            entries=[
                LlmsTxtEntry(title=title, url=target.url, description=description)
            ],
            provenance={"strategy": self.id, "generated": True},
        )
        return StrategyResult(strategy_id=self.id, success=True, document=document)

    def cost_hint(self) -> int:
        return 5


class BrowserAssistedStrategy(Strategy):
    id = "browser_assisted"

    def can_handle(self, target: WebsiteTarget, context: dict) -> bool:
        return context.get("enable_browser", False)

    def execute(self, target: WebsiteTarget, context: dict) -> StrategyResult:
        return StrategyResult(
            strategy_id=self.id,
            success=False,
            diagnostics={"note": "playwright adapter not yet enabled in runtime"},
        )

    def cost_hint(self) -> int:
        return 20


class WebArchiveAssistStrategy(Strategy):
    id = "web_archive_assist"

    def can_handle(self, target: WebsiteTarget, context: dict) -> bool:
        return context.get("enable_archive", False)

    def execute(self, target: WebsiteTarget, context: dict) -> StrategyResult:
        return StrategyResult(
            strategy_id=self.id,
            success=False,
            diagnostics={"note": "archive assist is extension"},
        )

    def cost_hint(self) -> int:
        return 30
