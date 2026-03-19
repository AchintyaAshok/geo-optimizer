---
parent_prd: ../prd-007-fallback-link-following-crawler/prd.md
prd_name: "PRD 007: Fallback Link-Following Crawler"
prd_id: 007
task_id: 008
created: 2026-03-19
state: pending
---

# Task 008: Integration test with Category C sites

## Metadata

| Field | Value |
|-------|-------|
| PRD | [PRD 007: Fallback Link-Following Crawler](../prd.md) |
| Created | 2026-03-19 |
| State | pending |

## Changelog

| Date | Change |
|------|--------|
| 2026-03-19 | Task created |

## Objective

Verify the spider works end-to-end with real Category C sites (example.com and httpbin.org) — sites that have no llms.txt, no sitemap, and no robots.txt hints — producing multi-page llms.txt output with spider events visible in the API.

## Inputs

- Fully wired spider from Tasks 001-007
- Running FastAPI + Celery worker (via `make run-dev` or test fixtures)
- `GET /api/v1/crawls` endpoint for submitting crawls
- `GET /api/v1/crawls/{run_id}/events` endpoint for querying events
- example.com and httpbin.org as test targets

## Outputs

- Integration tests in `tests/integration/test_spider_e2e.py`
- Tests validate multi-page output, llms.txt content, and spider events for both sites

## Steps

1. Create `tests/integration/test_spider_e2e.py`
2. Write a test for example.com:
   - Submit a crawl via `POST /api/v1/crawls` with url=`https://example.com`
   - Poll for completion (or use test fixture that runs synchronously)
   - Verify the crawl completed successfully
   - Verify output contains >1 page (spider discovered additional pages beyond root)
   - Verify the generated llms.txt has multiple sections
   - Query `/api/v1/crawls/{run_id}/events` and verify spider events are present (spider.scan_started, spider.scan_completed, spider.index_started, spider.index_completed)
3. Write a test for httpbin.org:
   - Submit a crawl via `POST /api/v1/crawls` with url=`https://httpbin.org`
   - Verify the crawl completed successfully
   - Verify output contains >1 page
   - Verify the generated llms.txt has multiple sections
   - Verify events show spider strategy was used
4. Add appropriate markers (e.g., `@pytest.mark.integration`, `@pytest.mark.network`) so these tests can be skipped in CI without network access
5. Run the integration tests and verify both pass

## Done Criteria

- [ ] Integration test exists for example.com crawl
- [ ] Integration test exists for httpbin.org crawl
- [ ] Both sites produce >1 page in output (spider discovers pages beyond root)
- [ ] Generated llms.txt contains multiple sections for both sites
- [ ] Events endpoint shows spider strategy events (scan_started, scan_completed, index_started, index_completed)
- [ ] Tests are marked as integration/network tests for selective execution
- [ ] Tests pass when run with network access

## Notes

_Any additional context or decisions made during execution._
