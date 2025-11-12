# -*- coding: utf-8 -*-
"""FastAPI application for Local Deep Research API."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from local_deep_research.utils import log

from .config import settings
from .dependencies import cleanup_components, get_embedding_model, get_vector_db, initialize_components
from .models import HealthCheckResponse
from .routers import documents, research


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events.

    Args:
        app (FastAPI): FastAPI application instance.
    """
    # Startup
    log.info("Starting Local Deep Research API...")
    try:
        initialize_components()
        log.info("API startup completed successfully")
    except Exception as e:
        log.error(f"API startup failed: {e}")
        raise

    yield

    # Shutdown
    log.info("Shutting down Local Deep Research API...")
    try:
        cleanup_components()
        log.info("API shutdown completed")
    except Exception as e:
        log.error(f"API shutdown error: {e}")


# Create FastAPI app
app = FastAPI(
    title="Local Deep Research API",
    description=(
        "API for performing deep research using local vector database and LLM. "
        "Supports document loading, vector search, and research queries."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(research.router)
app.include_router(documents.router)


# Root endpoint
@app.get(
    "/",
    tags=["root"],
    summary="Root endpoint",
    description="Get API information",
)
async def root() -> dict:
    """Root endpoint.

    Returns:
        dict: API information.
    """
    return {
        "name": "Local Deep Research API",
        "version": "1.0.0",
        "description": "API for local deep research with vector database",
        "docs": "/docs",
        "health": "/health",
    }


# Health check endpoint
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["health"],
    summary="Health check",
    description="Check API health status",
)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint.

    Returns:
        HealthCheckResponse: Health status.
    """
    try:
        # Check embedding model
        embedding_model = get_embedding_model()
        embedding_loaded = embedding_model is not None

        # Check vector database
        vector_db = get_vector_db()
        vector_db_connected = vector_db is not None

        # Try to list collections to verify connection
        try:
            vector_db.list_collections()
        except Exception:
            vector_db_connected = False

        status = "healthy" if (embedding_loaded and vector_db_connected) else "degraded"

        return HealthCheckResponse(
            status=status,
            vector_db_connected=vector_db_connected,
            embedding_model_loaded=embedding_loaded,
            version="1.0.0",
        )

    except Exception as e:
        log.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            vector_db_connected=False,
            embedding_model_loaded=False,
            version="1.0.0",
        )


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Global exception handler.

    Args:
        request: Request object.
        exc (Exception): Exception instance.

    Returns:
        JSONResponse: Error response.
    """
    log.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": type(exc).__name__,
            "message": str(exc),
        },
    )
