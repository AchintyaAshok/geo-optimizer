.PHONY: sync test lint lint-fix format check run-api run-ui run-worker run-dev run-observability clean-db clean stop restart crawl-status help

# ─── Setup ───────────────────────────────────────────────────────────────────

sync:  ## Install/sync all dependencies via uv
	uv sync

# ─── Quality ─────────────────────────────────────────────────────────────────

test:  ## Run test suite (pytest -v -s)
	uv run pytest -v -s

lint:  ## Lint code with ruff
	uv run ruff check .

lint-fix:  ## Lint and auto-fix (imports, safe fixes)
	uv run ruff check --fix .

format:  ## Auto-format code with ruff
	uv run ruff format .

check: format lint test  ## Run format → lint → test (full quality gate)

fix: format lint-fix  ## Auto-format + auto-fix lint issues

# ─── Run (Local) ─────────────────────────────────────────────────────────────

run-api:  ## Start FastAPI server on :8000 (with hot-reload)
	uv run uvicorn crawllmer.main:app --host 0.0.0.0 --port 8000 --reload

run-ui:  ## Start Streamlit UI on :8501
	uv run streamlit run src/crawllmer/web/streamlit_app.py --server.address 0.0.0.0 --server.port 8501

run-worker:  ## Start Celery worker (SQLite broker by default)
	uv run python -m crawllmer.worker

run-dev:  ## Start API + UI + worker together (Ctrl-C stops all)
	bash -lc 'trap "kill 0" EXIT; uv run uvicorn crawllmer.main:app --host 0.0.0.0 --port 8000 --reload & uv run streamlit run src/crawllmer/web/streamlit_app.py --server.address 0.0.0.0 --server.port 8501 & uv run python -m crawllmer.worker & wait'

run-observability:  ## Start full stack with OTEL Collector, Jaeger, Prometheus, Grafana
	docker compose -f docker-compose.yml -f docker-compose.observability.yml up --build

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
	-pkill -f "crawllmer.worker" 2>/dev/null
	@sleep 1

restart: stop clean-db run-dev  ## Stop servers, wipe DBs, and start fresh

crawl-status:  ## Show status of all crawl runs (add -v for events detail)
	@python3 scripts/check-crawl-status.py $(ARGS)

# ─── Help ────────────────────────────────────────────────────────────────────

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
