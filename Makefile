.PHONY: test lint format check sync

test:
	uv run pytest -v -s

lint:
	uv run ruff check .

format:
	uv run ruff format .

check: format lint test

sync:
	uv sync
