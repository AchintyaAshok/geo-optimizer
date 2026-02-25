from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from crawllmer.domain.models import ExtractedPage


def discover_urls(
    target_url: str, client: httpx.Client | None = None
) -> list[tuple[str, str]]:
    parsed = urlparse(target_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    found: list[tuple[str, str]] = []
    requester = client or httpx.Client(timeout=8.0)

    llms = requester.get(f"{base}/llms.txt")
    if llms.status_code == 200:
        for line in llms.text.splitlines():
            match = re.search(r"\[[^\]]+\]\(([^\)]+)\)", line)
            if match:
                found.append((urljoin(base, match.group(1)), "llms"))

    robots = requester.get(f"{base}/robots.txt")
    if robots.status_code == 200:
        for line in robots.text.splitlines():
            lower = line.lower()
            if lower.startswith("sitemap:"):
                found.extend(parse_sitemap(requester, line.split(":", 1)[1].strip()))
            if lower.startswith("llms:"):
                found.append((urljoin(base, line.split(":", 1)[1].strip()), "robots"))

    if not found:
        sitemap = requester.get(f"{base}/sitemap.xml")
        if sitemap.status_code == 200:
            found.extend(parse_sitemap(requester, f"{base}/sitemap.xml"))

    if not found:
        found.append((target_url, "crawl"))

    deduped: dict[str, str] = {}
    for url, source in found:
        deduped.setdefault(url, source)
    return list(deduped.items())


def parse_sitemap(client: httpx.Client, sitemap_url: str) -> list[tuple[str, str]]:
    response = client.get(sitemap_url)
    if response.status_code != 200:
        return []

    root = ET.fromstring(response.text)
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    discovered: list[tuple[str, str]] = []

    for child in root.findall(f"{namespace}sitemap"):
        loc = child.find(f"{namespace}loc")
        if loc is not None and loc.text:
            discovered.extend(parse_sitemap(client, loc.text.strip()))

    for child in root.findall(f"{namespace}url"):
        loc = child.find(f"{namespace}loc")
        if loc is not None and loc.text:
            discovered.append((loc.text.strip(), "sitemap"))

    return discovered


def extract_metadata(
    run_id,
    urls: list[tuple[str, str]],
    validators: dict[str, tuple[str | None, str | None]],
    client: httpx.Client | None = None,
) -> tuple[list[ExtractedPage], dict[str, tuple[str | None, str | None]]]:
    requester = client or httpx.Client(timeout=8.0)
    pages: list[ExtractedPage] = []
    new_validators: dict[str, tuple[str | None, str | None]] = {}

    for url, provenance in urls:
        headers = {}
        etag, last_modified = validators.get(url, (None, None))
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        response = requester.get(url, headers=headers)
        if response.status_code == 304:
            continue
        if response.status_code != 200:
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


def generate_llms_txt(hostname: str, pages: list[ExtractedPage]) -> str:
    lines = [f"# llms.txt for {hostname}", ""]
    for page in sorted(pages, key=lambda p: p.url):
        title = page.title or page.url
        entry = f"- [{title}]({page.url})"
        if page.description:
            entry += f": {page.description}"
        lines.append(entry)
    return "\n".join(lines).strip() + "\n"
