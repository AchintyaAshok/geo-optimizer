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

Our approach: **Two-phase BFS**. Phase 1 scans the site to build a link graph and compute page importance. Phase 2 indexes the top-priority pages via the task queue.

## Measures of Success

- [ ] Category C sites (no llms.txt, no sitemap) produce >1 page in the output
- [ ] httpbin.org crawl discovers at least the main documentation pages
- [ ] Depth and page limits are respected — never exceeds configured bounds
- [ ] Spidering completes within a reasonable time (< 30s for a small site)
- [ ] Large sites don't run forever — hard limits prevent unbounded crawling
- [ ] Existing discovery strategies (tiers 1-3) are unaffected
- [ ] Pipeline events reconstruct the full crawl strategy (what was tried, what was skipped, why)
- [ ] Crawl strategy is auditable via the `/api/v1/crawls/{run_id}/events` endpoint

## Low Effort Version

### Two-Phase Architecture

The spider is two distinct phases:

**Phase 1: BFS Scan** — Build a link graph and compute page importance scores. This phase fetches pages lightly (just enough to extract `<a href>` links), does NOT extract metadata, and builds an in-link count map.

**Phase 2: Index** — Take the top-N pages by importance score and feed them into the existing extraction pipeline as `crawllmer.index_page` subtasks via the Celery task queue.

```
Phase 1: BFS Scan (synchronous within spider)
    seed_url → fetch → extract <a> links → enqueue children → repeat
    Output: priority-ordered list of (url, inlink_score, depth)

Phase 2: Page Indexing (async via task queue)
    For each URL in priority order:
        enqueue crawllmer.index_page(url, run_id, provenance="crawl")
    Await all subtask results
```

### Phase 1: BFS Scan Algorithm

```python
def spider_scan(seed_url, max_depth, max_scan_pages):
    visited = set()
    queue = deque([(seed_url, 0)])  # (url, depth)
    inlink_count = Counter()        # url → inbound link count
    link_graph = {}                 # url → [outbound urls]

    while queue and len(visited) < max_scan_pages:
        url, depth = queue.popleft()

        if url in visited or depth > max_depth:
            continue

        visited.add(url)
        html = fetch(url)

        # BeautifulSoup for link extraction (not regex)
        links = extract_same_domain_links(html, seed_hostname)

        # Emit pipeline event for this scan step
        emit_event("spider.page_scanned", {
            "url": url,
            "depth": depth,
            "links_found": len(links),
        })

        link_graph[url] = links
        for link in links:
            if link not in visited:
                inlink_count[link] += 1
                queue.append((link, depth + 1))

    # Rank by inlink count (descending), break ties by depth (ascending)
    ranked = sorted(
        visited,
        key=lambda u: (-inlink_count[u], ...depth...),
    )
    return ranked
```

### Phase 2: Page Indexing via Task Queue

The spider produces a priority-ordered list of URLs. These are dispatched as `crawllmer.index_page` subtasks on the Celery task queue:

```python
# In the orchestrator, after spider scan completes:
subtasks = []
for url in ranked_urls[:max_index_pages]:
    task = celery_app.send_task(
        "crawllmer.index_page",
        kwargs={"url": url, "run_id": str(run_id), "provenance": "crawl"},
    )
    subtasks.append(task)

# Await all results
results = [t.get(timeout=timeout) for t in subtasks]
```

The `crawllmer.index_page` task is **shared** — it can be called by the spider, but it's also the same unit of work that the extraction stage does for sitemap/llms-discovered URLs. This is the natural decomposition point.

```python
@celery_app.task(name="crawllmer.index_page")
def index_page_task(url, run_id, provenance):
    """Fetch a single page, extract metadata, store it."""
    # Same logic currently inside extract_metadata's loop
    html = fetch(url)
    title, title_source, title_conf = _extract_title(html)
    desc, desc_source, desc_conf = _extract_description(html)
    page = ExtractedPage(run_id=run_id, url=url, ...)
    repo.upsert_extracted_pages([page])

    emit_event("spider.page_indexed", {
        "url": url, "provenance": provenance,
        "title": title, "title_confidence": title_conf,
    })
    return page
```

### Configuration

All bounds are config-driven via `src/crawllmer/config.py` (pydantic-settings):

