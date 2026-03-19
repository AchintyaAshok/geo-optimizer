---
parent_prd: ../prd-005-streamlit-ui-enhancement/prd.md
prd_name: "PRD 005: Streamlit UI Enhancement"
prd_id: 005
task_id: 003
created: 2026-03-18
state: pending
---

# Task 003: Event timeline expander per run

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

Add an expandable event timeline to each crawl card, showing the sequence of pipeline stages with timestamps, durations, states, and error details. This gives users audit-trail visibility into what happened during a crawl.

## Inputs

- Task 002 complete (crawl cards rendering)
- `repo.list_work_items(run_id)` returns `WorkItem` list with stage, state, created_at, updated_at, last_error

## Outputs

- `render_timeline(work_items)` function in `streamlit_app.py`
- Expandable section in each crawl card showing stage-by-stage breakdown

## Steps

1. Add `st.expander("View timeline")` inside each crawl card
2. Build `render_timeline(work_items)`:
   - Group work items by stage (there may be duplicates — discovery initial + per-stage items)
   - For each stage: show icon (✓ completed, ✗ failed, ⏳ processing, ○ queued), stage name, duration (updated_at - created_at), error if failed
   - Use `st.columns` for aligned rows
3. For completed runs: timeline is static and fully populated
4. For active runs: timeline updates on each poll cycle
5. For failed runs: highlight the failed stage with `st.error` inline

## Done Criteria

- [ ] Each crawl card has a "View timeline" expander
- [ ] Timeline shows all pipeline stages with correct state icons
- [ ] Duration displayed per stage
- [ ] Failed stages show error message
- [ ] Timeline updates live during active crawls
- [ ] `make check` passes

## Notes

Work items include both the initial discovery item (created by `enqueue_run`) and stage-specific items (created by `_run_stage`). May need to filter or deduplicate.
