---
id: PRD-002
status: draft
owner: platform-engineering
created: 2026-02-25
---

# PRD-002 — Strategy Orchestration, Crawl Engine, and Resilience

## 1) Problem Statement
Given a target site, we need a strategy pipeline that tries fast/happy-path discovery first, then progressively broader fallback paths. The pipeline must short-circuit on success and provide complete diagnostics on failures.

## 2) Goals
- Implement strategy interface and orchestration with short-circuit semantics.
- Support happy-path and extended-path discovery/generation modes.
- Add resilience (timeouts, retries, exponential backoff, anti-blocking tactics).

## 3) Strategy Catalog (Initial)
1. **Direct llms.txt fetch strategy**
   - Probe common canonical locations (e.g., `/llms.txt`, root alternatives if configured).
2. **Robots and well-known hints strategy**
   - Parse `robots.txt` and known metadata locations for pointers.
3. **Metadata extraction strategy**
   - Crawl key pages and derive structure/content for generated `llms.txt`.
4. **Browser-assisted strategy**
   - Use headless browser for JS-heavy sites and anti-bot friction.
5. **Web archive assist strategy (extension flag)**
   - Query archive snapshots to discover historical page graph/canonical hints.
6. **LLM-assisted strategy selection (future extension)**
   - Optional policy hook for dynamic next-strategy recommendations.

## 4) Strategy Interface Contract
- `can_handle(target, context) -> bool`
- `execute(target, context) -> StrategyResult`
- `cost_hint() -> int` for ordering/optimization
- `id` and `version` for telemetry and persistence

## 5) Orchestration Rules
- Ordered strategy execution; short-circuit on successful `LlmsTxtDocument`.
- Persist attempt outcomes for future prioritization on same host.
- Use prior success history to reorder strategy candidates.
- Emit structured events per attempt: start, retry, fail reason, completion.

## 6) Resilience & Anti-Blocking
- Configurable request timeout budgets by strategy.
- Exponential backoff with jitter for transient failures.
- Retry policy keyed by failure class (5xx/network/timeouts/captcha).
- Custom user-agent rotation and optional header templates.
- Capture roadblock diagnostics (status, challenge type, rendered evidence).

## 7) Acceptance Criteria
- Strategy interface implemented and unit-tested.
- Orchestrator short-circuits correctly and records every attempt.
- Retry/backoff policies verified by integration tests.
- Historical strategy preference materially reduces average retries.

## 8) Task Backlog (Sequential)
1. Build strategy interface, registry, and orchestrator.
2. Implement direct fetch + robots/hints strategies.
3. Implement extraction strategy and generation fallback.
4. Add browser-assisted adapter with feature flag.
5. Add persistence-backed strategy prioritization.
6. Implement archive-assist extension pathway.
7. Add broad integration suite with mock websites.
