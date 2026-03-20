FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# Default: API server. Override per service via docker-compose or Railway.
CMD ["uv", "run", "uvicorn", "crawllmer.app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
