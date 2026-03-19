---
parent_prd: ../prd-007-fallback-link-following-crawler/prd.md
prd_name: "PRD 007: Fallback Link-Following Crawler"
prd_id: 007
task_id: 006
created: 2026-03-19
state: pending
---

# Task 006: Wire spider into discovery strategy

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

Replace the current `_fallback_seed_strategy` (tier 4 in discovery) with the spider. When tiers 1-3 (llms probe, robots hints, sitemap) find no URLs, the spider runs a BFS scan and dispatches `crawllmer.index_page` subtasks for the top-priority pages, feeding results into the existing extraction pipeline.

## Inputs

- `app/indexer/discovery.py` containing the discovery strategy chain (post-Task 001)
- `app/indexer/spider.py` from Task 004 (spider_scan)
- `app/indexer/tasks.py` from Task 005 (crawllmer.index_page task)
- Spider config settings from Task 002 (spider_max_index_pages)
- Celery app instance from `app/indexer/app.py`

## Outputs

- Modified `app/indexer/discovery.py` with `_spider_strategy` replacing `_fallback_seed_strategy`
- Spider scan runs Phase 1, then dispatches `crawllmer.index_page` subtasks for the top N URLs (Phase 2)
- Subtask results are awaited and fed back into the pipeline
- End-to-end test demonstrating the full flow with a site that has no llms.txt/sitemap

## Steps

1. In `app/indexer/discovery.py`, replace `_fallback_seed_strategy` with `_spider_strategy(context, requester, settings)`:
   - Call `spider_scan(seed_url, settings.spider_max_depth, settings.spider_max_scan_pages, settings.spider_timeout_per_page, include_extensions)`
   - Take the top `settings.spider_max_index_pages` URLs from the ranked results
   - Dispatch each as a `crawllmer.index_page` subtask via `celery_app.send_task("crawllmer.index_page", kwargs={...})`
   - Await all subtask results with a timeout
   - Return the collected `ExtractedPage` results to the pipeline
2. Update the `discover_urls` function to call `_spider_strategy` as tier 4 instead of `_fallback_seed_strategy`
3. Write an end-to-end test in `tests/integration/test_spider_discovery.py`:
   - Mock a site with no llms.txt, no robots.txt, no sitemap.xml — just HTML pages with links
   - Submit a crawl via the discovery pipeline
   - Verify the spider tier is invoked
   - Verify multiple pages are discovered and indexed (>1 page in output)
4. Run `make check`

## Done Criteria

- [ ] `_fallback_seed_strategy` is replaced by `_spider_strategy` in discovery.py
- [ ] Spider runs only when tiers 1-3 find no URLs
- [ ] Spider Phase 1 (scan) produces a ranked URL list
- [ ] Spider Phase 2 dispatches `crawllmer.index_page` subtasks and awaits results
- [ ] Results feed into the existing extraction pipeline
- [ ] End-to-end test with a site lacking llms.txt/sitemap produces >1 page in output
- [ ] Existing discovery tiers 1-3 remain unaffected
- [ ] `make check` passes

## Notes

_Any additional context or decisions made during execution._
