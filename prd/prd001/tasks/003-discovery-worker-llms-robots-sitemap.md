---
id: PRD-001-TASK-003
prd: PRD-001-ADDENDUM-A
title: Discovery worker for llms, robots, and sitemap
status: pending
owner: crawler-engineering
created: 2026-02-25
---

## Objective
Implement the first worker stage that discovers candidate pages via canonical llms endpoint checks, robots hints, and sitemap traversal.

## Motivation
Discovery quality determines downstream extraction coverage and crawl efficiency.

## Scope
- Celery worker task for discovery stage.
- Strategy order:
  1) direct llms probe,
  2) robots/hints evaluation,
  3) sitemap index/xml parsing,
  4) bounded fallback link seeding.
- Persist discovered URLs and provenance (`llms`, `robots`, `sitemap`, `crawl`).
- Emit discovery metrics/events and update work-item status.

## Out of Scope
- Deep metadata extraction.
- Canonicalization/dedup.

## Deliverables
- Discovery worker module and task registration.
- Parsers/utilities for robots and sitemap handling.
- Storage writes for discovered source records.

## Acceptance Criteria
- Worker processes queued discovery jobs and marks completion/failure correctly.
- Sitemap index recursion works for nested sitemap documents.
- Robots policy is evaluated before bounded crawl fallback.
- Discovery result set includes provenance per URL.

## Dependencies
- PRD-001-TASK-001
- PRD-001-TASK-002

## Validation
- Unit tests for robots/sitemap parsing.
- Integration tests with fixture websites covering each discovery path.
