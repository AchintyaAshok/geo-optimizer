---
parent_prd: ../prd-007-fallback-link-following-crawler/prd.md
prd_name: "PRD 007: Fallback Link-Following Crawler"
prd_id: 007
task_id: 005
created: 2026-03-19
state: pending
---

# Task 005: Implement page indexer task

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

Extract the single-page fetch-and-extract logic from the current extraction pipeline into a standalone `page_indexer.py` module and register it as a `crawllmer.index_page` Celery task in `app/indexer/tasks.py`, so it can be called independently by the spider or any other discovery strategy.

## Inputs

- Existing extraction logic in `app/indexer/page_indexer.py` (post-Task 001 — the `_extract_title`, `_extract_description` functions moved from workers.py)
- `app/indexer/tasks.py` (Celery task definitions)
- `app/indexer/app.py` (Celery app instance)
- Domain models: `ExtractedPage` from `domain/models.py`
- Storage adapter: `repo.upsert_extracted_pages` from `adapters/storage.py`

## Outputs

- `src/crawllmer/app/indexer/page_indexer.py` with a callable `index_page(url, run_id, provenance)` function that fetches a URL, extracts title and description, and persists an `ExtractedPage`
- `crawllmer.index_page` task registered in `app/indexer/tasks.py` that delegates to `index_page()`
- Unit test verifying the task can be called and returns an `ExtractedPage`

## Steps

1. In `src/crawllmer/app/indexer/page_indexer.py`, ensure there is a standalone function `index_page(url, run_id, provenance)` that:
   - Fetches the page HTML via httpx
   - Calls `_extract_title(html)` and `_extract_description(html)` (already in this module post-Task 001)
   - Constructs an `ExtractedPage` model instance
   - Persists it via `repo.upsert_extracted_pages([page])`
   - Returns the `ExtractedPage`
2. In `src/crawllmer/app/indexer/tasks.py`, register the Celery task:
   - `@app.task(name="crawllmer.index_page")`
   - Task function calls `index_page(url, run_id, provenance)` from page_indexer
3. Write a unit test in `tests/unit/test_page_indexer.py`:
   - Mock HTTP response and storage repo
   - Call `index_page()` directly and verify it returns a valid `ExtractedPage` with correct url, run_id, and provenance
   - Verify `repo.upsert_extracted_pages` was called with the page
4. Run `make check`

## Done Criteria

- [ ] `index_page(url, run_id, provenance)` function exists in `page_indexer.py` and works standalone
- [ ] `crawllmer.index_page` Celery task is registered in `tasks.py`
- [ ] Task delegates to `index_page()` and returns an `ExtractedPage`
- [ ] Unit test passes with mocked HTTP and storage
- [ ] `make check` passes

## Notes

_Any additional context or decisions made during execution._
