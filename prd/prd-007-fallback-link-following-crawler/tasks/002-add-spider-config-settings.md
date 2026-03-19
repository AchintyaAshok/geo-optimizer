---
parent_prd: ../prd-007-fallback-link-following-crawler/prd.md
prd_name: "PRD 007: Fallback Link-Following Crawler"
prd_id: 007
task_id: 002
created: 2026-03-19
state: pending
---

# Task 002: Add spider config settings

## Metadata

| Field | Value |
|-------|-------|
| PRD | [PRD 007: Fallback Link-Following Crawler](../prd.md) |
| Created | 2026-03-19 |
| State | pending |

## Changelog

| Date | Change |
|------|--------|
| 2026-03-19 | Task created |

## Objective

Add spider-related configuration fields to the pydantic-settings `Settings` class in `core/config.py` so that spider behaviour (depth, page limits, extension allowlist, timeouts) is config-driven and overridable via environment variables.

## Inputs

- `src/crawllmer/core/config.py` (post-Task 001 restructure)
- `.env.example` at project root
- PRD configuration table specifying field names, env vars, defaults, and purposes

## Outputs

- Five new fields on the `Settings` class: `spider_max_depth`, `spider_max_scan_pages`, `spider_max_index_pages`, `spider_include_extensions`, `spider_timeout_per_page`
- Updated `.env.example` with documented spider env vars
- Unit test validating default values and env-var overrides

## Steps

1. Open `src/crawllmer/core/config.py` and add the five spider fields to the `Settings` class with their defaults:
   - `spider_max_depth: int = 3`
   - `spider_max_scan_pages: int = 100`
   - `spider_max_index_pages: int = 50`
   - `spider_include_extensions: str = ".html,.htm,.txt,.md,"` (trailing comma = extensionless paths)
   - `spider_timeout_per_page: int = 5`
2. Add a property or helper to parse `spider_include_extensions` into a `list[str]` for consumption by the link filter
3. Add the corresponding `CRAWLLMER_SPIDER_*` env vars to `.env.example` with inline documentation
4. Write a unit test in `tests/unit/test_config.py` (or similar) that:
   - Verifies default values load correctly
   - Overrides each field via environment variable and asserts the new value
   - Verifies the extension list parsing handles the trailing-comma convention
5. Run `make check` to confirm lint + test pass

## Done Criteria

- [ ] `Settings` class has all five spider fields with correct types and defaults
- [ ] Extension string is parseable into a list including empty string for extensionless paths
- [ ] `.env.example` documents all five `CRAWLLMER_SPIDER_*` variables
- [ ] Unit test validates defaults and env-var overrides
- [ ] `make check` passes

## Notes

_Any additional context or decisions made during execution._
