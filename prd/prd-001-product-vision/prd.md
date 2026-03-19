---
id: PRD-001
status: draft
owner: product+engineering
created: 2026-02-25
---

# PRD-001 — Product Vision, Canonical llms.txt Modeling, and Quality Bar

## 1) Problem Statement
We need a production-quality web application that accepts a website URL and returns a spec-compliant `llms.txt` file. The system must first discover whether a canonical `llms.txt` already exists and, if not, generate one from site metadata and crawl findings.

## 2) Goals
- Define a canonical domain model for `llms.txt` and related crawl artifacts using Pydantic-first modeling.
- Establish architecture and quality standards that all implementation PRDs must follow.
- Ensure conformance with `llmstxt.org` specification and project assignment requirements.

## 3) Non-Goals
- Implementing all crawling strategies in this PRD.
- Final UI polish and design system.

## 4) Functional Requirements
- Input: a user-provided website URL.
- Output: downloadable `llms.txt` plus transparent run metadata.
- Validation: URL normalization, scheme handling, host validation.
- Canonicalization:
  - represent `llms.txt` structures as strongly typed domain models;
  - support deterministic serialization;
  - preserve source provenance for each generated section/entry.

## 5) Domain Model (Canonical)
### Core entities
- `WebsiteTarget`: normalized URL, hostname, crawl constraints.
- `CrawlRun`: run id, timestamps, selected strategy, status, diagnostics.
- `DocumentSource`: URL, mime type, retrieval status, retrieval method.
- `PageMetadata`: title, description, canonical URL, language, priority.
- `LlmsTxtDocument`: metadata header, entries, optional sections, source mapping.
- `StrategyResult`: success/failure, score/confidence, outputs, failure reasons.

### Model requirements
- Pydantic models for all API contracts and internal cross-boundary DTOs.
- Strict validation and explicit parsing errors.
- Serialization contract tests for stable output.

## 6) Architecture (Hexagonal)
- **Domain layer**: entities/value objects, strategy interfaces, policies.
- **Application layer**: use-cases (process website, generate file, retrieve history).
- **Ports**: crawler port, strategy port, storage port, telemetry port, ui/api port.
- **Adapters**: HTTP crawler adapters, Playwright adapter, SQL storage adapter, FastAPI adapter.
- **Cross-cutting**: observability, retry/backoff, structured logging, config.

## 7) Quality Requirements
- Unit tests for domain logic and canonicalization.
- Integration tests for adapters and end-to-end strategy sequencing.
- Contract tests for serialization and API response shape.
- Static quality gates: formatting, linting, tests.

## 8) Acceptance Criteria
- Canonical `LlmsTxtDocument` model exists with deterministic serializer.
- API and strategy contracts are Pydantic-based and documented.
- Architecture boundaries are reflected in package structure and tests.
- Quality gates execute in CI and locally.

## 9) Risks & Mitigations
- **Spec ambiguity** → keep spec interpretation notes and golden tests.
- **Strategy drift** → central interface contract and shared scoring rubric.
- **Output inconsistency** → deterministic sort and stable formatting rules.

## 10) Task Backlog (Sequential)
1. Define package layout for hexagonal architecture.
2. Implement domain entities and serializers.
3. Add contract and golden-file tests for `llms.txt` output.
4. Add architecture decision record for canonicalization rules.
5. Validate against representative example sites.
