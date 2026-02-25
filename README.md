# crawllmer

Queue-driven web app that crawls websites and generates deterministic `llms.txt` output.

## Local development

```bash
make sync
make check
uv run uvicorn crawllmer.main:app --reload
```

## API quickstart

```bash
curl -X POST http://localhost:8000/api/v1/crawls \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com"}'

curl -X POST http://localhost:8000/api/v1/crawls/<RUN_ID>/process
curl http://localhost:8000/api/v1/crawls/<RUN_ID>/llms.txt
```

## Queue backend options

By default, Celery is configured to use SQLAlchemy+SQLite for broker and result backend:

- `CRAWLLMER_CELERY_BROKER_URL=sqla+sqlite:///./celery-broker.db`
- `CRAWLLMER_CELERY_RESULT_BACKEND=db+sqlite:///./celery-results.db`

This provides a lightweight setup with no additional services required.

## Docker baseline stack (SQLite-backed Celery)

```bash
docker compose up --build
curl http://localhost:8000/health
```

## Redis extension profile

```bash
docker compose -f docker-compose.yml -f docker-compose.redis.yml up --build
```

This profile adds Redis and overrides Celery broker/result backend to Redis.
