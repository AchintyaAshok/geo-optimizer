---
parent_prd: ../prd-005-streamlit-ui-enhancement/prd.md
prd_name: "PRD 005: Streamlit UI Enhancement"
prd_id: 005
task_id: 002
created: 2026-03-18
state: pending
---

# Task 002: Active crawls panel with stage progress

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

Replace the current "submit and spin" UX with an active crawls panel. After submitting a URL, the run appears as a card showing hostname, elapsed time, and a 5-stage visual progress bar. Multiple concurrent crawls are supported via `st.session_state`.

## Inputs

- Task 001 complete (`list_work_items` available)
- Current `streamlit_app.py`
- Pipeline stages: discovery → extraction → canonicalization → scoring → generation

## Outputs

- Rewritten `streamlit_app.py` with session-state-driven crawl tracking
- Active crawls panel rendering one card per in-flight run
- Auto-polling with `st.rerun()` while any run is active

## Steps

1. Add `st.session_state.active_runs` (list of run_id UUIDs) initialization
2. On form submit: call `pipeline.enqueue_run(url)`, append run_id to session state, `st.rerun()`
3. Build `render_crawl_card(run, work_items)` function:
   - Show hostname and elapsed time (`datetime.now() - run.created_at`)
   - Render 5-stage progress bar: completed stages get ✓, current stage highlighted, pending stages dimmed
   - Determine current stage from work_items (latest non-completed stage)
4. In the main page flow, iterate `active_runs` and render cards
5. For terminal runs (completed/failed): show summary inline (score, error) and move to history
6. If any runs still active: `time.sleep(1)` + `st.rerun()`
7. Test manually with `make run-dev`

## Done Criteria

- [ ] Submitting a URL immediately shows a card in the active crawls panel
- [ ] Card displays hostname, elapsed time, and current pipeline stage
- [ ] Stage progress bar visually distinguishes completed/active/pending stages
- [ ] Multiple concurrent crawls render as separate cards
- [ ] Completed/failed runs transition to showing results inline
- [ ] `make check` passes

## Notes

Stage progress can use `st.columns(5)` with conditional styling or `st.progress` with stage labels.
