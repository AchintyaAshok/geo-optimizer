# Integration Test Plan — Crawl & Generation

This document defines the test matrix for end-to-end integration testing of crawllmer's crawl pipeline and llms.txt generation.

The canonical list of test sites lives in [`resources/inttest-sites.json`](../resources/inttest-sites.json). Submit them with `make inttest` or list them with `make inttest-list`.

## Test Matrix

### Category A: Sites with llms.txt

These sites serve a valid `/llms.txt` file. The crawler should discover URLs from it, extract metadata, and generate a well-structured output.

| # | URL | Expected Discovery | Expected Sections | Notes |
|---|-----|-------------------|-------------------|-------|
| A1 | `https://nextjs.org` | Direct llms probe finds links to docs, blog, learn | Docs, Blog, Learn, Support Policy | Large site, versioned docs (14, 15, 16) |
| A2 | `https://nuxt.com` | Direct llms probe + sitemap via robots.txt | Docs, Blog, Learn | Very large (1000+ pages), has sitemap with versions |
| A3 | `https://vite.dev` | Direct llms probe finds .md links | Guide, Config, Changes, Plugins | Links to raw .md files — low extraction confidence |
| A4 | `https://clerk.com` | Direct llms probe | Docs, Changelog, Blog | Clean llms.txt with descriptions |
| A5 | `https://docs.retool.com` | Direct llms probe | Docs sections | Documentation-focused site |
| A6 | `https://uploadcare.com` | Direct llms probe | Docs, Blog | Has robots.txt with disallow directives |
| A7 | `https://mariadb.com` | Direct llms probe | Docs, Kb, Resources | Has robots.txt with LLMS.txt reference |

**Pass criteria for Category A**:
- Run completes with status `completed`
- Score > 0 (at least some metadata extracted)
- Generated llms.txt contains `#` H1 heading
- Generated llms.txt contains `>` blockquote with generation metadata
- Generated llms.txt contains at least one `## Section` heading
- Generated llms.txt contains at least one `- [title](url)` entry
- Pipeline timeline shows Discovery completed with duration < 5s
- Events log contains `stage.discovery` with `outcome=success`

### Category B: Sites with sitemap but NO llms.txt

These sites have no `/llms.txt` but serve a `/sitemap.xml`. The crawler should fall through the direct llms probe, find the sitemap via robots.txt or direct probe, and extract metadata from discovered pages.

| # | URL | Expected Discovery | Notes |
|---|-----|-------------------|-------|
| B1 | `https://docs.python.org` | Robots → sitemap (7 version entries) | Multi-language, small sitemap |
| B2 | `https://flask.palletsprojects.com` | Robots → sitemap (RTD auto-generated) | Read the Docs hosted, small |
| B3 | `https://expressjs.com` | Direct sitemap probe (no robots.txt) | Multi-language sitemap |
| B4 | `https://jquery.com` | Robots → sitemap (WordPress wp-sitemap.xml) | Sitemap index with child sitemaps |

**Pass criteria for Category B**:
- Run completes (status `completed` or `failed` with clear error)
- Discovery strategy is `sitemap` or `robots` (not `llms`)
- If completed: generated llms.txt has at least one entry
- Events log shows discovery strategy attempted sitemap

### Category C: Sites with neither llms.txt nor sitemap

These sites have no `/llms.txt` and no `/sitemap.xml`. The crawler should fall through to the fallback seed strategy (root URL only).

| # | URL | Expected Behavior | Notes |
|---|-----|-------------------|-------|
| C1 | `https://example.com` | Fallback seed → extracts root page only | IANA-maintained, minimal single page |
| C2 | `https://httpbin.org` | Fallback seed → extracts root page only | Developer utility, no sitemap |

**Pass criteria for Category C**:
- Run completes with status `completed`
- Only 1 page in the generated llms.txt (the root URL)
- Score may be low but should not be 0 if the page has a title
- Events log shows fallback seed strategy used

## Execution Notes

### Environment Setup

```bash
make stop          # Kill any running processes
make clean-db      # Remove stale databases
make run-dev       # Start API + UI + worker
```

Wait for all three services (API on :8000, UI on :8501, worker) to be ready before starting tests.

### Test Execution Order

Run tests in order: A1 first (known-good baseline), then remaining A sites, then B, then C. If A1 fails, the environment is broken — do not proceed.

### Timing

- Category A sites: allow up to 120s per crawl (large sites like nuxt.com can take 60-90s)
- Category B sites: allow up to 60s per crawl
- Category C sites: should complete in < 10s

### Observing Results

For each test, verify via the Streamlit UI at `http://localhost:8501`:
1. Submit the URL via the input field
2. Watch the active crawls panel for stage progression
3. After completion, check the detail panel for:
   - Status badge shows `completed` (or expected failure)
   - Score metrics are populated
   - llms.txt preview contains proper structure (H1, blockquote, H2 sections)
   - Pipeline timeline shows all 5 stages with durations
   - Events log shows discovery strategy and extraction details

### Recording Results

For each test, record:
- **Status**: completed / failed / timeout
- **Score**: overall score percentage
- **Pages crawled**: from the blockquote metadata
- **Sections generated**: list of H2 section names
- **Discovery strategy**: which strategy found URLs (llms / robots / sitemap / fallback)
- **Duration**: total pipeline time
- **Issues**: any unexpected behavior or errors
