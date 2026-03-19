from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup

from crawllmer.domain.models import (
    DiscoverySource,
    ExtractedPage,
    LlmsTxtDocument,
    LlmsTxtEntry,
    SitemapDocument,
    SitemapUrl,
    StrategyInput,
    StrategyOutput,
    WebsiteTarget,
)


def discover_urls(
    target_url: str,
    client: httpx.Client | None = None,
) -> list[tuple[str, str]]:
    """Run hierarchical discovery strategies and return deduplicated URL candidates.

    Strategy order follows PRD guidance:
    1) direct llms probe,
    2) robots hints,
    3) sitemap traversal,
    4) bounded fallback seed.
    """
    target = WebsiteTarget(url=target_url, hostname=urlparse(target_url).netloc)
    context = StrategyInput(target=target, run_id=uuid4())
    requester = client or httpx.Client(timeout=8.0)

    outputs: list[StrategyOutput] = [
        _direct_llms_strategy(context, requester),
        _robots_hints_strategy(context, requester),
    ]

    discovered = _collect_discovered(outputs)
    if not discovered:
        sitemap_output = _sitemap_strategy(context, requester)
        outputs.append(sitemap_output)
        discovered = _collect_discovered(outputs)

    if not discovered:
        outputs.append(_fallback_seed_strategy(context))
        discovered = _collect_discovered(outputs)

    deduped: dict[str, str] = {}
    for url, source in discovered:
        deduped.setdefault(str(url), source.value)
    return list(deduped.items())


def _direct_llms_strategy(
    context: StrategyInput, requester: httpx.Client
) -> StrategyOutput:
    base = f"{context.target.url.scheme}://{context.target.hostname}"
    llms = requester.get(f"{base}/llms.txt")
    if llms.status_code != 200:
        return StrategyOutput(
            strategy_id="direct_llms",
            success=False,
            diagnostics={"status_code": llms.status_code},
        )

    found: list[tuple[str, DiscoverySource]] = []
    for line in llms.text.splitlines():
        match = re.search(r"\[[^\]]+\]\(([^\)]+)\)", line)
        if match:
            found.append((urljoin(base, match.group(1)), DiscoverySource.llms))
    return StrategyOutput(
        strategy_id="direct_llms", success=bool(found), discovered=found
    )


def _robots_hints_strategy(
    context: StrategyInput, requester: httpx.Client
) -> StrategyOutput:
    base = f"{context.target.url.scheme}://{context.target.hostname}"
    robots = requester.get(f"{base}/robots.txt")
    if robots.status_code != 200:
        return StrategyOutput(
            strategy_id="robots_hints",
            success=False,
            diagnostics={"status_code": robots.status_code},
        )

    discovered: list[tuple[str, DiscoverySource]] = []
    for line in robots.text.splitlines():
        lower = line.lower()
        if lower.startswith("llms:"):
            discovered.append(
                (urljoin(base, line.split(":", 1)[1].strip()), DiscoverySource.robots)
            )
        if lower.startswith("sitemap:"):
            sitemap_url = line.split(":", 1)[1].strip()
            parsed = parse_sitemap(requester, sitemap_url)
            discovered.extend(
                (str(url.loc), DiscoverySource.sitemap) for url in parsed.urls
            )
    return StrategyOutput(
        strategy_id="robots_hints",
        success=bool(discovered),
        discovered=discovered,
    )


def _sitemap_strategy(
    context: StrategyInput, requester: httpx.Client
) -> StrategyOutput:
    base = f"{context.target.url.scheme}://{context.target.hostname}"
    parsed = parse_sitemap(requester, f"{base}/sitemap.xml")
    discovered = [(str(url.loc), DiscoverySource.sitemap) for url in parsed.urls]
    return StrategyOutput(
        strategy_id="sitemap", success=bool(discovered), discovered=discovered
    )


def _fallback_seed_strategy(context: StrategyInput) -> StrategyOutput:
    return StrategyOutput(
        strategy_id="fallback_seed",
        success=True,
        discovered=[(str(context.target.url), DiscoverySource.crawl)],
    )


