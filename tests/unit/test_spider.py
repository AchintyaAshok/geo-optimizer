from __future__ import annotations

from unittest.mock import MagicMock

import httpx

from crawllmer.app.indexer.spider import spider_scan
from crawllmer.core.config import Settings


def _mock_client(pages: dict[str, str]) -> httpx.Client:
    """Create a mock httpx.Client that returns predefined HTML per URL."""
    client = MagicMock(spec=httpx.Client)

    def fake_get(url, **kwargs):  # noqa: ARG001
        resp = MagicMock(spec=httpx.Response)
        if url in pages:
            resp.status_code = 200
            resp.text = pages[url]
            resp.headers = {"content-type": "text/html"}
        else:
            resp.status_code = 404
            resp.text = ""
            resp.headers = {"content-type": "text/html"}
        return resp

    client.get = fake_get
    return client


def _page(*links: str) -> str:
    hrefs = "".join(f'<a href="{href}">link</a>' for href in links)
    return f"<html><body>{hrefs}</body></html>"


def test_spider_discovers_linked_pages() -> None:
    pages = {
        "https://example.com": _page("/about", "/docs"),
        "https://example.com/about": _page("/"),
        "https://example.com/docs": _page("/", "/about"),
    }
    settings = Settings(spider_max_depth=2, spider_max_scan_pages=10)
    result = spider_scan("https://example.com", settings, _mock_client(pages))

    urls = [url for url, _, _ in result]
    assert "https://example.com" in urls
    assert "https://example.com/about" in urls
    assert "https://example.com/docs" in urls


def test_spider_respects_max_depth() -> None:
    pages = {
        "https://example.com": _page("/a"),
        "https://example.com/a": _page("/a/b"),
        "https://example.com/a/b": _page("/a/b/c"),
        "https://example.com/a/b/c": _page("/a/b/c/d"),
    }
    settings = Settings(spider_max_depth=2, spider_max_scan_pages=100)
    result = spider_scan("https://example.com", settings, _mock_client(pages))

    urls = [url for url, _, _ in result]
    assert "https://example.com" in urls
    assert "https://example.com/a" in urls
    assert "https://example.com/a/b" in urls
    # depth 3 should NOT be visited
    assert "https://example.com/a/b/c" not in urls


def test_spider_respects_max_pages() -> None:
    pages = {
        "https://example.com": _page("/a", "/b", "/c", "/d", "/e"),
        "https://example.com/a": _page(),
        "https://example.com/b": _page(),
        "https://example.com/c": _page(),
        "https://example.com/d": _page(),
        "https://example.com/e": _page(),
    }
    settings = Settings(spider_max_depth=5, spider_max_scan_pages=3)
    result = spider_scan("https://example.com", settings, _mock_client(pages))

    assert len(result) == 3


def test_spider_ranks_by_inlink_count() -> None:
    # /popular is linked from both root and /other (2 inlinks)
    # /other is linked only from root (1 inlink)
    pages = {
        "https://example.com": _page("/popular", "/other"),
        "https://example.com/other": _page("/popular"),
        "https://example.com/popular": _page(),
    }
    settings = Settings(spider_max_depth=3, spider_max_scan_pages=100)
    result = spider_scan("https://example.com", settings, _mock_client(pages))

    inlinks = {url: count for url, count, _ in result}
    assert inlinks["https://example.com/popular"] == 2
    assert inlinks["https://example.com/other"] == 1


def test_spider_handles_404s_gracefully() -> None:
    pages = {
        "https://example.com": _page("/exists", "/missing"),
        "https://example.com/exists": _page(),
    }
    settings = Settings(spider_max_depth=2, spider_max_scan_pages=10)
    result = spider_scan("https://example.com", settings, _mock_client(pages))

    urls = [url for url, _, _ in result]
    assert "https://example.com" in urls
    assert "https://example.com/exists" in urls


def test_spider_returns_seed_only_when_unreachable() -> None:
    settings = Settings(spider_max_depth=2, spider_max_scan_pages=10)
    result = spider_scan("https://example.com", settings, _mock_client({}))
    # Seed is visited but 404 produces no child links
    assert len(result) == 1
    assert result[0][0] == "https://example.com"
