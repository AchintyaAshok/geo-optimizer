---
id: PRD-001-TASK-004
prd: PRD-001-ADDENDUM-A
title: Extraction worker with metadata quality tiers
status: complete
owner: crawler-engineering
created: 2026-02-25
---

## Objective
Implement metadata extraction with tiered precedence and per-field provenance/confidence capture.

## Motivation
High-quality metadata is essential for generating accurate, useful llms.txt output.

## Scope
- Celery worker stage consuming discovered URLs.
- Extraction tiers:
  - Tier 1: `<title>`, meta description.
  - Tier 2: OpenGraph/Twitter tags.
  - Tier 3: JSON-LD/schema.org fallbacks.
- Persist extracted fields, source provenance, and confidence scores.
- Mark extraction failures with explicit failure reason taxonomy.

## Out of Scope
- URL canonicalization and dedup.
- Final llms.txt generation.

## Deliverables
- Extraction worker tasks and parsing helpers.
- Data model updates for provenance/confidence fields.
- Coverage metrics emission (title/description completeness).

## Acceptance Criteria
- Title coverage target >=95% on fixture corpus.
- Description coverage target >=80% on fixture corpus.
- Extraction errors are classified and persisted.
- Worker updates stage status and emits metrics for each processed URL.

## Dependencies
- PRD-001-TASK-001
- PRD-001-TASK-003

## Validation
- Unit tests for tiered precedence behavior.
- Integration tests on mixed metadata fixture pages.


## Implementation Notes
- Implemented extraction worker with title/description tier precedence (<title>/meta, OG tags, JSON-LD regex fallback) and per-field provenance/confidence persistence.
- Updated during implementation pass for PRD001 end-to-end pipeline delivery.