def _collect_discovered(
    outputs: list[StrategyOutput],
) -> list[tuple[str, DiscoverySource]]:
    discovered: list[tuple[str, DiscoverySource]] = []
    for output in outputs:
        discovered.extend(output.discovered)
    return discovered


def parse_sitemap(client: httpx.Client, sitemap_url: str) -> SitemapDocument:
    """Parse sitemap index or urlset recursively into a typed sitemap document."""
    response = client.get(sitemap_url)
    if response.status_code != 200:
        return SitemapDocument()

    root = ET.fromstring(response.text)
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    document = SitemapDocument()

    for child in root.findall(f"{namespace}sitemap"):
        loc = child.find(f"{namespace}loc")
        if loc is not None and loc.text:
            child_doc = parse_sitemap(client, loc.text.strip())
            document.children.append(loc.text.strip())
            document.urls.extend(child_doc.urls)

    for child in root.findall(f"{namespace}url"):
        loc = child.find(f"{namespace}loc")
        if loc is not None and loc.text:
            document.urls.append(SitemapUrl(loc=loc.text.strip()))

    return document


def extract_metadata(
    run_id,
    urls: list[tuple[str, str]],
    validators: dict[str, tuple[str | None, str | None]],
    client: httpx.Client | None = None,
    on_page_event: Callable[[str, dict[str, Any]], None] | None = None,
) -> tuple[list[ExtractedPage], dict[str, tuple[str | None, str | None]]]:
    requester = client or httpx.Client(timeout=8.0)
    pages: list[ExtractedPage] = []
    new_validators: dict[str, tuple[str | None, str | None]] = {}
    emit = on_page_event or (lambda _name, _data: None)

    for url, provenance in urls:
        fetch_start = datetime.now(UTC)
        headers = {}
        etag, last_modified = validators.get(url, (None, None))
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        response = requester.get(url, headers=headers)
        fetch_end = datetime.now(UTC)

        if response.status_code == 304:
            emit(
                "extraction.page_skipped",
                {
                    "url": url,
                    "reason": "not_modified",
                    "status_code": 304,
                    "started_at": fetch_start,
                    "completed_at": fetch_end,
                },
            )
            continue
        if response.status_code != 200:
            emit(
                "extraction.page_skipped",
                {
                    "url": url,
                    "reason": "http_error",
                    "status_code": response.status_code,
                    "started_at": fetch_start,
                    "completed_at": fetch_end,
                },
            )
            continue

        title, title_source, title_conf = _extract_title(response.text)
        desc, desc_source, desc_conf = _extract_description(response.text)
        pages.append(
            ExtractedPage(
                run_id=run_id,
                url=url,
                title=title,
                description=desc,
                provenance={
                    "discovery": provenance,
                    "title": title_source,
                    "description": desc_source,
                },
                confidence={"title": title_conf, "description": desc_conf},
            )
        )
        new_validators[url] = (
            response.headers.get("etag"),
            response.headers.get("last-modified"),
        )
        emit(
            "extraction.page_extracted",
            {
                "url": url,
                "provenance": provenance,
                "title": title,
                "title_source": title_source,
                "title_confidence": title_conf,
                "description": desc[:120] if desc else None,
                "description_source": desc_source,
                "description_confidence": desc_conf,
                "started_at": fetch_start,
                "completed_at": datetime.now(UTC),
            },
        )
    return pages, new_validators


def _extract_title(html: str) -> tuple[str | None, str, float]:
    soup = BeautifulSoup(html, "html.parser")
    head = soup.head or soup

    if head.title and head.title.string and head.title.string.strip():
        return head.title.string.strip(), "title", 1.0

    og = _meta_content(head, property_name="og:title")
    if og:
        return og, "og:title", 0.8

    twitter = _meta_content(head, property_name="twitter:title")
    if twitter:
        return twitter, "twitter:title", 0.75

    headline = _jsonld_value_from_head(head, "headline")
    if headline:
        return headline, "jsonld:headline", 0.6

    return None, "none", 0.0


