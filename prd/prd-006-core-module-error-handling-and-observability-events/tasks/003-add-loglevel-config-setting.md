---
parent_prd: ../prd-006-core-module-error-handling-and-observability-events/prd.md
prd_name: "PRD 006: Core Module — Error Handling and Observability Events"
prd_id: 006
task_id: 003
created: 2026-03-19
state: pending
---

# Task 003: Add log_level config setting

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

Add a configurable `log_level` setting to `Settings` in `config.py`, validated by Pydantic via `Literal`, and wire it into the OTEL telemetry bootstrap so the `crawllmer` logger severity is configurable at startup.

## Inputs

- `src/crawllmer/config.py` (existing Settings class)
- `src/crawllmer/core/observability/telemetry_setup.py` (moved in Task 2)
- `.env.example` (existing env documentation)

## Outputs

- Modified: `src/crawllmer/config.py` — `log_level` field added
- Modified: `src/crawllmer/core/observability/telemetry_setup.py` — wires log level from settings
- Modified: `.env.example` — `CRAWLLMER_LOG_LEVEL` entry added
- Created: `tests/unit/test_config_log_level.py`

## Steps

1. Write test: create `Settings` with `CRAWLLMER_LOG_LEVEL=WARNING`, assert `settings.log_level == "WARNING"`
2. Write test: create `Settings` with invalid log level, assert Pydantic `ValidationError`
3. Run tests — confirm they fail
4. Add `log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG"` to `Settings` in `config.py` (add `from typing import Literal` import)
5. Run tests — confirm they pass
6. Update `telemetry_setup.py`: import `get_settings`, set `logging.getLogger("crawllmer").setLevel(getattr(logging, get_settings().log_level))` after adding the handler
7. Add `CRAWLLMER_LOG_LEVEL=DEBUG` entry to `.env.example` with comment
8. Run `make check`

## Done Criteria

- [ ] `Settings.log_level` field exists with type `Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]` and default `"DEBUG"`
- [ ] Pydantic rejects invalid values (e.g. `CRAWLLMER_LOG_LEVEL=VERBOSE`) with `ValidationError`
- [ ] `telemetry_setup.py` reads `get_settings().log_level` and applies it to the `crawllmer` logger
- [ ] `.env.example` includes `CRAWLLMER_LOG_LEVEL=DEBUG` with a descriptive comment
- [ ] Tests in `tests/unit/test_config_log_level.py` pass
- [ ] `make check` passes

## Notes

_Any additional context or decisions made during execution._