| Setting | Env Var | Default | Purpose |
|---------|---------|---------|---------|
| `spider_max_depth` | `CRAWLLMER_SPIDER_MAX_DEPTH` | `3` | Maximum link hops from seed |
| `spider_max_scan_pages` | `CRAWLLMER_SPIDER_MAX_SCAN_PAGES` | `100` | Max pages to scan in Phase 1 |
| `spider_max_index_pages` | `CRAWLLMER_SPIDER_MAX_INDEX_PAGES` | `50` | Max pages to index in Phase 2 |
| `spider_include_extensions` | `CRAWLLMER_SPIDER_INCLUDE_EXTENSIONS` | `.html,.htm,.txt,.md,` | Page extensions to index (empty = extensionless paths) |
| `spider_timeout_per_page` | `CRAWLLMER_SPIDER_TIMEOUT_PER_PAGE` | `5` | HTTP timeout per page (seconds) |

**Extension filtering**: The `spider_include_extensions` list defines which URL extensions are indexable. The trailing comma represents extensionless paths (e.g., `/docs/intro`), which are common for modern web frameworks. URLs with extensions not in this list (`.css`, `.js`, `.png`, `.pdf`, `.zip`, etc.) are skipped during Phase 1 scanning and logged as `spider.link_skipped` events with `reason=extension_filtered`.

### Link Extraction

Uses **BeautifulSoup** (already a dependency) — not regex:

```python
def extract_same_domain_links(html, hostname):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for tag in soup.find_all("a", href=True):
        url = urljoin(base_url, tag["href"])
        parsed = urlparse(url)

        # Same domain only
        if parsed.netloc != hostname:
            continue

        # Strip fragments
        url = url.split("#")[0]

        # Check extension filter
        path = parsed.path
        ext = Path(path).suffix.lower()
        if ext and ext not in include_extensions:
            emit_event("spider.link_skipped", {
                "url": url, "reason": "extension_filtered", "ext": ext,
            })
            continue

        # Skip common non-content paths
        if any(seg in NON_CONTENT_PATHS for seg in path.split("/")):
            emit_event("spider.link_skipped", {
                "url": url, "reason": "non_content_path",
            })
            continue

        links.append(url)
    return links
```

`NON_CONTENT_PATHS`: `login`, `signup`, `cart`, `admin`, `wp-admin`, `wp-login`, `logout`, `register`

### Pipeline Events

The spider emits structured events throughout both phases using the existing pipeline events architecture:

**Phase 1 events:**

| Event Name | System | Metadata | When |
|------------|--------|----------|------|
| `spider.scan_started` | `spider` | `seed_url`, `max_depth`, `max_scan_pages` | Scan begins |
| `spider.page_scanned` | `spider` | `url`, `depth`, `links_found`, `inlink_score` | Each page scanned |
| `spider.link_skipped` | `spider` | `url`, `reason` (`extension_filtered`, `non_content_path`, `depth_exceeded`) | Link filtered out |
| `spider.scan_completed` | `spider` | `pages_scanned`, `unique_links_found`, `duration` | Scan finishes |

**Phase 2 events:**

| Event Name | System | Metadata | When |
|------------|--------|----------|------|
| `spider.index_started` | `spider` | `pages_to_index`, `strategy` | Indexing begins |
| `spider.page_indexed` | `spider` | `url`, `provenance`, `title`, `title_confidence` | Each page indexed |
| `spider.page_index_failed` | `spider` | `url`, `error`, `status_code` | Page fetch/parse failed |
| `spider.index_completed` | `spider` | `pages_indexed`, `pages_failed`, `duration` | Indexing finishes |

All events go through `repo.create_event()` and are visible via `GET /api/v1/crawls/{run_id}/events`.

### Strategy Audit

The existing `/api/v1/crawls/{run_id}/events` endpoint already exposes all pipeline events. With the spider events above, a consumer can reconstruct:

1. Which discovery strategy was selected (llms/robots/sitemap/spider)
2. For spider: every page scanned, every link followed/skipped, and why
3. The priority ranking that determined which pages were indexed
4. Each page's indexing result (success/failure, extracted metadata)

No new API endpoint needed — the events endpoint serves this purpose. The Streamlit UI's "Live Events" feed and "All events" dataframe already render these.

### Integration with Existing Discovery

The spider runs as **tier 4** in the existing discovery hierarchy, replacing `_fallback_seed_strategy`:

```python
def discover_urls(target_url, ...):
    # Tier 1: direct llms probe
    # Tier 2: robots hints
    # (if no URLs found)
    # Tier 3: sitemap
    # (if still no URLs found)
    # Tier 4: spider scan + index (replaces single-seed fallback)
    spider_result = _spider_strategy(context, requester, settings)
    outputs.append(spider_result)
```

