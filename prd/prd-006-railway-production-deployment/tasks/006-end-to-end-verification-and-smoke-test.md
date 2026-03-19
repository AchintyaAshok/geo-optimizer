---
parent_prd: ../prd-006-railway-production-deployment/prd.md
prd_name: "PRD 006: Railway Production Deployment"
prd_id: 006
task_id: 006
created: 2026-03-19
state: pending
---

# Task 006: End-to-end verification and smoke test

## Metadata

| Field | Value |
|-------|-------|
| PRD | [PRD 006: Railway Production Deployment](../prd.md) |
| Created | 2026-03-19 |
| State | pending |

## Changelog

| Date | Change |
|------|--------|
| 2026-03-19 | Task created |

## Objective

Verify the full deployed stack works end-to-end: submit a URL, receive a generated llms.txt, confirm data persists in Postgres, confirm traces appear in Jaeger.

## Inputs

- Deployed Railway project with all services from Tasks 004-005
- Public URLs for API, UI, and Jaeger

## Outputs

- Verified working deployment
- Updated `guides/deployment.md` with Railway-specific instructions
- Updated `README.md` with live deployment URL
- Screenshots or evidence for submission

## Steps

1. **API smoke test:**
   - `curl <railway-api-url>/health` → 200
   - `curl -X POST <railway-api-url>/api/v1/crawls -H 'Content-Type: application/json' -d '{"url": "https://example.com"}'` → returns `run_id`
   - `curl <railway-api-url>/api/v1/crawls/<run_id>` → status eventually `completed`
   - `curl <railway-api-url>/api/v1/crawls/<run_id>/llms.txt` → returns generated llms.txt content
2. **UI smoke test:**
   - Open Streamlit URL in browser
   - Submit a URL
   - Verify crawl completes and llms.txt is downloadable
3. **Persistence check:**
   - `curl <railway-api-url>/api/v1/history` → shows the run from step 1
   - Restart API service → history still shows the run (Postgres persistence)
4. **Observability check:**
   - Open Jaeger UI URL
   - Find traces for `crawllmer-api` and `crawllmer-worker`
   - Verify pipeline span structure: `crawl_pipeline.run` → `crawl_pipeline.stage.*`
5. **Update documentation:**
   - Add Railway deployment section to `guides/deployment.md`
   - Add live URL to `README.md`
6. **Capture evidence:**
   - Screenshots of Streamlit UI with completed crawl
   - Screenshot of Jaeger trace view
   - Screenshot of API response

## Done Criteria

- [ ] API `/health` returns 200 from public URL
- [ ] Full crawl completes via API (enqueue → process → download llms.txt)
- [ ] Full crawl completes via Streamlit UI
- [ ] Data persists across service restarts
- [ ] Traces visible in Jaeger with correct span hierarchy
- [ ] `guides/deployment.md` updated with Railway instructions
- [ ] `README.md` includes live deployment URL
- [ ] Evidence captured (screenshots or demo)

## Notes

This is the final validation task — all PRD measures of success should be met after this task completes.
