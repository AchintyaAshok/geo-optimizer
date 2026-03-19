---
id: PRD-001-TASK-007
prd: PRD-001-ADDENDUM-A
title: Async scheduler and host-aware rate limiting
status: complete
owner: platform-engineering
created: 2026-02-25
---

## Objective
Implement host-aware scheduling and rate limiting for worker throughput, relying on Celery queue ownership (no custom claim complexity).

## Motivation
Improves p95 crawl performance while reducing host bans and transient failures.

## Scope
- Configure Celery queues/routes for stage-aware processing.
- Add host-level concurrency caps and adaptive slowdown on 429/5xx.
- Implement retry policy with bounded backoff/jitter.
- Add queue latency and retry telemetry.

## Out of Scope
- Replacing Celery with custom queue engines.
- Browser-render fallback stage.

## Deliverables
- Scheduler configuration and worker tuning profile.
- Host-limit policy module.
- Retry/backoff policy docs and metrics hooks.

## Acceptance Criteria
- Parallel worker execution shows no duplicate task processing for the same Celery message.
- p95 runtime improves >=25% on concurrency benchmark fixtures.
- 429 recovery rate meets >=70% target.
- Queue wait and retry metrics are visible in telemetry.

## Dependencies
- PRD-001-TASK-001
- PRD-001-TASK-003
- PRD-001-TASK-004

## Validation
- Load/integration tests with simulated 429/5xx responses.
- Worker concurrency tests across multiple processes.


## Implementation Notes
- Added host-aware rate limiter, retry policy integration, and stage processing orchestration with queued->processing->completed transitions.
- Updated during implementation pass for PRD001 end-to-end pipeline delivery.
