# syntax=docker/dockerfile:1

# ==============================================================================
# Builder stage: install dependencies using uv
# ==============================================================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Install dependencies from lockfile (frozen = fail if lockfile outdated)
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

# Copy application source
COPY src ./src

# ==============================================================================
# Runtime stage: minimal Python image
# ==============================================================================
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Copy virtual environment and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src ./src

# Configure environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Run FastAPI using uvicorn (included with fastapi[standard])
CMD ["fastapi", "run", "src/api/main.py", "--host", "0.0.0.0", "--port", "8000"]
