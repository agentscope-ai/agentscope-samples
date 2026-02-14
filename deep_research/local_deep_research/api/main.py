# -*- coding: utf-8 -*-
"""Main entry point for Local Deep Research API.

Run with:
    python -m local_deep_research.api.main

Or with uvicorn:
    uvicorn local_deep_research.api.main:app --reload
"""
import uvicorn

from .app import app
from .config import settings


def main():
    """Start the FastAPI application."""
    uvicorn.run(
        "local_deep_research.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
