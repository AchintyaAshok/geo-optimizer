---
parent_prd: ../prd-006-railway-production-deployment/prd.md
prd_name: "PRD 006: Railway Production Deployment"
prd_id: 006
task_id: 004
created: 2026-03-19
state: in_progress
---

# Task 004: Configure Railway services and deploy

## Metadata

| Field | Value |
|-------|-------|
| PRD | [PRD 006: Railway Production Deployment](../prd.md) |
| Created | 2026-03-19 |
| State | in_progress |

## Changelog

| Date | Change |
|------|--------|
| 2026-03-19 | Task created |
| 2026-03-19 | Railway project created, services spawned, config-as-code files added |

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

### Progress (2026-03-19)

**Done:**
- Railway project created on `AchintyaAshok/geo-optimizer` GitHub repo
- 3 app services created (API, Worker, UI) + Redis plugin + PostgreSQL plugin
- Per-service `railway.toml` config-as-code files created in `railway/api/`, `railway/worker/`, `railway/ui/`
- Auto-deploy disconnected (branch disconnected from production) — manual deploy only for now
- Shared variables configured in Railway project settings

**Config-as-code files (`railway/*.toml`):**
- Each service has its own `railway.toml` with builder, dockerfilePath, startCommand, restartPolicy
- API service has `healthcheckPath = "/health"` and `healthcheckTimeout = 120`
- Root Directory left as default (repo root) for all services — config file path set per service in dashboard
- `dockerfilePath = "Dockerfile"` (relative to repo root)

**Shared variables (set in Railway dashboard → Shared Variables):**
```
CRAWLLMER_STORAGE_BACKEND=pgsql
CRAWLLMER_PG_HOST=${{Postgres.PGHOST}}
CRAWLLMER_PG_PORT=${{Postgres.PGPORT}}
CRAWLLMER_PG_USER=${{Postgres.PGUSER}}
CRAWLLMER_PG_PASSWORD=${{Postgres.PGPASSWORD}}
CRAWLLMER_PG_DATABASE=${{Postgres.PGDATABASE}}
CRAWLLMER_CELERY_BROKER_URL=redis://${{Redis.REDIS_PRIVATE_DOMAIN}}:6379/0
CRAWLLMER_CELERY_RESULT_BACKEND=redis://${{Redis.REDIS_PRIVATE_DOMAIN}}:6379/1
CRAWLLMER_LOG_LEVEL=INFO
```

**Railway dashboard settings per service:**
- Each service: Settings → Config File Path → `railway/api/railway.toml` (or worker/ui)
- API + UI: Settings → Networking → Generate Domain (public)
- All services: auto-deploy branch disconnected

**Remaining:**
- Push config files to GitHub and merge to main
- Set Config File Path for each service in Railway dashboard
- Trigger first manual deploy on all 3 services
- Verify services start, connect to Redis/Postgres, and respond

**Key learnings:**
- Railway `railway.toml` is per-service build/deploy config only — cannot set env vars or provision databases
- No Terraform-style infrastructure-as-code — databases and variables are always manual via dashboard
- For multi-service repos, use separate `railway.toml` files with Config File Path set per service in dashboard
- Root Directory must stay as repo root so `dockerfilePath = "Dockerfile"` resolves correctly
