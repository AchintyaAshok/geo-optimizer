---
id: PRD-001-ADDENDUM-A
status: complete
owner: product+engineering
created: 2026-02-25
related_prd: PRD-001
---

# PRD-001 Addendum — Accepted Strategy Scope and Queue-Driven Processing Architecture

## Context and source of truth
This addendum is anchored to the assignment requirements in `docs/project_requirements.md` and aligned with PRD-002/003/004. It captures **accepted scope decisions** and translates them into an implementation-ready architecture + task decomposition.

## Accepted scope from review
- **Accepted in full:** Phase A and Phase B ideas.
- **Accepted from Phase C:** Async crawler / scheduler approach only.
- **Deferred from Phase C:** JS render fallback and multi-tenant artifact expansion are not in this immediate execution set.

### Accepted idea set (implementation now)
1. Adaptive strategy pipeline with confidence fallback.
2. Sitemap-first discovery.
3. Robots-aware governance.
4. Canonical URL + duplicate consolidation.
5. Metadata extraction quality tiers.
6. Incremental recrawl and freshness policy.
7. Async host-aware scheduler + queueing/rate-limit controls.
8. Output quality scoring and review flags.

## Overlap review vs existing PRDs
We avoid re-proposing already planned work by explicitly mapping this addendum to PRD-002/003/004 and focusing on net improvements.

| Idea | Existing PRD anchor | Classification | Net improvement in this addendum |
|---|---|---|---|
| Adaptive strategy pipeline | PRD-002 (orchestration rules) | Improvement | Confidence-thresholded fallback + persisted decision rationale. |
| Sitemap-first discovery | PRD-002 extraction path | Net-new | First-class sitemap/index traversal step before generic crawl. |
| Robots governance | PRD-002 robots/hints, resilience | Improvement | Explicit governance policy + audited decisions + budgets. |
| Canonical URL + dedup | PRD-001 modeling, PRD-002 extraction output | Net-new | Deterministic canonical maps and duplicate cluster controls. |
| Extraction quality tiers | PRD-002 metadata extraction | Improvement | Tiered precedence and per-field provenance/confidence. |
| Incremental recrawl | PRD-004 history-aware behavior | Net-new | `ETag`/`Last-Modified` conditional recrawl policy. |
| Async scheduler | PRD-002 resilience | Improvement | Work queue + worker claim semantics + host-aware concurrency. |
| Quality scorecard | PRD-003 observability | Improvement | User-facing score and low-confidence review workflow. |

## Queue-driven processing architecture (amendment)

### Why this architecture
The accepted scope now requires independently scalable processing stages and safe concurrent execution. A queue-driven pipeline allows:
- separation of concerns across discovery/extraction/canonicalization/generation;
- backpressure and retry isolation by stage;
- horizontal worker scaling without duplicate URL processing.

### Processing-state model (single-claim guarantee)
Celery task ownership (delivery + ack semantics) is the primary single-claim mechanism. We keep DB state tracking focused on observability/recovery, not bespoke distributed locking.

Proposed job lifecycle:
- `accepted` → `queued` → `processing` → (`completed` | `failed` | `dead_letter`)

State rules:
- Only one worker should execute a given Celery task message at a time (queue guarantee).
- DB state updates remain idempotent and monotonic for visibility.
- Retries are driven by Celery retry policies and recorded in `attempt_count`/event logs.

### Pipeline stages
1. **Ingress stage**: URL normalize/validate + seed run.
2. **Discovery stage**: llms short-circuit, robots, sitemap, bounded link expansion.
3. **Extraction stage**: metadata tiers + structured data.
4. **Canonicalization stage**: URL normalization and dedup cluster mapping.
5. **Scoring stage**: run quality/confidence.
6. **Generation stage**: deterministic llms.txt assembly.
7. **Persistence/notification stage**: run completion state + API/UI status update.

## Python queue library options (researched)

### Option A — Celery (recommended default for worker framework)
- **Why**: mature task queue, retries, scheduling, routing, worker pools, monitoring ecosystem.
- **Best when**: multi-process stage workers and future distributed execution are needed.
- **Broker/backend options**:
  - early/simple: SQLite/SQLAlchemy transport is possible but limited;
  - production: Redis or RabbitMQ (Redis noted as likely extension).
- **Trade-offs**: heavier operational model; best value appears as concurrency requirements grow.

### Option B — Dramatiq
- **Why**: simpler developer experience than Celery, good reliability primitives.
- **Best when**: team wants queue semantics with lower framework complexity.
- **Trade-offs**: smaller ecosystem, less ubiquitous than Celery.

### Option C — RQ / Arq
- **Why**: very small footprint for straightforward background jobs.
- **Best when**: low complexity and Redis-first operations are acceptable.
- **Trade-offs**: fewer orchestration features for multi-stage pipelines.

### Option D — In-process queue + SQL claims (bootstrap mode)
- **Why**: avoids a new container initially; easiest local onboarding.
- **Pattern**: `asyncio.Queue` for local development with durable SQL work table for state tracking and worker claiming.
- **Trade-offs**: not suitable for true distributed multi-node production alone.

### Recommendation path
- **Start**: Celery-based worker ownership and simple DB state tracking for visibility.
- **Scale**: enable Redis-backed Celery profile for higher throughput and distributed workers.

## Package/monorepo structure amendment (uv-friendly)
Use a core package plus stage-specific subpackages that depend on core contracts.