### Where It Lives — Module Separation

The codebase has three distinct applications that share core modules:

- **API** (`api/`) — FastAPI REST endpoints
- **Web App** (`web/`) — Streamlit UI
- **Indexer** (`indexer/`) — Crawler, spider, page indexing tasks

Currently `web/` conflates API and UI. This PRD introduces `indexer/` and also proposes separating API from UI in a future refactor.

```
src/crawllmer/
├── core/              # Shared: errors, observability, config
├── domain/            # Shared: models, ports
├── application/       # Shared: orchestrator, queueing, retry, scheduler
├── adapters/          # Shared: storage
├── app/               # Application layer — three distinct runtimes
│   ├── api/           # REST API (FastAPI)
│   │   ├── __init__.py
│   │   └── routes.py     # All API endpoints (move from web/app.py)
│   ├── web/           # Streamlit UI
│   │   ├── __init__.py
│   │   ├── streamlit_app.py
│   │   └── runtime.py
│   └── indexer/       # Crawler, spider, task processing
│       ├── __init__.py
│       ├── app.py            # Celery app instance + config (importable, no side effects)
│       ├── tasks.py          # Task definitions (@app.task: process_run, index_page, spider)
│       ├── spider.py         # BFS scan, link graph building
│       ├── page_indexer.py   # Single-page fetch + extract (shared primitive)
│       ├── link_filter.py    # Extension filtering, non-content path detection
│       └── __main__.py       # Worker entrypoint (python -m crawllmer.app.indexer)
├── config.py          # Shared config (add spider settings)
└── main.py            # FastAPI entrypoint (imports app.api)
```

The three applications live under `app/` as sibling packages. Each has its own entrypoint and can be deployed independently, but they share `core/`, `domain/`, `application/`, and `adapters/`.

