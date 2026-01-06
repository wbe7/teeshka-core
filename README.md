# Teeshka Core

**Central Brain service for Teeshka AI Ecosystem.**

FastAPI-based orchestrator with PydanticAI agents for handling requests from Edge (voice) and Telegram (text) clients.

## Architecture

See [Master Design Doc](../.gemini/GEMINI.md) for full architecture.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Liveness probe for K8s |
| GET | `/api/v1/ready` | Readiness probe (stub) |
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

## Docker

```bash
# Build for production (linux/amd64)
make buildx

# Run locally
docker run --rm -p 8000:8000 wbe7/teeshka-core:dev

# Verify
curl http://localhost:8000/api/v1/health
```

## Project Structure

```
src/
├── api/
│   ├── main.py      # FastAPI application
│   ├── health.py    # Health check endpoints
│   └── schemas.py   # Pydantic response models
└── agents/          # PydanticAI agents (future phases)

tests/               # Unit and integration tests
```

## Status

✅ **Phase 1**: Project Scaffold  
✅ **Phase 2**: Linting & CI Setup  
✅ **Phase 3**: FastAPI Skeleton + Health
