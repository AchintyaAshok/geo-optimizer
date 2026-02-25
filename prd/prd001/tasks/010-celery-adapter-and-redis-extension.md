---
id: PRD-001-TASK-010
prd: PRD-001-ADDENDUM-A
title: Celery + Redis scaling profile
status: pending
owner: platform-engineering
created: 2026-02-25
---

## Objective
Finalize the scalable queue profile using Celery with Redis broker/backend for multi-worker execution.

## Motivation
As throughput grows, dedicated queue infrastructure improves reliability and operational scalability.

## Scope
- Add Redis service profile and Celery broker/backend configuration.
- Configure worker routing, queue names, and retry defaults.
- Document migration path from baseline mode to Redis-backed mode.
- Add operational notes for visibility (task lag, dead-letter handling patterns).

## Out of Scope
- Non-Celery queue frameworks.
- Full production SRE runbook.

## Deliverables
- Compose extension profile for Redis-backed mode.
- Celery configuration module updates.
- Migration/documentation notes.

## Acceptance Criteria
- Redis-backed mode processes runs end-to-end with multiple worker replicas.
- Task retry/ack behavior is stable under worker restarts.
- Queue depth/lag can be observed through logs or basic metrics endpoint.

## Dependencies
- PRD-001-TASK-007
- PRD-001-TASK-009

## Validation
- Integration test with multi-worker Celery setup.
- Restart/failure simulation to validate retry + ack behavior.
