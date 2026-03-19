---
parent_prd: ../prd-006-core-module-error-handling-and-observability-events/prd.md
prd_name: "PRD 006: Core Module — Error Handling and Observability Events"
prd_id: 006
task_id: 007
created: 2026-03-19
state: pending
---

# Task 007: Update documentation

## Metadata

| Field | Value |
|-------|-------|
| PRD | [PRD 006: Core Module — Error Handling and Observability Events](../prd.md) |
| Created | 2026-03-19 |
| State | pending |

## Changelog

| Date | Change |
|------|--------|
| 2026-03-19 | Task created |

## Objective

Update project documentation to reflect the new `core/` package, error handling design, observability events design, and the `CRAWLLMER_LOG_LEVEL` environment variable.

## Inputs

- `docs/design_decisions.md` (existing design decisions document)
- `CLAUDE.md` (project instructions)
- Completed Tasks 1-6 (all code changes landed)

## Outputs

- Modified: `docs/design_decisions.md` — new "Error Handling" and "Observability Events" sections
- Modified: `CLAUDE.md` — updated environment variable table and Architecture directory tree

## Steps

1. Add "Error Handling" section to `docs/design_decisions.md`: typed exceptions over generic catches, hierarchy rationale, `PipelineProcessingError` causal chain, `retry.py` exemption
2. Add "Observability Events" section to `docs/design_decisions.md`: stage-level vs business-level metrics separation, single-emission-point principle, `EventMetadata` abstraction
3. Update `CLAUDE.md` environment variable table: add `CRAWLLMER_LOG_LEVEL` row
4. Update `CLAUDE.md` Architecture section: add `core/` to the directory tree

## Done Criteria

- [ ] `docs/design_decisions.md` has an "Error Handling" section explaining typed exceptions, hierarchy design, causal chain, and `retry.py` exemption
- [ ] `docs/design_decisions.md` has an "Observability Events" section explaining stage vs business metrics, single-emission-point, and `EventMetadata` abstraction
- [ ] `CLAUDE.md` environment variable table includes `CRAWLLMER_LOG_LEVEL` with default and purpose
- [ ] `CLAUDE.md` Architecture directory tree includes `core/` with `errors.py` and `observability/` subpackage

## Notes

_Any additional context or decisions made during execution._
