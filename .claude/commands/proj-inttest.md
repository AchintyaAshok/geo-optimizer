Run the integration test suite against a live crawllmer instance using Playwright. This command executes the test matrix defined in `docs/integration-test-plan.md`.

## Prerequisites

Before running tests, ensure the dev environment is up:

```bash
make stop
make clean-db
make run-dev
```

Wait for all three services (API on :8000, UI on :8501, worker) to be ready. Verify by navigating Playwright to `http://localhost:8501` and confirming the navbar renders with "crawllmer".

## Test Execution

Work through the test matrix in order. For each site:

### Step 1: Submit the crawl

1. Navigate Playwright to `http://localhost:8501`
2. Type the test URL into the "Website URL" input field
3. Click the "Crawl" button
4. Confirm the run appears in the "ACTIVE" section of the left panel

### Step 2: Wait for completion

1. Poll the page — the detail panel on the right should auto-update via `st.rerun()`
2. Wait until the status badge changes from `running` to `completed` or `failed`
3. Timeout limits: Category A = 120s, Category B = 60s, Category C = 10s
4. If the crawl times out, record it as a failure and move to the next test

### Step 3: Verify the result

Check the detail panel for each of these criteria and record pass/fail:

**For ALL categories:**
- [ ] Status badge shows expected state (`completed` for A/C, `completed` or `failed` for B)
- [ ] Pipeline timeline shows all 5 stages with durations
- [ ] Events section is populated

**For Category A (has llms.txt) — additional checks:**
- [ ] Score > 0%
- [ ] "View llms.txt" expander is present
- [ ] llms.txt starts with `#` (H1 heading)
- [ ] llms.txt contains `>` blockquote with "structured overview" prompt text
- [ ] llms.txt contains `**Generated**:`, `**Pages crawled**:`, `**Links discovered**:`
- [ ] llms.txt contains at least one `##` section heading
- [ ] llms.txt contains at least one `- [title](url)` link entry
- [ ] No `## Raw` section exists in the output

**For Category B (sitemap only) — additional checks:**
- [ ] If completed: llms.txt has at least one entry
- [ ] Events show sitemap or robots discovery (not direct llms)

**For Category C (nothing) — additional checks:**
- [ ] Only 1 page crawled (visible in blockquote metadata)
- [ ] Generated llms.txt contains exactly one `## Home` section

### Step 4: Record the result

For each test, output a row in this format:

```
| ID | URL | Status | Score | Pages | Sections | Strategy | Duration | Issues |
```

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

1. **Start with A1** (`nextjs.org`). If this fails, stop — the environment is broken.
2. Run remaining A sites (A2-A7). A2 (nuxt.com) is slow; start it and move to A3-A7 while waiting if possible.
3. Run B sites (B1-B4). These test the sitemap fallback path.
4. Run C sites (C1-C2). These test the final fallback.
5. Compile the results table and report any failures.

## Reporting

After all tests complete, output:

1. **Summary table** with all results
2. **Pass rate** per category (e.g., "Category A: 7/7, Category B: 3/4, Category C: 2/2")
3. **Failures** with details on what went wrong
4. **Observations** on scoring patterns, timing, or unexpected behavior

If any Category A test fails, flag it as a **blocker**. Category B/C failures are informational unless the crawl crashes entirely.
