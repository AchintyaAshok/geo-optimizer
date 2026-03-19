.PHONY: sync test lint format check run-api run-ui run-dev run-observability

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
	PYTHONPATH=src uv run uvicorn crawllmer.main:app --host 0.0.0.0 --port 8000 --reload

run-ui:
	PYTHONPATH=src uv run streamlit run src/crawllmer/web/streamlit_app.py --server.address 0.0.0.0 --server.port 8501

run-dev:
	bash -lc 'trap "kill 0" EXIT; PYTHONPATH=src uv run uvicorn crawllmer.main:app --host 0.0.0.0 --port 8000 --reload & PYTHONPATH=src uv run streamlit run src/crawllmer/web/streamlit_app.py --server.address 0.0.0.0 --server.port 8501'

run-observability:
	docker compose -f docker-compose.yml -f docker-compose.observability.yml up --build
