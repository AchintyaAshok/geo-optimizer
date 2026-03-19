"""Single-page indexing — the atomic unit of extraction work.

Fetches one URL, extracts title and description metadata, and returns
an ExtractedPage. This is the shared primitive used by both the spider
(Phase 2) and the bulk extraction stage.
"""

from __future__ import annotations

from uuid import UUID

import httpx

from crawllmer.app.indexer.workers import _extract_description, _extract_title
from crawllmer.domain.models import ExtractedPage


def index_page(
    url: str,
    run_id: UUID,
    provenance: str = "crawl",
    client: httpx.Client | None = None,
    timeout: float = 8.0,
) -> ExtractedPage | None:
    """Fetch a single page and extract metadata.

    Args:
        url: The URL to fetch.
        run_id: The crawl run this page belongs to.
        provenance: How the URL was discovered (llms/sitemap/robots/crawl).
        client: Optional httpx client.
        timeout: HTTP request timeout in seconds.

    Returns:
        ExtractedPage if successful, None if the page could not be fetched
        or returned a non-200 status.
    """
    requester = client or httpx.Client(timeout=timeout)

    try:
        response = requester.get(url)
    except httpx.HTTPError:
        return None

    if response.status_code != 200:
        return None

    title, title_source, title_conf = _extract_title(response.text)
    desc, desc_source, desc_conf = _extract_description(response.text)

    return ExtractedPage(
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
