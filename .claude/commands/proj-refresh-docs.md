Refresh the project documentation (README, guides, docs) to reflect the current state of the codebase. Read the source code, then update the docs to match.

## What to Update

1. **README.md** — The primary entry point. Must stay current with the codebase.
2. **guides/** — Feature-focused documents that expand on README sections.
3. **docs/** — Architecture and design documents (NOT PRDs — those stay in `prd/`).
4. **Makefile** — Ensure all targets have `##` comments (powers `make help`).

## How to Refresh

### Step 1: Read the Current State

Read these files to understand what changed:
- `src/crawllmer/web/app.py` — API endpoints (routes, request/response shapes)
- `src/crawllmer/application/workers.py` — Pipeline stages (discovery, extraction, scoring, etc.)
- `src/crawllmer/application/orchestrator.py` — Pipeline orchestration
- `src/crawllmer/domain/models.py` — Domain models and enums
- `src/crawllmer/domain/ports.py` — Abstract interfaces
- `src/crawllmer/adapters/storage.py` — Persistence layer
- `src/crawllmer/web/runtime.py` — Configuration and env vars
- `Makefile` — Build targets
- `docker-compose.yml` — Docker setup (profiles: redis, distributed)
- `docker-compose.otel.yml` — Observability overlay
- `pyproject.toml` — Dependencies
- `.env.example`, `.env.redis`, `.env.local-distributed` — Environment configs
- `src/crawllmer/core/config.py` — Pydantic Settings (source of truth for all env vars)

### Step 2: Diff Against Docs

For each doc file, check:
- Are all API endpoints listed? Any new ones? Any removed?
- Are all Makefile targets documented? Any new ones?
- Are all env vars listed? Defaults correct?
- Does the architecture diagram match the actual module structure?
- Are the pipeline stages accurate? Any new stages or changed logic?
- Are dependency versions / badges correct?

### Step 3: Update Only What Changed

Do NOT rewrite docs that are already correct. Edit surgically — update the specific sections that are stale.

## README Principles

### Structure (in order)
1. **Title + badges** — Project name, key tech badges
2. **One-liner** — What this project does, in one sentence
3. **Quick Start** — `uv sync` → `make run-dev` → verify. Under 10 lines.
4. **Generate an llms.txt** — Concrete curl example showing the full enqueue → process → download flow
5. **How It Works** — The five-stage pipeline as a one-line diagram, then 1–2 sentences per stage
6. **Running the Server** — Local, Docker, Docker+Redis. Just the commands.
7. **API Reference** — Table of endpoints. One row per endpoint, no prose.
8. **Configuration** — Env var table. One row per variable.
9. **Architecture** — ASCII diagram + source tree. Link to full docs.
10. **Design Decisions** — 1–2 sentence summaries. Link to full doc.
11. **Testing** — `make test`, single-test example, test directory tree
12. **Development** — Makefile targets, code style notes
13. **Guides & Docs tables** — Link indexes to guides/ and docs/

### What Makes a Good README Section

- **Concise**: Each section should be scannable in under 10 seconds. If you're writing paragraphs, it belongs in a guide.
- **Example-driven**: Show a command or code snippet, not an explanation of what to do.
- **Table-heavy**: API endpoints, env vars, Makefile targets — always use tables, never prose lists.
- **Link-heavy**: The README is an index. Deep content lives in guides/ and docs/. Use `**[Title](path)**` links.

### Negative Examples (Do NOT Do These)

❌ **Don't write long explanations in the README:**
```markdown
## Extraction
The extraction stage fetches each discovered URL using httpx with a timeout of 8 seconds.
It then parses the HTML using BeautifulSoup, looking in the <head> section for various
metadata sources. The title is extracted by first checking the <title> tag (confidence 1.0),
then falling back to Open Graph (0.8), then Twitter Cards (0.75), and finally JSON-LD (0.6)...
```
This belongs in `guides/pipeline.md`. The README should say: "**Extraction** — Fetches pages, extracts titles and descriptions from head meta, OG, Twitter, JSON-LD" and link to the guide.

❌ **Don't duplicate content across README and guides:**
If the API guide has full request/response examples, the README should only have the endpoint table. Don't copy the examples into both places.

❌ **Don't add sections for things that don't exist yet:**
No "Roadmap", "Future Work", or "Coming Soon" sections. Document what IS, not what might be.

❌ **Don't use badges for things that aren't verifiable:**
No "coverage 90%" badges unless there's a CI job proving it. Stick to version/tool badges.

❌ **Don't nest headers more than 3 levels:**
`#`, `##`, `###` only. If you need `####`, the section is too detailed for its location.

## Guides vs Docs

### `guides/` — How to USE the project

Feature-focused. Written for someone running or integrating with crawllmer.

| File | Covers |
|------|--------|
| `pipeline.md` | The five pipeline stages in detail — what each does, confidence scores, scoring formula |
| `api.md` | Every API endpoint with request/response examples and a workflow script |
| `deployment.md` | Local, Docker, distributed setup with profile reference |
| `environment.md` | All env vars, storage backends, Docker Compose profiles, OTEL |

**Add a new guide when**: A README section keeps growing beyond a table + 2–3 sentences. Extract it into a guide and replace the README content with a summary + link.

**Guide tone**: Practical, example-heavy. "Here's how to do X" with code blocks. Minimal theory.

### `docs/` — How the project is DESIGNED

Architecture and decision-focused. Written for someone understanding or modifying crawllmer internals.

| File | Covers |
|------|--------|
| `architecture.md` | Layers, module responsibilities, data model, runtime topology, dependency flow |
| `design_decisions.md` | Key technical decisions with rationale and trade-offs |
| `project_requirements.md` | Original assignment spec (do not modify) |

**Add a new doc when**: You're documenting WHY something is built a certain way, not HOW to use it. Architecture diagrams, data model changes, protocol decisions → docs. Deployment steps, API examples, config guides → guides.

**Doc tone**: Analytical. "We chose X because Y. The trade-off is Z."

### `prd/` — Product requirements (DO NOT TOUCH)

PRDs are managed separately. Never move them to docs/ or reference them from guides/. The README links to `prd/` as a directory.

## Makefile Rules

- Every target MUST have a `## Comment` on the same line (enables `make help`)
- Group targets with `# ─── Section ───` ASCII dividers
- Keep the `.PHONY` list at the top, covering all targets
- If you add a new target, add it to `.PHONY` too

## Slash Commands

### Verify `/proj-setup` is still valid

After updating docs, read `.claude/commands/proj-setup.md` and check it against the current state:

- Do the questionnaire options still match available storage backends in `core/config.py`?
- Do the referenced Makefile targets (`docker-up`, `redis-up`, `distributed-up`, `full-stack-distributed-up`) still exist?
- Do the env file names (`.env.example`, `.env.redis`, `.env.local-distributed`) still exist?
- Are the verification commands (`curl /health`, Streamlit URL) still correct?
- If new configuration options were added (e.g., new `Settings` fields), should `/proj-setup` ask about them?

If anything is stale, update `proj-setup.md` to match. The setup command is the first thing new users run — it must reflect reality.

## After Updating

Run `make check` to ensure nothing is broken. Verify all cross-references:
- Every `[link](path)` in README points to a file that exists
- Every guide references back to related guides/docs where useful
- The Makefile `make help` output matches the documented targets
