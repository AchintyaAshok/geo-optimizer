---
id: PRD-001-TASK-009
prd: PRD-001-ADDENDUM-A
title: Docker compose baseline stack
status: complete
owner: devops
created: 2026-02-25
---

## Objective
Provide a one-command local stack to run API + workers + storage for end-to-end pipeline development.

## Motivation
Developers need an easy and consistent environment to run the full architecture locally.

## Scope
- Add `docker-compose.yml` baseline profile with:
  - API service
  - Worker service
  - persistent storage service/volume
- Add environment wiring and health checks.
- Document local startup and smoke-test commands.

## Out of Scope
- Production-grade orchestration (k8s, autoscaling).
- Redis extension profile (handled in Task 010).

## Deliverables
- Compose file(s) and service definitions.
- `.env.example` updates as needed.
- README section for local stack usage.

## Acceptance Criteria
- `docker compose up` boots stack and API health check passes.
- Worker can receive and process a submitted crawl run.
- Logs clearly show stage progression from enqueue to completion.

## Dependencies
- PRD-001-TASK-002
- PRD-001-TASK-003
- PRD-001-TASK-004
- PRD-001-TASK-008

## Validation
- Local smoke run of compose stack.
- Basic end-to-end crawl execution check.


## Implementation Notes
- Added docker-compose baseline stack with API + worker services, shared persistent volume, env wiring, and health check instructions in README.
- Updated during implementation pass for PRD001 end-to-end pipeline delivery.
