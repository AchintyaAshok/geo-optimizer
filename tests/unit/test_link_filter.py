from __future__ import annotations

from crawllmer.app.indexer.link_filter import extract_same_domain_links

BASE = "https://example.com/page"
HOST = "example.com"
DEFAULT_EXTS = {".html", ".htm", ".txt", ".md", ""}


def _html(*hrefs: str) -> str:
    links = "".join(f'<a href="{h}">link</a>' for h in hrefs)
    return f"<html><body>{links}</body></html>"


def test_extracts_same_domain_links() -> None:
    html = _html("/about", "/docs/intro", "https://example.com/contact")
    result = extract_same_domain_links(html, BASE, HOST, DEFAULT_EXTS)
    assert "https://example.com/about" in result
    assert "https://example.com/docs/intro" in result
    assert "https://example.com/contact" in result


def test_filters_external_domains() -> None:
    html = _html("https://other.com/page", "/local")
    result = extract_same_domain_links(html, BASE, HOST, DEFAULT_EXTS)
    assert len(result) == 1
    assert "https://example.com/local" in result


def test_strips_fragments() -> None:
    html = _html("/page#section1", "/page#section2")
    result = extract_same_domain_links(html, BASE, HOST, DEFAULT_EXTS)
    # Both should resolve to the same URL after fragment stripping
    assert len(result) == 1
    assert "https://example.com/page" in result


def test_deduplicates() -> None:
    html = _html("/about", "/about", "/about")
    result = extract_same_domain_links(html, BASE, HOST, DEFAULT_EXTS)
    assert len(result) == 1


def test_filters_disallowed_extensions() -> None:
    html = _html("/style.css", "/script.js", "/image.png", "/page.html")
    result = extract_same_domain_links(html, BASE, HOST, DEFAULT_EXTS)
    assert len(result) == 1
    assert "https://example.com/page.html" in result


def test_allows_extensionless_paths() -> None:
    html = _html("/docs/intro", "/blog/my-post")
    result = extract_same_domain_links(html, BASE, HOST, DEFAULT_EXTS)
    assert len(result) == 2


def test_rejects_extensionless_when_not_in_allowlist() -> None:
    exts = {".html"}  # no empty string
    html = _html("/docs/intro", "/page.html")
    result = extract_same_domain_links(html, BASE, HOST, exts)
    assert len(result) == 1
    assert "https://example.com/page.html" in result


def test_filters_non_content_paths() -> None:
    html = _html("/login", "/about", "/admin/dashboard", "/wp-admin")
    result = extract_same_domain_links(html, BASE, HOST, DEFAULT_EXTS)
    assert len(result) == 1
    assert "https://example.com/about" in result


def test_resolves_relative_urls() -> None:
    html = _html("../other", "sub/page")
    result = extract_same_domain_links(html, BASE, HOST, DEFAULT_EXTS)
    assert "https://example.com/other" in result
    assert "https://example.com/sub/page" in result
