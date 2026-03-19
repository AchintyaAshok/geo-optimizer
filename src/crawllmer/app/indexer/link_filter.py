"""Link extraction and filtering for the spider.

Uses BeautifulSoup to parse <a href> tags and filters by:
- Same-domain only
- Extension allowlist (from config)
- Non-content path exclusion
"""

from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

NON_CONTENT_SEGMENTS = frozenset(
    {
        "login",
        "logout",
        "signup",
        "register",
        "cart",
        "checkout",
        "admin",
        "wp-admin",
        "wp-login",
        "account",
        "search",
    }
)


def extract_same_domain_links(
    html: str,
    base_url: str,
    hostname: str,
    include_extensions: set[str],
) -> list[str]:
    """Extract same-domain links from HTML, filtered by extension and path.

    Args:
        html: Raw HTML content of the page.
        base_url: The URL of the page (for resolving relative hrefs).
        hostname: The target hostname to filter to.
        include_extensions: Set of allowed extensions (e.g. {".html", ".md", ""}).
            Empty string means extensionless paths are allowed.

    Returns:
        Deduplicated list of filtered URLs.
    """
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    links: list[str] = []

    for tag in soup.find_all("a", href=True):
        href = tag["href"]

        # Resolve relative URLs
        url = urljoin(base_url, href)
        parsed = urlparse(url)

        # Same domain only
        if parsed.netloc and parsed.netloc != hostname:
            continue

        # Strip fragments
        url = url.split("#")[0]
        if not url:
            continue

        # Skip already seen
        if url in seen:
            continue

        # Check extension
        ext = PurePosixPath(parsed.path).suffix.lower()
        if ext and ext not in include_extensions:
            continue
        if not ext and "" not in include_extensions:
            continue

        # Check non-content paths
        path_segments = parsed.path.lower().strip("/").split("/")
        if any(seg in NON_CONTENT_SEGMENTS for seg in path_segments):
            continue

        seen.add(url)
        links.append(url)

    return links
