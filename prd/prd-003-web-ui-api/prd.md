---
id: PRD-003
status: draft
owner: app-engineering
created: 2026-02-25
---

# PRD-003 — FastAPI Web App, Operator-Friendly UI, and Observability

## 1) Problem Statement
Users and operators need a simple UI to submit URLs, view live system activity, and download generated output. Engineering needs first-class telemetry and logs to debug strategy behavior in production.

## 2) Goals
- Ship a minimal but useful web UI with API backend.
- Surface live/near-live crawl logs and decision traces.
- Integrate OpenTelemetry for traces, metrics, and log correlation.

## 3) UI Requirements
- Single primary input box (search-style) for target URL.
- Action controls: crawl/generate, cancel, download `llms.txt`.
- Run detail panel: ordered timeline of strategy attempts and outcomes.
- Error panel: roadblocks and retry behavior explanation.
- Extension tab: prior crawl history and previously generated `llms.txt` content.

## 4) API Requirements (FastAPI)
- `POST /api/v1/crawls` to start crawl.
- `GET /api/v1/crawls/{id}` for run status and diagnostics.
- `GET /api/v1/crawls/{id}/llms.txt` for final output.
- `GET /api/v1/history?host=...` for prior attempts.
- Server-sent events or polling endpoint for action logs.

## 5) Logging & Telemetry
- Structured logs with run id, strategy id, URL, retry count.
- OpenTelemetry spans:
  - request lifecycle
  - strategy attempts
  - network operations
  - persistence operations
- Metrics:
  - strategy success rate
  - fallback depth distribution
  - crawl latency percentiles
  - error classes and roadblocks

## 6) Deployment/Runtime Requirements
- Python process execution for local/dev.
- Multi-process scale-out via Gunicorn workers + Uvicorn workers.
- Containerized deployment profile with health/readiness endpoints.

## 7) Acceptance Criteria
- User can submit URL and obtain downloadable `llms.txt`.
- User can inspect attempt-by-attempt logs from UI.
- Telemetry provides end-to-end trace visibility per crawl id.
- Service supports horizontal process scaling configuration.

## 8) Task Backlog (Sequential)
1. Implement FastAPI endpoints and request/response models.
2. Build simple server-rendered or lightweight frontend UI.
3. Add run log streaming/polling endpoint and UI panel.
4. Instrument with OpenTelemetry and correlation IDs.
5. Add deployment config for Gunicorn/Uvicorn and containers.
6. Add smoke tests for API + UI critical path.
