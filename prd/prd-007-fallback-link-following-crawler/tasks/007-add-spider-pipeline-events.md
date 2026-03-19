---
parent_prd: ../prd-007-fallback-link-following-crawler/prd.md
prd_name: "PRD 007: Fallback Link-Following Crawler"
prd_id: 007
task_id: 007
created: 2026-03-19
state: pending
---

# Task 007: Add spider pipeline events

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

Add structured pipeline event emissions throughout both spider phases so that every scan step, link decision, and indexing result is recorded via `repo.create_event()` and visible through the existing events API and Streamlit UI.

## Inputs

- `app/indexer/spider.py` from Task 004 (Phase 1 BFS scan)
- `app/indexer/discovery.py` from Task 006 (Phase 2 subtask dispatch)
- `app/indexer/page_indexer.py` from Task 005 (index_page)
- Existing `repo.create_event()` interface from `adapters/storage.py`
- PRD pipeline events tables (Phase 1 and Phase 2 event definitions)

## Outputs

- Phase 1 events emitted from `spider.py`: `spider.scan_started`, `spider.page_scanned`, `spider.link_skipped`, `spider.scan_completed`
- Phase 2 events emitted from `discovery.py` / `page_indexer.py`: `spider.index_started`, `spider.page_indexed`, `spider.page_index_failed`, `spider.index_completed`
- All events include the metadata fields specified in the PRD
- Events visible in `GET /api/v1/crawls/{run_id}/events` and Streamlit UI

## Steps

1. In `app/indexer/spider.py`, add event emissions:
   - `spider.scan_started` at the beginning of `spider_scan()` with `seed_url`, `max_depth`, `max_scan_pages`
   - `spider.page_scanned` after each page is fetched with `url`, `depth`, `links_found`, `inlink_score`
   - `spider.scan_completed` at the end with `pages_scanned`, `unique_links_found`, `duration`
2. In `app/indexer/link_filter.py`, add event emission for `spider.link_skipped` with `url`, `reason` (extension_filtered, non_content_path) — accept an optional event callback to avoid tight coupling
3. In `app/indexer/discovery.py` (`_spider_strategy`), add:
   - `spider.index_started` before dispatching subtasks with `pages_to_index`, `strategy`
   - `spider.index_completed` after all subtasks finish with `pages_indexed`, `pages_failed`, `duration`
4. In `app/indexer/page_indexer.py`, add:
   - `spider.page_indexed` on success with `url`, `provenance`, `title`, `title_confidence`
   - `spider.page_index_failed` on failure with `url`, `error`, `status_code`
5. Write tests verifying events are emitted:
   - Unit test: mock `repo.create_event` and run spider_scan, verify Phase 1 events are emitted in correct order
   - Unit test: mock page_indexer, verify Phase 2 events are emitted
   - Integration test: run a full spider crawl, query `/api/v1/crawls/{id}/events`, verify spider events appear
6. Run `make check`

## Done Criteria

- [ ] All 8 spider event types are emitted at the correct points per the PRD
- [ ] Each event includes the metadata fields specified in the PRD tables
- [ ] Events are created via `repo.create_event()` and persisted to the database
- [ ] Events appear in `GET /api/v1/crawls/{run_id}/events` response
- [ ] Events render in the Streamlit UI's "Live Events" feed and "All events" dataframe
- [ ] Unit tests verify event emission order and metadata
- [ ] `make check` passes

## Notes

_Any additional context or decisions made during execution._
