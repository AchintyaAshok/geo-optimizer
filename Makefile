.PHONY: sync test lint format check run-api run-ui run-worker run-dev clean-db clean stop restart

sync:
	uv sync

test:
	uv run pytest -v -s

lint:
	uv run ruff check .

format:
	uv run ruff format .

check: format lint test

run-api:
	uv run uvicorn crawllmer.main:app --host 0.0.0.0 --port 8000 --reload

run-ui:
	uv run streamlit run src/crawllmer/web/streamlit_app.py --server.address 0.0.0.0 --server.port 8501

run-worker:  ## Start Celery worker (SQLite broker by default)
	uv run python -m crawllmer.worker

run-dev:  ## Start API + UI + worker together
	bash -lc 'trap "kill 0" EXIT; uv run uvicorn crawllmer.main:app --host 0.0.0.0 --port 8000 --reload & uv run streamlit run src/crawllmer/web/streamlit_app.py --server.address 0.0.0.0 --server.port 8501 & uv run python -m crawllmer.worker & wait'

clean-db:  ## Remove local SQLite database files
	rm -f crawllmer.db celery-broker.db celery-results.db

clean: clean-db  ## Remove venv, caches, and DB files; run `make sync` after
	rm -rf .venv __pycache__ .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

stop:  ## Kill any running API/UI/worker processes
	-pkill -f "uvicorn crawllmer" 2>/dev/null
	-pkill -f "streamlit run" 2>/dev/null
	-pkill -f "crawllmer.worker" 2>/dev/null
	@sleep 1

restart: stop clean-db run-dev  ## Stop servers, wipe DBs, and start fresh
