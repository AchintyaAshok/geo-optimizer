#!/usr/bin/env python3
"""Submit integration test URLs to the crawllmer API.

Reads site definitions from resources/inttest-sites.json and submits
crawls for the specified category (or all categories).

Usage:
    uv run python scripts/submit-inttest.py          # all categories
    uv run python scripts/submit-inttest.py a         # Category A only
    uv run python scripts/submit-inttest.py b c       # Categories B and C
    uv run python scripts/submit-inttest.py --list    # list sites without submitting
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = "http://localhost:8000"
SITES_FILE = Path(__file__).resolve().parent.parent / "resources" / "inttest-sites.json"


def load_sites() -> dict:
    with open(SITES_FILE) as f:
        return json.load(f)


def submit(url: str, site_id: str) -> str:
    """Submit a crawl and return the status."""
    req = urllib.request.Request(
        f"{API_BASE}/api/v1/crawls",
        data=json.dumps({"url": url}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return f"{site_id}  {url}  -> {data.get('status', '?')}"
    except (urllib.error.URLError, TimeoutError) as exc:
        return f"{site_id}  {url}  -> FAILED ({exc})"


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    list_only = "--list" in sys.argv

    sites_data = load_sites()
    categories = sites_data["categories"]

    # Default to all categories
    selected = args if args else list(categories.keys())

    for cat_key in selected:
        if cat_key not in categories:
            print(f"Unknown category: {cat_key}")
            print(f"Available: {', '.join(categories.keys())}")
            sys.exit(1)

        cat = categories[cat_key]
        print(f"=== Category {cat_key.upper()}: {cat['name']} ===")

        for site in cat["sites"]:
            if list_only:
                print(f"  {site['id']}  {site['url']}  ({site['notes']})")
            else:
                print(submit(site["url"], site["id"]))

    if not list_only:
        print()
        print("All submitted. Check status with: make crawl-status")
        print("Verbose:                          make crawl-status ARGS=\"-v\"")


if __name__ == "__main__":
    main()
