"""Teeshka Core - FastAPI application entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.health import router as health_router
from src.api.settings import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Validates configuration on startup (fail-fast pattern).
    Configuration errors will prevent the application from starting.
    """
    # Validate settings on startup - will raise ValidationError if misconfigured
    get_settings()
    yield


app = FastAPI(
    title="Teeshka Core",
    description="Central Brain service for Teeshka AI Ecosystem",
    version="0.1.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

app.include_router(health_router, prefix="/api/v1")
