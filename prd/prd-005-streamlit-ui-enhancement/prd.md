# PRD 005: Streamlit UI Enhancement

## Overview

The current Streamlit UI is functional but minimal — a single form, a JSON dump, and a flat history table. For the assignment demo and presentation, the UI needs to feel like a polished product that communicates what's happening during a crawl. This PRD addresses four gaps:

1. **No visibility into crawl progress** — the user sees a spinner until completion, with no indication of which pipeline stage is executing.
2. **No processing queue** — if multiple URLs are submitted, there's no list of in-flight crawls.
3. **No event timeline** — after completion, there's no audit trail of what happened during the crawl.
4. **Visual polish** — the current UI is default Streamlit with no branding or layout hierarchy.

## Linked Tickets

| Ticket | Title | Status |
|--------|-------|--------|
| - | - | - |

## Measures of Success

- [ ] User can submit a URL and immediately see it appear in a "Processing" queue
- [ ] Each queued crawl shows its current pipeline stage with a visual progress indicator
- [ ] Clicking/expanding a crawl reveals an event timeline (stage transitions with timestamps)
- [ ] Completed crawls show score, generated llms.txt preview, and download button
- [ ] Failed crawls show error details inline
- [ ] The page has clear visual hierarchy, branding, and doesn't look like a Streamlit default

## Low Effort Version

Scope: Streamlit-only changes (no backend modifications). Use existing `repo` methods and polling.

### Layout

```
┌─────────────────────────────────────────────────┐
│  crawllmer                                       │
│  Generate llms.txt for any website               │
├─────────────────────────────────────────────────┤
│  [ URL input          ] [Crawl]                  │
├─────────────────────────────────────────────────┤
│  ▼ Active Crawls                                 │
│  ┌───────────────────────────────────────┐       │
│  │ nextjs.org    ██████░░░░ Extraction   │       │
│  │ queued 12s ago                        │       │
│  └───────────────────────────────────────┘       │
│  ┌───────────────────────────────────────┐       │
│  │ nuxt.com      ██████████ Completed ✓  │       │
│  │ score: 0.89 · 32 pages · 5.1s        │       │
│  │ ▸ View timeline  ▸ Download llms.txt  │       │
│  └───────────────────────────────────────┘       │
├─────────────────────────────────────────────────┤
│  Recent History (table)                          │
└─────────────────────────────────────────────────┘
```

### Components

**1. URL Input (existing, minor restyle)**
- Keep the form, add `st.columns` for better proportions
- Validate URL format before submission (show inline error)

**2. Active Crawls Panel**
- After submitting, store `run_id` in `st.session_state` list
- Poll `repo.get_run(run_id)` on a `time.sleep(1)` loop with `st.rerun()`
- For each active run, render a card using `st.container` + `st.columns`:
  - Hostname, elapsed time since `created_at`
  - Pipeline stage indicator: 5 stages as a step bar (discovery → extraction → canonicalization → scoring → generation)
  - Current stage highlighted, completed stages checked
- Use the run's `WorkItem` records to determine the current stage

**3. Event Timeline (expandable per run)**
- Query `repo.list_work_items(run_id)` to get all work items with their stages, states, and timestamps
- Render inside `st.expander("View timeline")`:
  - Each stage as a row: stage name, state icon (✓/✗/⏳), duration, error if failed
- No backend changes needed — work items already track stage + state + timestamps

**4. Completed Run Details**
- Score with visual bar (`st.progress`)
- Score breakdown as small metrics row (`st.metric` columns)
- llms.txt preview in `st.code` with download button
- Error details in `st.error` for failed runs

**5. Visual Polish**
- Custom CSS via `st.markdown(unsafe_allow_html=True)` for:
  - Card-like containers with borders/shadows
  - Stage progress bar styling
  - Consistent color palette (use Streamlit theme vars)
- Add `st.caption` for timestamps in relative format ("12s ago")
- Use `st.columns` for layout density

### Data Flow

```
Submit URL
  → pipeline.enqueue_run(url)
  → store run_id in session_state.active_runs
  → st.rerun()

Poll loop (on each rerun):
  → for run_id in session_state.active_runs:
      → run = repo.get_run(run_id)
      → items = repo.list_work_items(run_id)  # need this method
      → render card with stage progress
      → if terminal state: move to completed list
  → time.sleep(1)
  → st.rerun() if any still active
```

### Backend Requirements

One new repository method needed:

```python
# In CrawlRepository (ports.py) and SqliteCrawlRepository (storage.py)
def list_work_items(self, run_id: UUID) -> list[WorkItem]:
    """Return all work items for a run, ordered by created_at."""
```

This is a simple query on the existing `WorkItemRecord` table — no schema changes.

### Master-Detail Panel Layout (added post-approval)

Replace the per-card expander design with a two-column master-detail layout:

