---
id: PRD-001-TASK-006
prd: PRD-001-ADDENDUM-A
title: Incremental recrawl freshness policy
status: complete
owner: reliability-engineering
created: 2026-02-25
---

## Objective
Add conditional-fetch recrawl behavior using HTTP freshness validators to reduce redundant work on subsequent runs.

## Motivation
Incremental recrawls reduce bandwidth and runtime costs while preserving output completeness.

## Scope
- Persist and reuse `ETag` and `Last-Modified` metadata.
- Issue conditional requests (`If-None-Match`, `If-Modified-Since`) where available.
- Skip extraction/canonicalization for confirmed unchanged pages.
- Track freshness windows and stale-page scheduling rules.

## Out of Scope
- Queue framework changes.
- UI design changes beyond exposing freshness diagnostics.

## Deliverables
- Freshness policy service and repository integration.
- Conditional request support in crawler client adapters.
- Metrics for cache/conditional hit rates.

## Acceptance Criteria
- Repeat runs on unchanged fixtures reduce total requests by >=50%.
- No significant drop in generated-output completeness vs full recrawl baseline.
- Validator metadata persists and is reused correctly across runs.

## Dependencies
- PRD-001-TASK-001
- PRD-001-TASK-004
- PRD-001-TASK-005

## Validation
- Integration tests with controlled ETag/Last-Modified fixtures.
- Regression comparison between full and incremental outputs.


## Implementation Notes
- Added validator storage (ETag/Last-Modified) and conditional request support for incremental recrawls; extraction skips unchanged pages (304 responses).
- Updated during implementation pass for PRD001 end-to-end pipeline delivery.