def _extract_description(html: str) -> tuple[str | None, str, float]:
    soup = BeautifulSoup(html, "html.parser")
    head = soup.head or soup

    description = _meta_content(head, name="description")
    if description:
        return description, "meta:description", 1.0

    og = _meta_content(head, property_name="og:description")
    if og:
        return og, "og:description", 0.8

    twitter = _meta_content(head, property_name="twitter:description")
    if twitter:
        return twitter, "twitter:description", 0.75

    jsonld_desc = _jsonld_value_from_head(head, "description")
    if jsonld_desc:
        return jsonld_desc, "jsonld:description", 0.6

    return None, "none", 0.0


def _meta_content(
    head,
    *,
    name: str | None = None,
    property_name: str | None = None,
) -> str | None:
    attrs: dict[str, str] = {}
    if name:
        attrs["name"] = name
    if property_name:
        attrs["property"] = property_name
    tag = head.find("meta", attrs=attrs)
    if tag and tag.get("content"):
        return str(tag.get("content")).strip()
    return None


def _jsonld_value_from_head(head, key: str) -> str | None:
    for script in head.find_all("script", attrs={"type": "application/ld+json"}):
        if not script.string:
            continue
        try:
            payload = json.loads(script.string)
        except json.JSONDecodeError:
            continue
        values = payload if isinstance(payload, list) else [payload]
        for obj in values:
            if isinstance(obj, dict) and key in obj and isinstance(obj[key], str):
                return obj[key].strip()
    return None


def canonicalize_and_dedup(pages: list[ExtractedPage]) -> list[ExtractedPage]:
    canonical: dict[str, ExtractedPage] = {}
    for page in pages:
        normalized = _normalize_url(page.url)
        if normalized not in canonical:
            page.url = normalized
            canonical[normalized] = page
            continue
        if (page.confidence.get("title", 0) + page.confidence.get("description", 0)) > (
            canonical[normalized].confidence.get("title", 0)
            + canonical[normalized].confidence.get("description", 0)
        ):
            page.url = normalized
            canonical[normalized] = page
    return list(canonical.values())


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return f"{parsed.scheme}://{parsed.netloc}{path}".lower()


def score_pages(pages: list[ExtractedPage]) -> dict[str, float]:
    if not pages:
        return {"coverage": 0.0, "confidence": 0.0, "redundancy": 0.0, "total": 0.0}

    titled = sum(1 for page in pages if page.title)
    described = sum(1 for page in pages if page.description)
    coverage = ((titled / len(pages)) + (described / len(pages))) / 2
    confidence = sum(
        (page.confidence.get("title", 0.0) + page.confidence.get("description", 0.0))
        / 2
        for page in pages
    ) / len(pages)
    unique_urls = len({page.url for page in pages})
    redundancy = unique_urls / len(pages)
    total = round((coverage * 0.4) + (confidence * 0.4) + (redundancy * 0.2), 4)
    return {
        "coverage": round(coverage, 4),
        "confidence": round(confidence, 4),
        "redundancy": round(redundancy, 4),
        "total": total,
    }


def generate_llms_txt(
    hostname: str,
    pages: list[ExtractedPage],
    *,
    site_title: str | None = None,
    site_description: str | None = None,
    links_discovered: int = 0,
) -> str:
    """Build a spec-compliant llms.txt grouped by top-level URL path."""
    sections: dict[str, list[LlmsTxtEntry]] = {}
    for page in pages:
        entry = LlmsTxtEntry(
            title=(page.title or page.url),
            url=page.url,
            description=page.description,
        )
        section = _section_name_from_url(page.url, hostname)
        sections.setdefault(section, []).append(entry)

    document = LlmsTxtDocument(
        source_url=f"https://{hostname}",
        title=site_title or hostname,
        site_description=site_description,
        pages_crawled=len(pages),
        links_discovered=links_discovered or len(pages),
        sections=sections,
    )
    return document.to_text()


def _section_name_from_url(url: str, hostname: str) -> str:
    """Derive an H2 section name from the first path segment."""
    parsed = urlparse(url)

    # External links get their own section
    if parsed.netloc and parsed.netloc != hostname:
        return "External"

    path = parsed.path.strip("/")
    if not path:
        return "Home"

    first_segment = path.split("/")[0]
    # Strip file extensions (.html, .md, .txt, etc.)
    name = first_segment.rsplit(".", 1)[0] if "." in first_segment else first_segment
    return name.replace("-", " ").replace("_", " ").title()