```
┌──────────────────────────┬──────────────────────────────┐
│  [ URL input     ] [Go]  │                              │
│                          │  Detail Panel                │
│  ▼ Active                │  ─────────────────────────── │
│  ┃ vite.dev  ▶ Extr  3s │  vite.dev                    │
│                          │  Status: running             │
│  ▼ Completed             │  ✓ Discovery     226ms      │
│  ┃ nuxt.com  ✓  89%     │  ▶ Extraction    ...        │
│  ┃ nextjs.org ✓  41%    │  ○ Canonicalize  --         │
│                          │  ○ Scoring       --         │
│  ▼ History               │  ○ Generation    --         │
│  ┃ example.com ✗ failed │                              │
│                          │  [llms.txt: 42 lines, 1.2K] │
│                          │  ┌─────────────────────┐    │
│                          │  │ # llms.txt for ...  │    │
│                          │  │ - [Page](url): ...  │    │
│                          │  │ ...                  │    │
│                          │  │ (truncated, 1000+)   │    │
│                          │  └─────────────────────┘    │
│                          │  [Download llms.txt]         │
└──────────────────────────┴──────────────────────────────┘
```

**Left column (master list, ~40% width):**
- URL input + submit button at top
- Compact run rows: hostname, status badge, score (if done), elapsed time
- Click a row → populates the detail panel on the right
- Grouped: Active (polling), Completed this session, History
- Selected row visually highlighted

**Right column (detail panel, ~60% width):**
- Appears when a run is selected (empty state: "Select a crawl to view details")
- Shows: stage progress bar, score metrics with tooltips, timeline, llms.txt
- llms.txt handling:
  - Show word count and line count as a header: "42 lines · 1,247 words"
  - If ≤1000 lines: show full content in collapsible `st.expander`
  - If >1000 lines: show first 1000 lines, then "... truncated. Download to see full file."
  - Always show download button
- Auto-selects newly submitted runs

**Session state additions:**
- `selected_run`: UUID string of the currently viewed run (None = empty state)
- Auto-set to new run on submit, persists on rerun cycles

## High Effort Version

Everything in Low Effort, plus:

- **WebSocket/SSE streaming** for real-time updates (replace polling)
- **Multi-tab layout** — separate tabs for "New Crawl", "Queue", "History"
- **Diff view** comparing generated llms.txt with the site's actual llms.txt (if it exists)
- **Run comparison** — side-by-side view of two crawl results
- **Dark/light theme toggle**

## Possible Future Extensions

- Batch URL upload (paste list or upload CSV)
- Scheduled re-crawls with change detection
- Email/webhook notifications on crawl completion
- Shareable run result links
- Export history as JSON/CSV

## Amendment: Replace Session-State Tracking with Database Polling

**Date**: 2026-03-19
**Problem**: The Streamlit app tracks active and completed runs in `st.session_state` (`active_runs`, `completed_runs`). This means runs queued directly through the FastAPI API never appear in the UI — the frontend only shows crawls it initiated itself.

**Root cause**: The data flow currently is:
1. User clicks "Crawl" → `pipeline.enqueue_run()` → `run_id` added to `st.session_state.active_runs`
2. Poll loop only iterates over `session_state.active_runs`
3. Runs created via `POST /api/v1/crawls` bypass this session state entirely

**Proposed changes to `streamlit_app.py`**:

### 1. Remove session-state run tracking
- Delete `st.session_state.active_runs` and `st.session_state.completed_runs`
- Keep only `st.session_state.selected_run` (UI selection state — this is appropriate for session state)

### 2. Derive run lists from the database
- Query `repo.list_runs(limit=50)` once per render cycle
- Split into three groups by status:
  - **Active**: runs where `status in (queued, running)` — shown under "ACTIVE" heading
  - **Recent**: runs where `status in (completed, failed)` and `created_at` within last 24 hours — shown under "RECENT" heading
  - **History**: remaining older completed/failed runs — shown under "HISTORY" heading

### 3. Auto-refresh based on database state
- Set `has_active = True` if any run in the database has `status in (queued, running)`
- This means the UI auto-refreshes for API-initiated crawls too

### 4. Auto-select newly created runs
- After `pipeline.enqueue_run()`, still set `st.session_state.selected_run` to the new run ID
- This is the only session-state write remaining — just for navigating to the new run

### 5. Configurable refresh rate
- Add `ui_refresh_seconds: int = 2` to `Settings` in `core/config.py`
- Env var: `CRAWLLMER_UI_REFRESH_SECONDS` (default 2s)
- Use this instead of the hardcoded `time.sleep(1)` in the auto-refresh loop

### What stays the same
- All rendering functions (`_render_detail_panel`, `_render_stage_bar`, `_render_timeline`, `_render_events`, `_render_llms_txt`) — unchanged
- Helper functions (`_elapsed`, `_duration`, `_stage_state`, `_current_stage_label`) — unchanged
- CSS, navbar, page config — unchanged
- Direct `repo` access (no HTTP client needed since Streamlit and API share the same database)

### Files changed
- `src/crawllmer/core/config.py` — add `ui_refresh_seconds` setting
- `.env.example` — document new env var
- `src/crawllmer/app/web/streamlit_app.py` — session state section + run classification section + left column + auto-refresh

## Approval State

| Status | Date | Notes |
|--------|------|-------|
| Draft | 2026-03-18 | Initial draft |
| Approved | 2026-03-18 | Low effort scope approved |
| Amendment | 2026-03-19 | Replace session-state tracking with DB polling — pending review |
