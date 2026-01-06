"""Teeshka Core - FastAPI application entrypoint."""

from fastapi import FastAPI

from src.api.health import router as health_router

app = FastAPI(
    title="Teeshka Core",
    description="Central Brain service for Teeshka AI Ecosystem",
    version="0.1.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)

app.include_router(health_router, prefix="/api/v1")
