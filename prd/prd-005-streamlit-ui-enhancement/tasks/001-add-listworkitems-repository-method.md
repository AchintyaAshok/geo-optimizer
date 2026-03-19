---
parent_prd: ../prd-005-streamlit-ui-enhancement/prd.md
prd_name: "PRD 005: Streamlit UI Enhancement"
prd_id: 005
task_id: 001
created: 2026-03-18
state: pending
---

# Task 001: Add list_work_items repository method

## Metadata

| Field | Value |
|-------|-------|
| PRD | [PRD 005: Streamlit UI Enhancement](../prd.md) |
| Created | 2026-03-18 |
| State | pending |

## Changelog

| Date | Change |
|------|--------|
| 2026-03-18 | Task created |

## Objective

Add `list_work_items(run_id)` to the repository interface and SQLite implementation so the UI can query pipeline stage progress for a given run.

## Inputs

- `domain/ports.py` — `CrawlRepository` abstract class
- `adapters/storage.py` — `SqliteCrawlRepository` implementation
- Existing `WorkItemRecord` table (already has `run_id` index)

## Outputs

- New abstract method on `CrawlRepository`
- Working SQLite implementation returning `list[WorkItem]` ordered by `created_at`
- Unit test validating the method

## Steps

1. Add `list_work_items(self, run_id: UUID) -> list[WorkItem]` to `CrawlRepository` in `ports.py`
2. Implement in `SqliteCrawlRepository` — query `WorkItemRecord` where `run_id` matches, order by `created_at`
3. Add test in `tests/unit/` verifying it returns work items in order
4. Run `make check`

## Done Criteria

- [ ] `CrawlRepository.list_work_items` exists as abstract method
- [ ] `SqliteCrawlRepository.list_work_items` returns correct results
- [ ] Test passes
- [ ] `make check` passes

## Notes

No schema changes — `WorkItemRecord` already has a `run_id` indexed column.
