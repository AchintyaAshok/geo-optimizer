"""BFS spider scan — Phase 1 of the fallback crawler.

Traverses a website following <a href> links within the same domain,
building an in-link count map to rank pages by importance. Returns a
priority-ordered list of URLs for Phase 2 (indexing).
"""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from crawllmer.app.indexer.link_filter import extract_same_domain_links
from crawllmer.core.config import Settings


def spider_scan(
    seed_url: str,
    settings: Settings,
    client: httpx.Client | None = None,
    on_event: Callable[[str, dict[str, Any]], None] | None = None,
) -> list[tuple[str, int, int]]:
    """BFS scan of a website to build a ranked URL list.

    Args:
        seed_url: Starting URL to crawl from.
        settings: Application settings (spider bounds).
        client: Optional httpx client (for testing).
        on_event: Optional callback for emitting pipeline events.

    Returns:
        List of (url, inlink_count, depth) tuples, sorted by
        importance (most inlinks first, then shallowest depth).
    """
    hostname = urlparse(seed_url).netloc
    extensions = settings.spider_extensions_set
    max_depth = settings.spider_max_depth
    max_pages = settings.spider_max_scan_pages
    timeout = settings.spider_timeout_per_page

    emit = on_event or (lambda _name, _data: None)
    requester = client or httpx.Client(timeout=float(timeout))

    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(seed_url, 0)])
    inlink_count: Counter[str] = Counter()
    depth_map: dict[str, int] = {seed_url: 0}

    scan_start = datetime.now(UTC)
    emit(
        "spider.scan_started",
        {
            "seed_url": seed_url,
            "max_depth": max_depth,
            "max_scan_pages": max_pages,
        },
    )

    while queue and len(visited) < max_pages:
        url, depth = queue.popleft()

        if url in visited or depth > max_depth:
            continue

        visited.add(url)

        try:
            response = requester.get(url)
        except httpx.HTTPError:
            continue

        if response.status_code != 200:
            continue

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            continue

        links = extract_same_domain_links(response.text, url, hostname, extensions)

        emit(
            "spider.page_scanned",
            {
                "url": url,
                "depth": depth,
                "links_found": len(links),
                "inlink_score": inlink_count[url],
            },
        )

        for link in links:
            inlink_count[link] += 1
            if link not in visited and link not in depth_map:
                depth_map[link] = depth + 1
                queue.append((link, depth + 1))

    # Rank: most inlinks first, then shallowest depth
    ranked = sorted(
        visited,
        key=lambda u: (-inlink_count[u], depth_map.get(u, 0)),
    )

    scan_end = datetime.now(UTC)
    emit(
        "spider.scan_completed",
        {
            "pages_scanned": len(visited),
            "unique_links_found": len(inlink_count),
            "duration": (scan_end - scan_start).total_seconds(),
        },
    )

    return [(url, inlink_count[url], depth_map.get(url, 0)) for url in ranked]
