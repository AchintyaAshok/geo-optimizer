# Processing Pipeline

crawllmer processes every URL through a five-stage pipeline. Each stage is tracked as a work item with state transitions (`queued → processing → completed/failed`) and an event audit trail.

```
URL → Discovery → Extraction → Canonicalization → Scoring → Generation → llms.txt
```

## Stage 1: Discovery

**Goal**: Find all relevant pages on the target website.

Discovery runs a hierarchical strategy chain — each strategy is tried in order, and we stop as soon as we have URLs:

| Priority | Strategy | Source | What It Does |
|----------|----------|--------|--------------|
| 1 | Direct llms probe | `/llms.txt` | Fetch the site's existing `llms.txt` and extract markdown links |
| 2 | Robots hints | `robots.txt` | Parse `llms:` and `sitemap:` directives |
| 3 | Sitemap traversal | `/sitemap.xml` | Recursively parse sitemap index and urlset XML |
| 4 | Fallback seed | Target URL itself | Use the input URL as the only candidate |

**Why hierarchical?** If a site already publishes `/llms.txt`, that's the most authoritative source. Falling through to sitemaps and robots provides broad coverage for sites that don't.

The sitemap parser handles both sitemap index files (containing `<sitemap>` entries pointing to other sitemaps) and urlset files (containing `<url>` entries). It follows the [Sitemaps protocol](https://www.sitemaps.org/protocol.html) namespace.

All discovered URLs are deduplicated by URL string, preserving the first discovery source for provenance tracking.

**Implementation**: `src/crawllmer/app/indexer/workers.py` — `discover_urls()`, `_direct_llms_strategy()`, `_robots_hints_strategy()`, `_sitemap_strategy()`, `_fallback_seed_strategy()`

## Stage 2: Extraction

**Goal**: Fetch each discovered page and extract title + description metadata.

For every URL from discovery, the extractor:
1. Sends a `GET` request (respecting ETag/Last-Modified validators for conditional requests)
2. Parses the HTML `<head>` section with BeautifulSoup
3. Extracts title and description using a priority cascade:

### Title Extraction (by confidence)

| Source | Confidence | Selector |
|--------|------------|----------|
| `<title>` tag | 1.0 | `soup.head.title.string` |
| Open Graph | 0.8 | `<meta property="og:title">` |
| Twitter Card | 0.75 | `<meta property="twitter:title">` |
| JSON-LD | 0.6 | `<script type="application/ld+json">` → `headline` |

### Description Extraction (by confidence)

| Source | Confidence | Selector |
|--------|------------|----------|
| Meta description | 1.0 | `<meta name="description">` |
| Open Graph | 0.8 | `<meta property="og:description">` |
| Twitter Card | 0.75 | `<meta property="twitter:description">` |
| JSON-LD | 0.6 | `<script type="application/ld+json">` → `description` |

The first match in each cascade wins. Every extraction records its source and confidence score in a provenance dict, which flows through the rest of the pipeline.

**Conditional requests**: If a previous crawl stored ETag or Last-Modified validators for a URL, the extractor sends `If-None-Match` / `If-Modified-Since` headers. A `304 Not Modified` response skips re-extraction.

**Implementation**: `src/crawllmer/app/indexer/workers.py` — `extract_metadata()`, `_extract_title()`, `_extract_description()`

## Stage 3: Canonicalization

**Goal**: Normalize URLs and deduplicate extracted pages.

URL normalization:
- Lowercases scheme and netloc
- Strips trailing slashes (except root `/`)
- Produces a canonical form: `scheme://netloc/path`

When multiple extracted pages map to the same canonical URL, the one with the highest combined confidence (title + description) wins.

**Implementation**: `src/crawllmer/app/indexer/workers.py` — `canonicalize_and_dedup()`, `_normalize_url()`

## Stage 4: Scoring

**Goal**: Compute a quality score for the extraction results.

The score has three components:

| Component | Weight | Formula |
|-----------|--------|---------|
| **Coverage** | 40% | `(pages_with_title / total + pages_with_description / total) / 2` |
| **Confidence** | 40% | Average of `(title_confidence + description_confidence) / 2` across all pages |
| **Redundancy** | 20% | `unique_urls / total_pages` (higher = less duplication = better) |

**Total score** = `(coverage × 0.4) + (confidence × 0.4) + (redundancy × 0.2)`

All values are rounded to 4 decimal places. A perfect score of 1.0 means every page has a title and description extracted from high-confidence sources with no duplicates.

The score breakdown is stored on the `CrawlRun` and returned in API responses, so users can understand _why_ a particular crawl scored the way it did.

**Implementation**: `src/crawllmer/app/indexer/workers.py` — `score_pages()`

## Stage 5: Generation

**Goal**: Produce a spec-compliant `llms.txt` document.

The generator builds an `LlmsTxtDocument` Pydantic model from the canonicalized pages and serializes it to markdown:

```markdown
# llms.txt for example.com

- [Page Title](https://example.com/page): Description of the page
- [Another Page](https://example.com/other): Another description
```

**Deterministic output**: Entries are sorted by URL, so the same input always produces the same output. This makes the output diffable and reproducible.

If a page has no title, the URL itself is used as the link text. Descriptions are optional — entries without descriptions omit the `: description` suffix.

The generated text is stored as a `GenerationArtifact` and served via `GET /api/v1/crawls/{run_id}/llms.txt`.

**Implementation**: `src/crawllmer/app/indexer/workers.py` — `generate_llms_txt()`; `src/crawllmer/domain/models.py` — `LlmsTxtDocument.to_text()`

## Pipeline Orchestration

The `CrawlPipeline` class (`src/crawllmer/core/orchestrator.py`) coordinates all five stages:

1. `enqueue_run(url)` — Validates the URL, creates a `CrawlRun` and initial `WorkItem`, publishes a discovery task to the queue
2. `process_run(run_id)` — Loads the run, builds the stage plan, and executes each stage sequentially

Each stage creates a work item, transitions it through `queued → processing → completed/failed`, and logs the outcome via OpenTelemetry spans. If any stage fails, the run is marked as `failed` with error details in the `notes` dict.

### Supporting Infrastructure

- **RetryPolicy** (`retry.py`): Wraps stage execution with exponential backoff (2 retries, 50ms base delay, 2× multiplier)
- **HostRateLimiter** (`scheduler.py`): Per-host request throttling (10ms delay, 50ms adaptive penalty after throttling)
- **PipelineTelemetry** (`observability.py`): OpenTelemetry metrics (counters, histograms) and span creation for each stage
