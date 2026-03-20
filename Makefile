.PHONY: sync test test-one lint lint-fix lint-path lint-fix-path format check run-api run-ui run-worker run-dev docker-up redis-up distributed-up otel-up clean-db clean stop restart crawl-status inttest inttest-list help

# ─── Setup ───────────────────────────────────────────────────────────────────

sync:  ## Install/sync all dependencies via uv
	uv sync

# ─── Quality ─────────────────────────────────────────────────────────────────

test:  ## Run test suite (pytest -v -s)
	uv run pytest -v -s

test-one:  ## Run a single test (make test-one T=tests/unit/test_foo.py::test_bar)
	uv run pytest -v -s $(T)

lint:  ## Lint code with ruff
	uv run ruff check .

lint-fix:  ## Lint and auto-fix (imports, safe fixes)
	uv run ruff check --fix .

lint-path:  ## Lint specific path(s): make lint-path P="src/crawllmer/core/config.py"
	uv run ruff check $(P)

lint-fix-path:  ## Lint and auto-fix specific path(s): make lint-fix-path P="src/file.py"
	uv run ruff check --fix $(P)

format:  ## Auto-format code with ruff
	uv run ruff format .

check: format lint test  ## Run format → lint → test (full quality gate)

fix: format lint-fix  ## Auto-format + auto-fix lint issues

# ─── Run (Local) ─────────────────────────────────────────────────────────────

run-api:  ## Start FastAPI server on :8000 (with hot-reload)
	uv run uvicorn crawllmer.app.api.main:app --host 0.0.0.0 --port 8000 --reload

run-ui:  ## Start Streamlit UI on :8501
	uv run streamlit run src/crawllmer/app/web/streamlit_app.py --server.address 0.0.0.0 --server.port 8501

run-worker:  ## Start Celery worker (SQLite broker by default)
	uv run python -m crawllmer.app.indexer

run-dev:  ## Start API + UI + worker together (Ctrl-C stops all)
	bash -lc 'trap "kill 0" EXIT; uv run uvicorn crawllmer.app.api.main:app --host 0.0.0.0 --port 8000 --reload & uv run streamlit run src/crawllmer/app/web/streamlit_app.py --server.address 0.0.0.0 --server.port 8501 & uv run python -m crawllmer.app.indexer & wait'

# ─── Docker Compose ──────────────────────────────────────────────────────────

docker-up:  ## Docker: SQLite default (api + worker + ui)
	docker compose up --build

docker-up-production-like: ## Spins up an entire stack (apps + infra + otel) with distributed datastores for app + tasks.
	docker compose --profile distributed --env-file .env.local-distributed -f docker-compose.yml -f docker-compose.otel.yml up --build

redis-up:  ## Docker: + Redis broker (SQLite DB)
	docker compose --profile redis --env-file .env.redis up --build

distributed-up:  ## Docker: Postgres + Redis (production-like)
	docker compose --profile distributed --env-file .env.local-distributed up --build

otel-up:  ## Docker: Postgres + Redis + OTEL/Jaeger/Prometheus/Grafana
	docker compose --profile distributed --env-file .env.local-distributed -f docker-compose.yml -f docker-compose.otel.yml up --build

# ─── Cleanup ─────────────────────────────────────────────────────────────────

clean-db:  ## Remove local SQLite database files
	rm -f crawllmer.db celery-broker.db celery-results.db

clean: clean-db  ## Remove venv, caches, and DB files (run `make sync` after)
	rm -rf .venv __pycache__ .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ─── Process Management ──────────────────────────────────────────────────────

stop:  ## Kill any running API/UI/worker processes
	-pkill -f "uvicorn crawllmer" 2>/dev/null
	-pkill -f "streamlit run" 2>/dev/null
	-pkill -f "crawllmer.app.indexer" 2>/dev/null
	@sleep 1

restart: stop clean-db run-dev  ## Stop servers, wipe DBs, and start fresh

crawl-status:  ## Show status of all crawl runs (add -v for events detail)
	@python3 scripts/check-crawl-status.py $(ARGS)

inttest:  ## Submit integration test URLs (CATEGORY=llmstxt-sites|sitemap-sites|noinfo-sites)
	@uv run python scripts/submit-inttest.py $(CATEGORY)

inttest-list:  ## List integration test URLs without submitting
	@uv run python scripts/submit-inttest.py --list

# ─── Help ────────────────────────────────────────────────────────────────────

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
