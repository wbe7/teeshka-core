"""Teeshka Core - FastAPI application entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.health import router as health_router
from src.api.logging import configure_logging, get_logger
from src.api.middleware import RequestLoggingMiddleware
from src.api.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Initializes logging and validates configuration on startup.
    Configuration errors will prevent the application from starting.
    """
    # Initialize structured logging first
    settings = get_settings()
    configure_logging(settings.log_level)

    log = get_logger(__name__)
    log.info("application_started", version=app.version)

    yield

    log.info("application_shutdown")


app = FastAPI(
    title="Teeshka Core",
    description="Central Brain service for Teeshka AI Ecosystem",
    version="0.1.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

app.include_router(health_router, prefix="/api/v1")
