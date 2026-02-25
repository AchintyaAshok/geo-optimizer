---
id: PRD-001-TASK-001
prd: PRD-001-ADDENDUM-A
title: Core queue contracts and minimal run/work-item persistence
status: complete
owner: platform-engineering
created: 2026-02-25
---

## Objective
Establish the shared core models and storage contracts required by API + workers, while keeping queue-claim semantics simple and aligned with Celery guarantees.

## Motivation
All pipeline stages depend on consistent run/work-item schemas and status transitions. This task creates that foundation without over-engineering custom claim logic.

## Scope
- Create/extend core domain enums for run status and stage status.
- Define SQLModel entities for:
  - `crawl_runs`
  - `work_items` (tracking stage progression and retry metadata)
  - optional `work_item_events` (append-only audit trail).
- Define repository interfaces in core for run/work-item CRUD and status updates.
- Keep claim semantics minimal:
  - Celery task delivery/acknowledgement is the primary ownership mechanism.
  - DB stores processing state for visibility/recovery only.

## Out of Scope
- Full worker implementations.
- Queue broker deployment configuration.

## Deliverables
- Core model definitions and migration notes.
- Repository interfaces + basic adapter implementations.
- Status transition documentation in this task file or linked ADR.

## Acceptance Criteria
- Shared models compile and are importable by API and worker packages.
- A run can be created and work-item states can transition through queued -> processing -> completed/failed.
- State transitions are unit-tested for valid/invalid transitions.
- No bespoke distributed lock/claim system is introduced beyond Celery ownership guarantees.

## Dependencies
- None.

## Validation
- Unit tests for model validation and transition rules.
- Repository round-trip tests.


## Implementation Notes
- Implemented core run/work-item enums, transition guards, SQLModel persistence for crawl_runs/work_items/work_item_events, and repository contracts in domain ports with sqlite adapter.
- Updated during implementation pass for PRD001 end-to-end pipeline delivery.
