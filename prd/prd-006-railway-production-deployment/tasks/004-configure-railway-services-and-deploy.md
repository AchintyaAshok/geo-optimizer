---
parent_prd: ../prd-006-railway-production-deployment/prd.md
prd_name: "PRD 006: Railway Production Deployment"
prd_id: 006
task_id: 004
created: 2026-03-19
state: pending
---

# Task 004: Configure Railway services and deploy

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

Create a Railway project with all application services, configure environment variables, and deploy the app from GitHub.

## Inputs

- Working Dockerfile from Task 003
- Railway account with Hobby plan
- GitHub repo access

## Outputs

- Railway project with 5 services: API, Worker, UI, Redis (plugin), PostgreSQL (plugin)
- Public URLs for API and Streamlit UI
- All services running and connected

## Steps

1. Install Railway CLI: `npm i -g @railway/cli` and authenticate
2. Create Railway project: `railway init`
3. Add Redis plugin via Railway dashboard
4. Add PostgreSQL plugin via Railway dashboard
5. Create API service:
   - Connect to GitHub repo
   - Set start command: `uv run uvicorn crawllmer.app.api.main:app --host 0.0.0.0 --port $PORT`
   - Set environment variables (CRAWLLMER_STORAGE_BACKEND, PG_*, CELERY_*, OTEL_*)
   - Enable public domain
   - Configure healthcheck on `/health`
6. Create Worker service:
   - Same repo, same Dockerfile
   - Set start command: `uv run python -m crawllmer.app.indexer`
   - Set same environment variables (minus OTEL_SERVICE_NAME = crawllmer-worker)
   - No public domain needed
7. Create UI service:
   - Same repo, same Dockerfile
   - Set start command: `uv run streamlit run src/crawllmer/app/web/streamlit_app.py --server.port $PORT --server.address 0.0.0.0`
   - Set environment variables (CRAWLLMER_STORAGE_BACKEND, PG_*, CELERY_*)
   - Enable public domain
8. Verify all services start and connect via Railway logs
9. Optionally create `railway.toml` for reproducible config

## Done Criteria

- [ ] Railway project exists with 5 services (API, Worker, UI, Redis, PostgreSQL)
- [ ] API accessible via public Railway URL, `/health` returns 200
- [ ] UI accessible via public Railway URL, Streamlit loads
- [ ] Worker service is running (visible in Railway logs)
- [ ] All services connect to shared Redis and PostgreSQL via private network

## Notes

Railway uses `$PORT` for dynamic port assignment — start commands should reference it. Redis and Postgres connection details are available as Railway reference variables (e.g., `${{Redis.RAILWAY_PRIVATE_DOMAIN}}`).