```text
src/
  crawllmer_core/
    domain/           # models, enums, validation, state-machine contracts
    storage/          # SQLModel entities/repositories, claim APIs
    telemetry/        # metrics/event interfaces
  crawllmer_ingress/
  crawllmer_discovery/
  crawllmer_extraction/
  crawllmer_canonicalization/
  crawllmer_scoring/
  crawllmer_generation/
  crawllmer_worker/   # queue worker bootstrap + routing
  crawllmer_api/      # FastAPI surface
```

Rules:
- `crawllmer_core` owns shared models and persistence interfaces.
- Stage packages should be independently testable and import core only.
- Worker package orchestrates queue routing without embedding stage business logic.

## Docker Compose amendment
Provide a one-command local stack to run all components.

### Baseline compose profile (no extra queue infra)
- `api` service
- `worker` service (bootstrap mode using SQL claims)
- `db` service (if external DB used; SQLite volume also acceptable initially)

### Extended compose profile (future)
- add `redis` service and enable Celery broker-backed worker mode.

## Feature detail with success criteria, metrics, persistence

### 1) Adaptive strategy pipeline with confidence-based fallback
- **Priority**: P0 | **Effort**: M
- **Libraries**: `httpx`, `sqlmodel`, optional `tenacity`.
- **Success**: ≥85% first-run non-empty output; lower median duration.
- **Metrics**: strategy success rate, fallback depth, p50/p95 runtime.
- **Persistence**: `crawl_runs.selected_strategy`, `strategy_sequence`, `confidence_score`, `fallback_reason`.

### 2) Sitemap-first deep discovery
- **Priority**: P0 | **Effort**: S/M
- **Libraries**: `httpx`, optional `lxml` or `selectolax`.
- **Success**: +30% unique pages on sitemap-enabled targets.
- **Metrics**: sitemap success rate; sitemap-to-extraction conversion.
- **Persistence**: `document_sources.discovery_method='sitemap'`, optional lineage fields.

### 3) Robots-aware governance
- **Priority**: P0 | **Effort**: S
- **Libraries**: `urllib.robotparser`, optional `reppy`.
- **Success**: 100% policy check prior to deep crawl; lower 403/429.
- **Metrics**: policy violations=0, blocked-by-policy count.
- **Persistence**: robots policy decision + snapshot hash per run.

### 4) Canonical URL + duplicate consolidation
- **Priority**: P1 | **Effort**: M
- **Libraries**: stdlib URL tools, optional `rapidfuzz`.
- **Success**: -40% duplicate entries in generated output.
- **Metrics**: dedup ratio; canonicalization conflicts.
- **Persistence**: canonical map table and duplicate cluster ids.

### 5) Metadata extraction quality tiers
- **Priority**: P0 | **Effort**: M
- **Libraries**: optional `selectolax`; `httpx`.
- **Success**: title coverage ≥95%; description coverage ≥80%.
- **Metrics**: per-field completeness and parse failures.
- **Persistence**: per-field source and confidence.

### 6) Incremental recrawl + freshness
- **Priority**: P1 | **Effort**: M/L
- **Libraries**: `httpx`, `sqlmodel`.
- **Success**: -50% repeat-run requests for unchanged sites.
- **Metrics**: conditional request hit rate; bytes/run.
- **Persistence**: `etag`, `last_modified`, freshness timestamps.

### 7) Async scheduler + queue worker claims
- **Priority**: P1 | **Effort**: L
- **Libraries**: `asyncio`, `httpx`, optional `aiolimiter`; optional Celery for distributed mode.
- **Success**: p95 duration improves ≥25% with stable success rate; no duplicate claims in concurrency tests.
- **Metrics**: queue wait time, claim conflicts, lease expirations, throughput.
- **Persistence**: `work_items` table with state + claim lease fields.

### 8) Output quality scoring
- **Priority**: P0 | **Effort**: S/M
- **Libraries**: stdlib + current models.
- **Success**: every run emits a score and rationale.
- **Metrics**: score distribution, low-score rate, manual overrides.
- **Persistence**: run-level score breakdown and review annotations.

## Updated architecture/process flow

```text
[URL Accepted]
   -> [Ingress API: normalize + validate]
   -> [Persist work_item(state=queued)]
   -> [Queue Router]
   -> [Worker claim (atomic: queued->claimed)]
   -> [Discovery Worker]
   -> [Extraction Worker]
   -> [Canonicalization Worker]
   -> [Scoring Worker]
   -> [Generation Worker]
   -> [Persist run/artifact state=completed]
   -> [API/UI status + download]
```

## Data model addendum for queue processing
New/extended entities:
- `work_items`: `id`, `run_id`, `url`, `stage`, `state`, `priority`, `attempt_count`, `last_error`, timestamps.
- `work_item_events` (optional): append-only state transition log.
- `crawl_runs`: retain strategy and quality fields from prior addendum.

## Task decomposition (approved scope)
The following tasks are intentionally independent and executable in sequence.
1. Core state machine + storage contracts for queue claims.
2. Ingress API + work item creation.
3. Discovery worker (llms/robots/sitemap).
4. Extraction worker with tiered metadata logic.
5. Canonicalization + dedup worker.
6. Incremental recrawl policy integration.
7. Async scheduler + host-aware rate limiting.
8. Scoring + deterministic generation + completion updates.
9. Docker compose baseline profile (api + worker + storage).
10. Optional Celery adapter + Redis compose profile (extension).

## Verification metrics across pipeline
- No duplicate claim processing under parallel workers.
- Stage-level throughput and queue latency.
- End-to-end run success rate.
- Output quality score uplift.
- Retry/lease-expiration recovery rate.


## Implementation Progress Notes
- Executed tasks 001-010 in a single implementation stream with working queue-driven orchestration in `src/crawllmer` and expanded tests.
- Added baseline + Redis compose profiles to match staged deployment recommendations.
