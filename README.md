# Teeshka Core

**Central Brain service for Teeshka AI Ecosystem.**

FastAPI-based orchestrator with PydanticAI agents for handling requests from Edge (voice) and Telegram (text) clients.

## Architecture

See [Master Design Doc](../.gemini/GEMINI.md) for full architecture.

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

# Run development server (Phase 3+)
make run

# Install pre-commit hooks
uv run pre-commit install
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

✅ **Phase 1**: Project Scaffold
🚧 **Phase 2**: Linting & CI Setup

