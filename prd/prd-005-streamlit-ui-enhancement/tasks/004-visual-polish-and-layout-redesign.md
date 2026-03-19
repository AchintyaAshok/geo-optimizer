---
parent_prd: ../prd-005-streamlit-ui-enhancement/prd.md
prd_name: "PRD 005: Streamlit UI Enhancement"
prd_id: 005
task_id: 004
created: 2026-03-18
state: pending
---

# Task 004: Visual polish and layout redesign

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

Polish the Streamlit UI to feel professional and demo-ready. Add custom CSS for card containers, progress indicators, score visualizations, and consistent layout hierarchy. The page should look intentional, not like a default Streamlit app.

## Inputs

- Tasks 002-003 complete (functional cards, timeline)
- Streamlit CSS injection via `st.markdown(unsafe_allow_html=True)`

## Outputs

- Custom CSS stylesheet injected into the app
- Refined layout with proper visual hierarchy
- Score visualization (progress bar or metric display)
- Consistent spacing, typography, and color usage

## Steps

1. Add custom CSS via `st.markdown` at top of app:
   - Card containers with subtle borders and rounded corners
   - Stage progress bar with colored segments (green=done, blue=active, gray=pending)
   - Score display styling
2. Redesign the input section:
   - Use `st.columns` for URL input + button proportions
   - Add subtle header/description styling
3. Polish crawl cards:
   - Hostname as bold header, metadata as caption
   - Score as `st.metric` with delta or `st.progress`
   - Score breakdown as a row of small metrics
4. Polish history table:
   - Status column with colored badges (completed=green, failed=red, queued=gray)
5. Add page config: favicon, page title already set
6. Test across light/dark Streamlit themes
7. Visual review with Playwright screenshot

## Done Criteria

- [ ] Cards have visible borders/containers, not floating elements
- [ ] Stage progress is visually distinct (color-coded states)
- [ ] Score displayed as a visual element, not raw JSON
- [ ] Layout uses columns effectively — no wasted horizontal space
- [ ] Page looks professional in both light and dark themes
- [ ] `make check` passes

## Notes

Keep CSS minimal and maintainable. Use Streamlit's built-in theming CSS variables where possible (`--primary-color`, etc.).
