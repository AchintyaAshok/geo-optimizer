from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import httpx

from crawllmer.app.indexer.page_indexer import index_page


def _mock_response(html: str, status: int = 200) -> httpx.Client:
    client = MagicMock(spec=httpx.Client)
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.text = html
    resp.headers = {}
    client.get = MagicMock(return_value=resp)
    return client


def test_index_page_extracts_title_and_description() -> None:
    html = """<html><head>
        <title>My Page</title>
        <meta name="description" content="A test page.">
    </head><body></body></html>"""

    run_id = uuid4()
    page = index_page("https://example.com", run_id, client=_mock_response(html))

    assert page is not None
    assert page.title == "My Page"
    assert page.description == "A test page."
    assert page.run_id == run_id
    assert page.provenance["discovery"] == "crawl"
    assert page.confidence["title"] == 1.0
    assert page.confidence["description"] == 1.0


def test_index_page_returns_none_on_404() -> None:
    page = index_page(
        "https://example.com",
        uuid4(),
        client=_mock_response("", status=404),
    )
    assert page is None


def test_index_page_returns_none_on_http_error() -> None:
    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(side_effect=httpx.ConnectError("connection refused"))
    page = index_page("https://example.com", uuid4(), client=client)
    assert page is None


def test_index_page_preserves_provenance() -> None:
    html = "<html><head><title>T</title></head></html>"
    page = index_page(
        "https://example.com",
        uuid4(),
        provenance="sitemap",
        client=_mock_response(html),
    )
    assert page is not None
    assert page.provenance["discovery"] == "sitemap"
