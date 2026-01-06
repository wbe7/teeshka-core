# Teeshka Core

**Central Brain service for Teeshka AI Ecosystem.**

FastAPI-based orchestrator with PydanticAI agents for handling requests from Edge (voice) and Telegram (text) clients.

## Architecture

See [Master Design Doc](../.gemini/GEMINI.md) for full architecture.

## Quick Start

```bash
# Install dependencies
uv sync

# Run development server
uv run fastapi dev src/main.py

# Run linter
uv run ruff check .
uv run ruff format --check .

# Run tests
uv run pytest
```

## Project Structure

```
src/
├── api/        # FastAPI routes (/api/v1/)
├── agents/     # PydanticAI agents (Router, SRE, Personal)
└── main.py     # Application entrypoint (Phase 3)

tests/          # Unit and integration tests
```

## Status

🚧 **Phase 1**: Project Scaffold (in progress)