The indexer follows [Celery's recommended project layout](https://docs.celeryq.dev/en/stable/getting-started/next-steps.html#proj-layout):
- **`app.py`** — Celery app instance. Importable from anywhere (e.g., `queueing.py` uses `send_task`) without triggering a worker start.
- **`tasks.py`** — Task functions decorated with `@app.task`. Current `process_run_task` plus new `index_page` and `spider` tasks.
- **`__main__.py`** — Worker bootstrap (`python -m crawllmer.app.indexer` starts the worker).

Beyond the spider, other indexing concerns that belong here:
- **Content extraction** — `_extract_title`, `_extract_description` (currently in `application/workers.py`) are indexing logic, not orchestration
- **Markdown extraction** — future `.md` content parser for sites like vite.dev
- **Freshness/validators** — ETag/If-Modified-Since conditional request logic

| Component | Location |
|-----------|----------|
| API routes | `src/crawllmer/app/api/routes.py` |
| Streamlit UI | `src/crawllmer/app/web/streamlit_app.py` |
| Celery app instance | `src/crawllmer/app/indexer/app.py` |
| Task definitions | `src/crawllmer/app/indexer/tasks.py` |
| Worker entrypoint | `src/crawllmer/app/indexer/__main__.py` |
| BFS scan + link graph | `src/crawllmer/app/indexer/spider.py` |
| Single-page indexing | `src/crawllmer/app/indexer/page_indexer.py` |
| Link extraction + filtering | `src/crawllmer/app/indexer/link_filter.py` |
| Spider config settings | `src/crawllmer/config.py` (new fields) |

**Migration path**:
- `web/app.py` → `app/api/routes.py`
- `web/streamlit_app.py` + `web/runtime.py` → `app/web/`
- `celery_app.py` → `app/indexer/app.py` (Celery instance) + `app/indexer/tasks.py` (task functions)
- `worker.py` → `app/indexer/__main__.py`
- `application/workers.py` extraction functions → `app/indexer/page_indexer.py`
- `main.py` updates to import from `app.api`
- Makefile `run-worker` → `python -m crawllmer.app.indexer`

## High Effort Version

Everything in Low Effort, plus:

### Concurrent Phase 1 Scanning

Use `httpx.AsyncClient` with asyncio to scan multiple pages in parallel during Phase 1. Current sequential scanning is O(n) round trips — concurrent scanning with a semaphore of 5-10 would reduce wall time significantly for larger sites.

### Full Async Pipeline Decomposition

Promote any pipeline stage that exceeds a time threshold to its own Celery task. The general principle:

- **Synchronous** (current, keep as-is): Discovery tiers 1-3, canonicalization, scoring, generation — all complete in <1s
- **Async** (this PRD): Spider scan + page indexing — 10-30s for moderate sites
- **Future candidates**: Extraction for large sites (1000+ URLs from sitemaps) — already takes 60s+ for nuxt.com/clerk.com

Task chaining in Celery:
```python
chain(
    discover_task.s(run_id),        # tiers 1-3, fast
    spider_task.s(run_id),          # tier 4 if needed
    extract_task.s(run_id),         # bulk extraction
    canonicalize_task.s(run_id),    # fast
    score_task.s(run_id),           # fast
    generate_task.s(run_id),        # fast
).apply_async()
```

### Additional Features (deferred)

- **Robots.txt crawl-delay** — respect `Crawl-delay` directive
- **Content-based importance** — score pages by content length, heading density, or keyword relevance
- **Incremental spidering** — resume from where a previous crawl left off
- **JavaScript rendering** — use Playwright for SPA sites that render client-side
- **Adaptive depth** — increase `max_depth` if the first N pages have similar content

## Possible Future Extensions

- **Domain-specific crawl profiles** — different settings for documentation sites vs blogs vs e-commerce
- **Crawl budget management** — per-domain rate limits and total bandwidth budgets
- **Shared index_page across all discovery** — refactor extraction stage to use the same `crawllmer.index_page` task for sitemap/llms-discovered URLs (not just spider URLs), unifying the extraction path

## Design Notes

### Why Two Phases

You need to scan before you can rank. If you index pages as you discover them (single pass), you can't prioritize — you'd index whatever BFS finds first, which might be footer links or pagination. The two-phase approach lets you build the full link graph, compute importance scores, and then spend your indexing budget on the most valuable pages.

### Why BFS over DFS

DFS would dive deep into one branch (e.g., `/docs/api/v1/users/create/validation/rules/...`) before seeing sibling pages. For llms.txt generation, we want breadth — the top-level pages (`/docs`, `/blog`, `/about`, `/api`) are more important than deeply nested sub-pages. BFS naturally discovers the site's structure first.

### Why In-Link Counting

A page linked from many other pages within the same site is likely important (similar to PageRank intuition). For example, a site's `/docs` page is probably linked from the homepage, the navbar, the footer, and multiple blog posts. By counting how many visited pages link to a URL, we naturally surface the most connected pages.

### Why Async via Task Queue

The spider can take 10-30s for a moderate site. Running this synchronously blocks the Celery worker for the entire duration. By breaking indexing into subtasks:
- Phase 1 (scan) runs in the spider task
- Phase 2 (index) fans out as individual `crawllmer.index_page` subtasks
- Multiple workers can process index tasks in parallel
- Each subtask emits its own pipeline events for auditability
- Celery already supports `task.get()` for awaiting subtask results

### Extension Filtering Rationale

Default include extensions: `.html`, `.htm`, `.txt`, `.md`, and extensionless paths.

Extensionless paths (e.g., `/docs/intro`, `/blog/my-post`) are included because most modern web frameworks (Next.js, Nuxt, FastAPI docs, Django) serve HTML at clean URLs without extensions. The empty string in the extension list handles this case.

Everything else (`.css`, `.js`, `.png`, `.jpg`, `.svg`, `.pdf`, `.zip`, `.xml`, `.json`, `.woff`, etc.) is excluded by default. These are assets/data files, not content pages. If a site serves meaningful content at unusual extensions, the user can override via `CRAWLLMER_SPIDER_INCLUDE_EXTENSIONS`.

### Auditability via Pipeline Events

Every decision the spider makes is recorded as a pipeline event:
- Why a link was followed or skipped
- What importance score each page received
- Which pages were selected for indexing and which were not
- Success/failure of each page index operation

This means `GET /api/v1/crawls/{run_id}/events` provides a complete audit trail. No new API endpoint is needed — the existing events endpoint and Streamlit UI already render these. A future enhancement could add a dedicated `/api/v1/crawls/{run_id}/strategy` endpoint that summarizes the discovery strategy in a structured format, but the raw events are sufficient for now.

## Approval State

| Status | Date | Notes |
|--------|------|-------|
| Draft | 2026-03-19 | Initial draft |
| Revised | 2026-03-19 | Incorporate feedback: two-phase architecture, async task queue, config-driven bounds, BeautifulSoup, pipeline events, extension filtering |
