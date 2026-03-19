Run the integration test suite against a live crawllmer instance. This command executes the test matrix defined in `docs/integration-test-plan.md`.

## Prerequisites

Before running tests, ensure the dev environment is up:

```bash
make stop
make clean-db
make run-dev
```

Wait for all three services (API on :8000, UI on :8501, worker) to be ready. Verify with:

```bash
curl -s http://localhost:8000/health   # → {"status": "ok"}
```

## Test Execution

### Submitting crawls

Submit crawls via the API. For each test URL:

```bash
curl -s -X POST http://localhost:8000/api/v1/crawls \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://TARGET_URL"}'
```

This returns `{"run_id": "...", "status": "queued"}`. The worker picks it up automatically.

You can submit multiple crawls — they queue and process sequentially.

### Checking status

Use the helper script to check all runs at once:

```bash
make crawl-status              # summary table
make crawl-status ARGS="-v"    # with event detail per run
```

Or check a specific run:

```bash
python3 scripts/check-crawl-status.py <run-id>
python3 scripts/check-crawl-status.py <run-id> -v
```

The script exits with:
- `0` — all runs completed
- `1` — at least one run failed
- `2` — at least one run still in progress

### Checking results in detail

For detailed inspection of a completed run:

```bash
# Get run details (status, score, breakdown)
curl -s http://localhost:8000/api/v1/crawls/<run-id> | python3 -m json.tool

# Get the generated llms.txt
curl -s http://localhost:8000/api/v1/crawls/<run-id>/llms.txt

# Get event log
curl -s http://localhost:8000/api/v1/crawls/<run-id>/events | python3 -m json.tool
```

### Visual verification (Playwright)

For UI verification, use Playwright to navigate to `http://localhost:8501`:
1. Click a run in the left panel to see its detail view
2. Verify stage pills, score metrics, timeline, and llms.txt preview
3. Take a screenshot with `browser_take_screenshot` for the record

Only use Playwright for visual spot-checks — use the API for bulk status checking.

## Verification Criteria

### For ALL categories:
- [ ] Run completes (status `completed` or `failed` with clear error)
- [ ] Events are populated (`/api/v1/crawls/<id>/events` returns entries)

### For Category A (has llms.txt):
- [ ] Score > 0%
- [ ] llms.txt starts with `#` (H1 heading)
- [ ] llms.txt contains `>` blockquote with "structured overview" text
- [ ] llms.txt contains `**Generated**:`, `**Pages crawled**:`, `**Links discovered**:`
- [ ] llms.txt contains at least one `##` section heading
- [ ] llms.txt contains at least one `- [title](url)` link entry
- [ ] No `## Raw` section in the output

### For Category B (sitemap only):
- [ ] If completed: llms.txt has at least one entry
- [ ] Events show sitemap or robots discovery strategy

### For Category C (nothing):
- [ ] Pages crawled = 1 (visible in blockquote)
- [ ] Only `## Home` section (fallback seed)

## Test Matrix

Reference: `docs/integration-test-plan.md`

### Category A: Sites with llms.txt

| ID | URL | Key Expectation |
|----|-----|----------------|
| A1 | `https://nextjs.org` | Baseline — must pass. Docs, Blog, Learn sections. |
| A2 | `https://nuxt.com` | Large site (1000+ pages). Long extraction. |
| A3 | `https://vite.dev` | Links to .md files — low confidence expected. |
| A4 | `https://clerk.com` | Clean llms.txt with good descriptions. |
| A5 | `https://docs.retool.com` | Documentation-focused. |
| A6 | `https://uploadcare.com` | Has robots.txt disallow directives. |
| A7 | `https://mariadb.com` | Has LLMS.txt reference in robots.txt. |

### Category B: Sites with sitemap, no llms.txt

| ID | URL | Key Expectation |
|----|-----|----------------|
| B1 | `https://docs.python.org` | Small sitemap (7 entries), multi-language. |
| B2 | `https://flask.palletsprojects.com` | Read the Docs hosted, small. |
| B3 | `https://expressjs.com` | No robots.txt, direct sitemap probe. |
| B4 | `https://jquery.com` | WordPress sitemap index. |

### Category C: No llms.txt, no sitemap

| ID | URL | Key Expectation |
|----|-----|----------------|
| C1 | `https://example.com` | Single page, fallback seed only. |
| C2 | `https://httpbin.org` | Single page, fallback seed only. |

## Execution Strategy

1. **Submit A1 first** (`nextjs.org`). Check status. If it fails, stop — environment is broken.
2. Submit remaining A sites, B sites, and C sites via the API.
3. Wait 2-3 minutes, then run `make crawl-status ARGS="-v"` to check all at once.
4. For any still running, wait and re-check.
5. For completed runs, spot-check llms.txt output via the API.
6. Optionally use Playwright for 1-2 visual spot-checks.

## Reporting

After all tests complete, output:

1. **Summary table** from `make crawl-status`
2. **Pass rate** per category
3. **Failures** with error details
4. **Observations** on scoring, timing, or unexpected behavior

Category A failures are **blockers**. Category B/C failures are informational unless the crawl crashes entirely.
