---
id: PRD-001-TASK-005
prd: PRD-001-ADDENDUM-A
title: Canonicalization and dedup worker
status: complete
owner: data-engineering
created: 2026-02-25
---

## Objective
Normalize discovered/extracted URLs and collapse duplicates into canonical clusters before scoring and generation.

## Motivation
Deduplication improves output quality and prevents noisy/redundant llms.txt entries.

## Scope
- Worker stage for canonical URL normalization.
- Dedup heuristics (path/query normalization + optional similarity scoring).
- Persist `raw_url -> canonical_url` mappings and cluster identifiers.
- Emit dedup metrics (ratio, conflict count).

## Out of Scope
- Freshness-based recrawl optimization.
- Final output scoring.

## Deliverables
- Canonicalization worker and utility library.
- Mapping persistence writes and lookups.
- Conflict resolution policy docs.

## Acceptance Criteria
- Equivalent URL variants collapse to stable canonical targets.
- Duplicate clusters are persisted and referenced by downstream stages.
- Dedup ratio and conflict metrics are emitted per run.
- Deterministic behavior is verified across repeated runs.

## Dependencies
- PRD-001-TASK-001
- PRD-001-TASK-004

## Validation
- Unit tests for URL normalization rules.
- Integration tests for duplicate-heavy fixtures.


## Implementation Notes
- Implemented canonicalization and dedup stage with normalized URL mapping and confidence-based winner selection before generation.
- Updated during implementation pass for PRD001 end-to-end pipeline delivery.
