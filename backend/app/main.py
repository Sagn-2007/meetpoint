"""FastAPI application entrypoint for MeetPoint."""

from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import uuid
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.routes import router as api_router
from app.api.session_routes import router as session_router
from app.api.websocket import router as ws_router
from app.core.config import settings
from app.core.exceptions import MeetPointException
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.schemas import HealthResponse
from app.services.session_service import session_service


async def session_cleanup_worker() -> None:
    """Background task to periodically expire stale sessions and purge aged history."""
    while True:
        try:
            await asyncio.sleep(settings.SESSION_CLEANUP_INTERVAL_MINUTES * 60)
            async with AsyncSessionLocal() as db:
                closed_ids = await session_service.mark_expired_sessions(db)
                if closed_ids:
                    logger.info("Auto-closed %d expired sessions: %s", len(closed_ids), closed_ids)
                purged = await session_service.purge_retained_sessions(
                    db, retention_hours=settings.SESSION_RETENTION_HOURS
                )
                if purged:
                    logger.info("Purged %d sessions older than retention policy", purged)
        except asyncio.CancelledError:
            logger.info("Session cleanup worker cancelled on shutdown.")
            break
        except Exception as e:
            logger.error("Session cleanup worker encountered error: %s", e)
            await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown procedures."""
    logger.info("Initializing %s v%s [environment=%s]", settings.PROJECT_NAME, settings.VERSION, settings.ENVIRONMENT)

    # Validate production safety constraints
    settings.validate_production_safety()

    # Start background cleanup worker
    cleanup_task = asyncio.create_task(session_cleanup_worker())

    yield

    # Shutdown: Cancel background tasks
    cleanup_task.cancel()
    await asyncio.gather(cleanup_task, return_exceptions=True)
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

# Request ID correlation middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Configure CORS with explicit allowed origins, methods, and headers
cors_origins = settings.get_cors_origins()
allow_credentials = True
if "*" in cors_origins:
    if settings.ENVIRONMENT == "production":
        raise ValueError("CORS wildcard '*' cannot be combined with credentials in production.")
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Session-Token", "X-Request-ID", "Accept"],
    expose_headers=["X-Request-ID"],
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
    description="Returns the operational health, database connectivity, and version status of the engine.",
)
async def health_check() -> HealthResponse:
    """Service health and database readiness check."""
    db_status = "connected"
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(select(1))
    except Exception as e:
        logger.warning("Database health check ping failed: %s", e)
        db_status = "unavailable"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        service="meetpoint-engine",
        version=settings.VERSION,
        database=db_status,
    )


# Include API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(session_router, prefix=settings.API_V1_STR)
app.include_router(ws_router, prefix=settings.API_V1_STR)
