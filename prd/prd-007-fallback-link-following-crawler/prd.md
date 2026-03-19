# PRD 007: Fallback Link-Following Crawler

## Overview

The current fallback discovery strategy (tier 4) returns only the root URL when a site has no `/llms.txt`, no `robots.txt` hints, and no `/sitemap.xml`. The project requirement says *"develop a crawler that traverses the website to identify key pages"* — but we don't traverse. This PRD adds a bounded, importance-aware link-following spider as the final fallback strategy.

### Problem

- Category C test sites (example.com, httpbin.org) produce exactly 1 page in the output
- Any site without structured discovery aids gets a useless single-entry llms.txt
- The requirement explicitly says "traverses the website"

### Inspiration

Web crawling literature describes several strategies for URL prioritisation ([BFS vs DFS comparison](https://medium.com/@seilylook95/understanding-dfs-vs-bfs-in-web-crawling-a-practical-perspective-8129c93bfb02), [crawling algorithms](https://www.academia.edu/29657302/Web_Crawling_Algorithms_A_Comparative_Study)):

- **BFS** discovers broadly — good for finding the site's structure, but slow for deep content
- **DFS** goes deep — fast initial results but misses sibling pages
- **Best-first / priority queue** — assigns importance scores and crawls the most promising URLs first
- **In-link counting** — pages linked from many other internal pages are likely more important

Our approach: **BFS with a priority queue**, bounded by max depth and max pages. Pages with more inbound links from already-visited pages get crawled first.

## Measures of Success

- [ ] Category C sites (no llms.txt, no sitemap) produce >1 page in the output
- [ ] httpbin.org crawl discovers at least the main API documentation pages
- [ ] Depth and page limits are respected — never exceeds configured bounds
- [ ] Spidering completes within a reasonable time (< 30s for a small site)
- [ ] Large sites don't run forever — hard limits prevent unbounded crawling
- [ ] Existing discovery strategies (tiers 1-3) are unaffected

## Low Effort Version

### Algorithm: Bounded BFS with In-Link Priority

```
spider(seed_url, max_depth=3, max_pages=50):
    visited = set()
    queue = PriorityQueue()  # lower score = higher priority
    inlink_count = Counter()  # url → number of internal pages linking to it

    queue.push(seed_url, priority=0, depth=0)

    while queue and len(visited) < max_pages:
        url, depth = queue.pop()

        if url in visited or depth > max_depth:
            continue

        visited.add(url)
        page_html = fetch(url)

        # Extract all same-domain <a href> links
        links = extract_links(page_html, same_domain_only=True)

        for link in links:
            if link not in visited:
                inlink_count[link] += 1
                # Priority: lower depth + more inlinks = crawl sooner
                priority = depth - inlink_count[link]
                queue.push(link, priority, depth + 1)

    return [(url, "crawl") for url in visited]
```

### Key Parameters

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `max_depth` | 3 | Maximum link hops from the seed URL |
| `max_pages` | 50 | Maximum total pages to visit |
| `same_domain` | True | Only follow links within the seed's hostname |
| `timeout_per_page` | 5s | HTTP fetch timeout per page |

### Integration with Existing Discovery

The spider runs as **tier 4** in the existing discovery hierarchy, replacing the current `_fallback_seed_strategy`:

```python
def discover_urls(target_url, ...):
    # Tier 1: direct llms probe
    # Tier 2: robots hints
    # (if no URLs found)
    # Tier 3: sitemap
    # (if still no URLs found)
    # Tier 4: spider (replaces single-seed fallback)
    outputs.append(_spider_strategy(context, requester))
```

The spider returns `(url, DiscoverySource.crawl)` tuples, same as the current fallback. No changes to downstream stages (extraction, canonicalization, scoring, generation).

### Link Extraction

Parse `<a href="...">` from the page HTML:
- Resolve relative URLs against the page's base URL
- Filter to same hostname only (no external links)
- Strip fragments (`#section`)
- Skip non-content URLs: `.css`, `.js`, `.png`, `.jpg`, `.svg`, `.pdf`, `.zip`, etc.
- Skip common non-content paths: `/login`, `/signup`, `/cart`, `/admin`, `/wp-admin`

### Where It Lives

New function `_spider_strategy(context, requester)` in `src/crawllmer/application/workers.py`, alongside the existing discovery strategies. Uses the same `StrategyOutput` return type.

### Rate Limiting

The spider respects the existing `HostRateLimiter` — no change needed. Each fetch goes through the same httpx client with its configured timeout.

## High Effort Version

Everything in Low Effort, plus:

### Async Worker Task for Spidering

Break spidering into its own Celery task so it runs asynchronously:

```
Enqueue crawl → discovery task (tiers 1-3)
    → if no URLs found: enqueue spider task
    → spider task crawls pages, emits discovered URLs
    → extraction task picks up from there
```

This would require:
- A new Celery task `crawllmer.spider`
- The orchestrator to chain tasks: discovery → (optional spider) → extraction → ...
- Work items for spider progress tracking
- Events for spider page visits

**Note**: This is the right architecture for production but adds complexity. The synchronous low-effort version is sufficient for the assignment scope. Any complex task (not just spidering) could eventually be broken out — discovery tiers 1-3 are fast enough (<1s) that they don't warrant async treatment.

### Shared "Index Page" Primitive

When the spider discovers a URL, the work it needs done is identical to what happens when a sitemap or llms.txt discovers a URL: fetch the page, extract metadata, store it. This suggests a shared primitive:

```
index_page(url, run_id, provenance) → ExtractedPage
```

Both the spider and the sitemap/llms discovery paths feed URLs into this same unit of work. In the current synchronous model, this is just a function call inside `extract_metadata`. In the async model, it becomes a shared Celery task that both the spider worker and the discovery worker can enqueue:

```
crawllmer.index_page  ← called by spider for each discovered link
                      ← called by extraction stage for each sitemap/llms URL
```

This decomposition is not needed for the low-effort version (the existing `extract_metadata` loop already handles it), but it's the natural seam for async task decomposition later. The key insight: **page indexing is the atomic unit of work, regardless of how the URL was discovered.**

### Additional High-Effort Features

- **Robots.txt crawl-delay** — respect `Crawl-delay` directive
- **Concurrent fetching** — fetch N pages in parallel within the spider (asyncio or thread pool)
- **Content-based importance** — score pages by content length, heading density, or keyword relevance
- **Incremental spidering** — resume from where a previous crawl left off
- **JavaScript rendering** — use Playwright for SPA sites that render content client-side

## Possible Future Extensions

- **Async task decomposition for all stages** — any stage that takes >5s could become its own Celery task. Current candidates: spidering (tier 4), extraction (large sites). Discovery tiers 1-3 and canonicalization/scoring/generation are fast enough to stay synchronous. This should be noted in the design decisions doc.
- **Adaptive depth** — increase max_depth if the first N pages all have similar content (suggests the real content is deeper)
- **Domain-specific crawl profiles** — different settings for documentation sites vs blogs vs e-commerce
- **Crawl budget management** — per-domain rate limits and total bandwidth budgets

## Design Notes

### Why BFS over DFS

DFS would dive deep into one branch (e.g., `/docs/api/v1/users/create/validation/rules/...`) before seeing sibling pages. For llms.txt generation, we want breadth — the top-level pages (`/docs`, `/blog`, `/about`, `/api`) are more important than deeply nested sub-pages. BFS naturally discovers the site's structure first.

### Why In-Link Counting

A page linked from many other pages within the same site is likely important (similar to PageRank intuition). For example, a site's `/docs` page is probably linked from the homepage, the navbar, the footer, and multiple blog posts. By counting how many visited pages link to a URL, we naturally surface the most connected pages.

### Why Not Just Increase max_pages

Without importance scoring, increasing max_pages would just crawl pages in whatever order they're discovered — potentially filling the budget with footer links or pagination pages. The priority queue ensures we spend our page budget on the most promising URLs.

### Async Task Decomposition — General Principle

The current pipeline runs all 5 stages synchronously in one Celery task. This works because most stages are fast (<1s each, except extraction for large sites). Spidering could take 10-30s for a moderately sized site, making it a candidate for async decomposition. However, the complexity cost of task chaining and progress tracking is significant. The recommendation is:

- **Low effort**: Keep spidering synchronous within the discovery stage
- **High effort**: Break spidering into its own Celery task
- **Future**: Any stage exceeding a time threshold could be promoted to its own task

This principle should be documented in `docs/design_decisions.md`.

## Approval State

| Status | Date | Notes |
|--------|------|-------|
| Draft | 2026-03-19 | Initial draft |
