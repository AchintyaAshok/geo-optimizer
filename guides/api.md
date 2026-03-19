# API Reference

crawllmer exposes a REST API via FastAPI on port 8000 by default.

## Endpoints

### Health Check

```
GET /health
```

Returns server status. Used by Docker healthchecks.

**Response** `200 OK`:
```json
{"status": "ok"}
```

---

### Enqueue a Crawl

```
POST /api/v1/crawls
Content-Type: application/json
```

Creates a new crawl run and enqueues it for processing.

**Request body**:
```json
{
  "url": "https://example.com"
}
```

The `url` field is validated as a proper HTTP/HTTPS URL by Pydantic's `HttpUrl` type.

**Response** `200 OK`:
```json
{
  "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "queued"
}
```

**Error** `422 Unprocessable Entity` — Invalid URL format:
```json
{
  "detail": "..."
}
```

---

### Process a Run

```
POST /api/v1/crawls/{run_id}/process
```

Synchronously executes the full pipeline (discovery → extraction → canonicalization → scoring → generation) for a previously enqueued run. Blocks until complete.

**Path parameters**:
- `run_id` (UUID) — The run ID returned by the enqueue endpoint

**Response** `200 OK`:
```json
{
  "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "score": 0.85,
  "score_breakdown": {
    "coverage": 0.9,
    "confidence": 0.85,
    "redundancy": 0.75,
    "total": 0.85
  }
}
```

**Error** `404 Not Found` — Run ID doesn't exist
**Error** `500 Internal Server Error` — Pipeline processing failed

---

### Get Run Status

```
GET /api/v1/crawls/{run_id}
```

Returns the current status and score of a crawl run.

**Path parameters**:
- `run_id` (UUID) — The run ID

**Response** `200 OK`:
```json
{
  "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "score": 0.85,
  "score_breakdown": {
    "coverage": 0.9,
    "confidence": 0.85,
    "redundancy": 0.75,
    "total": 0.85
  }
}
```

Status values: `queued`, `running`, `completed`, `failed`

**Error** `404 Not Found` — Run ID doesn't exist

---

### Download llms.txt

```
GET /api/v1/crawls/{run_id}/llms.txt
```

Returns the generated `llms.txt` file as plain text.

**Path parameters**:
- `run_id` (UUID) — The run ID

**Response** `200 OK` (`text/plain`):
```
# llms.txt for example.com

- [Example Page](https://example.com/page): A description of the page
- [Another Page](https://example.com/other): Another description
```

**Error** `404 Not Found` — Run hasn't been processed yet or doesn't exist

---

### List Run History

```
GET /api/v1/history
```

Returns the most recent crawl runs (up to 50).

**Query parameters**:
- `host` (string, optional) — Filter by hostname

**Response** `200 OK`:
```json
[
  {
    "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "host": "example.com",
    "status": "completed",
    "score": 0.85
  }
]
```

## Typical Workflow

```bash
# Step 1: Enqueue
RUN_ID=$(curl -s -X POST http://localhost:8000/api/v1/crawls \
  -H 'content-type: application/json' \
  -d '{"url":"https://docs.python.org"}' | jq -r '.run_id')

# Step 2: Process
curl -s -X POST http://localhost:8000/api/v1/crawls/$RUN_ID/process | jq .

# Step 3: Download
curl -s http://localhost:8000/api/v1/crawls/$RUN_ID/llms.txt

# Check history
curl -s http://localhost:8000/api/v1/history | jq .
```

## Notes

- The API uses synchronous processing via `/process`. For async processing, the Celery worker handles tasks published through the queue (see the [deployment guide](deployment.md)).
- All timestamps are UTC.
- Score breakdown values are floats between 0.0 and 1.0.
- The `llms.txt` endpoint returns `text/plain` content, suitable for direct download.
