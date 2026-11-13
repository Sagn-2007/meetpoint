"""FastAPI application entrypoint for MeetPoint."""

from __future__ import annotations
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.exceptions import MeetPointException
from app.core.logging import logger
from app.models.schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown procedures."""
    logger.info("Initializing %s v%s", settings.PROJECT_NAME, settings.VERSION)
    yield
    logger.info("Shutting down %s", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Core Geospatial Engine for finding optimal Network 1-Median meeting locations.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Enable CORS for permissive local development and integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(MeetPointException)
async def meetpoint_exception_handler(request: Request, exc: MeetPointException) -> JSONResponse:
    """Fallback exception handler for unhandled MeetPoint domain exceptions."""
    logger.error("Unhandled MeetPoint domain error: %s (details: %s)", exc.message, exc.details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": exc.message, "error_type": exc.__class__.__name__, "details": exc.details},
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Health check",
    description="Returns the operational health and version status of the engine.",
)
async def health_check() -> HealthResponse:
    """Service health and readiness check."""
    return HealthResponse(
        status="healthy",
        service="meetpoint-engine",
        version=settings.VERSION,
    )


# Include API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)
