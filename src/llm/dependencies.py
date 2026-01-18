"""Dependency injection for LLM client (GEMINI.md §2.6)."""

from fastapi import Request

from src.llm.client import OpenRouterClient


def get_llm_client(request: Request) -> OpenRouterClient:
    """Get OpenRouter client from application state.

    The client is valid for the lifetime of the application
    and is properly closed on shutdown.
    """
    return request.app.state.llm_client
