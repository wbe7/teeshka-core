# Teeshka Core

**Central Brain service for Teeshka AI Ecosystem.**

FastAPI-based orchestrator with PydanticAI agents for handling requests from Edge (voice) and Telegram (text) clients.

## Architecture

See [Master Design Doc](../.gemini/GEMINI.md) for full architecture.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/query` | Main Teeshka query endpoint |
| GET | `/api/v1/health` | Liveness probe for K8s |
| GET | `/api/v1/ready` | Readiness probe (includes Langfuse status) |
| GET | `/api/v1/docs` | Swagger UI |
| GET | `/api/v1/redoc` | ReDoc |
| GET | `/api/v1/openapi.json` | OpenAPI schema |

## Development

```bash
# Install dependencies
uv sync

# Linting (zero errors required)
make lint

# Auto-fix lint errors
make lint-fix

# Run tests
make test

# Run development server
make run

# Build Docker image (linux/amd64)
make buildx

# Install pre-commit hooks
uv run pre-commit install
```

## Configuration

Configuration is managed via environment variables using `pydantic-settings`.

1. Copy the template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your values (see `.env.example` for all options)

3. Start the server — it will fail fast if required variables are missing

**Required variables:**
- `ALLOWED_USER_ID`, `POSTGRES_URL`, `REDIS_URL`, `GEMINI_GATEWAY_URL`
- `TELEGRAM_BOT_TOKEN`, `LLM_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS_JSON`
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`
- `S3_ACCESS_KEY`, `S3_SECRET_KEY`

## Logging

Structured JSON logging via `structlog` for K8s/Loki/ELK compatibility.

**Features:**
- JSON format output to stdout
- `trace_id` in every log (correlates with Langfuse)
- Request lifecycle logging (`request_started`, `request_completed`)
- Exception logging with stack traces

**Log Level:** Set via `LOG_LEVEL` env var (default: `INFO`)

**Sample log:**
```json
{"event": "request_completed", "trace_id": "abc-123", "status_code": 200, "duration_ms": 15, "level": "info", "timestamp": "2026-01-07T12:00:00.000000Z"}
```

## Docker

```bash
# Build for production (linux/amd64)
make buildx

# Run locally (requires .env file)
docker run --rm -p 8000:8000 --env-file .env wbe7/teeshka-core:dev

# Verify
curl http://localhost:8000/api/v1/health
```

## Project Structure

```
src/
├── api/
│   ├── main.py       # FastAPI application + lifespan
│   ├── health.py     # Health check endpoints
│   ├── logging.py    # Structured logging configuration
│   ├── middleware.py # Request logging middleware
│   ├── schemas.py    # Pydantic response models
│   └── settings.py   # Configuration management
├── storage/
│   └── s3_client.py  # Async S3 client for attachments
└── agents/           # PydanticAI agents (future phases)

tests/                # Unit and integration tests
tests/e2e/            # E2E tests (real services)
```

## Observability

**Langfuse** tracing for full request observability.

**Configuration:**
- `LANGFUSE_PUBLIC_KEY` — Your Langfuse project public key
- `LANGFUSE_SECRET_KEY` — Your Langfuse project secret key  
- `LANGFUSE_BASE_URL` — Self-hosted URL (default: `https://langfuse.cloudnative.space`)

**Features:**
- Client initialization at startup, flush on shutdown
- Readiness probe includes `langfuse: true|false` status
- `@observe_request` decorator for tracing with trace_id correlation
- Graceful degradation if Langfuse unavailable

## Attachment Storage (S3)

Async S3/MinIO client for file attachments (images, voice, documents).

**Configuration:**
- `S3_ENDPOINT` — MinIO endpoint (default: `http://cloudnative.space:9000`)
- `S3_BUCKET` — Bucket name (default: `teeshka`)
- `S3_ACCESS_KEY`, `S3_SECRET_KEY` — Credentials

**S3 Key Format:** `attachments/{user_id}/{session_id}/{uuid7}.{ext}`

**Features:**
- Async upload via `aiobotocore`
- Presigned URLs for download (TTL: 1 hour)
- Retry logic with exponential backoff (max 3 attempts)
- Health check in `/api/v1/ready` endpoint
- Base64 fallback for files < 100KB (configurable)

## Status

✅ **Phase 1**: Project Scaffold  
✅ **Phase 2**: Linting & CI Setup  
✅ **Phase 3**: FastAPI Skeleton + Health  
✅ **Phase 4**: Settings & Configuration  
✅ **Phase 5**: Logging Setup  
✅ **Phase 7**: Langfuse Integration  
✅ **Phase 8**: TeeshkaRequest/Response Models  
✅ **Phase 8b**: Attachment Storage (S3)

