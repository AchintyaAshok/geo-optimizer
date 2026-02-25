---
id: PRD-001-TASK-002
prd: PRD-001-ADDENDUM-A
title: Ingress API and enqueue flow
status: pending
owner: app-engineering
created: 2026-02-25
---

## Objective
Implement the API endpoint that accepts a target URL, validates/normalizes it, creates a crawl run, and enqueues the first Celery task.

## Motivation
Ingress is the user entrypoint and must reliably bridge synchronous API input with asynchronous pipeline execution.

## Scope
- Add/extend endpoint for URL submission.
- URL normalization and validation.
- Persist `crawl_runs` record and initial `work_items` record.
- Publish discovery task to Celery queue with run/work-item identifiers.
- Return run id + initial status payload suitable for polling/stream updates.

## Out of Scope
- Full UI implementation changes beyond API response compatibility.
- Downstream worker business logic.

## Deliverables
- API handler + request/response schemas.
- Enqueue adapter abstraction and Celery integration call.
- Error mapping for invalid URL / enqueue failure.

## Acceptance Criteria
- Valid URL request returns run id and queued status.
- Invalid URL returns deterministic 4xx with validation details.
- Enqueue failures are surfaced as retriable 5xx with structured error payload.
- Integration test verifies run record + queued work item are created together.

## Dependencies
- PRD-001-TASK-001

## Validation
- API integration tests for success and failure paths.
- Persistence assertions for run/work-item creation.
