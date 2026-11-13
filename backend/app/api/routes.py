"""FastAPI API routes for MeetPoint."""

from __future__ import annotations
from fastapi import APIRouter, HTTPException, status

from app.core.exceptions import (
    DisconnectedNetworkError,
    InvalidBoundingBoxError,
    MeetPointException,
    NetworkAcquisitionError,
    ParticipantCoordinateError,
    ParticipantSnappingError,
)
from app.core.logging import logger
from app.models.schemas import (
    HealthResponse,
    NetworkInfoResponse,
    OptimizeMeetingRequest,
    OptimizeMeetingResponse,
)
from app.services.network_service import network_service
from app.services.optimization_service import optimization_service

router = APIRouter()


@router.post(
    "/meeting/optimize",
    response_model=OptimizeMeetingResponse,
    status_code=status.HTTP_200_OK,
    summary="Optimize meeting point for N participants",
    description=(
        "Snaps participant coordinates to the road network, computes traversable route distances "
        "via Dijkstra's algorithm, and determines the optimal Network 1-Median meeting location."
    ),
)
async def optimize_meeting(request: OptimizeMeetingRequest) -> OptimizeMeetingResponse:
    """Find the optimal meeting location for participants along traversable road networks."""
    try:
        return optimization_service.optimize_meeting_location(request)
    except (ParticipantCoordinateError, InvalidBoundingBoxError) as e:
        logger.warning("Validation error in meeting optimization: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": e.message, "details": e.details},
        ) from e
    except ParticipantSnappingError as e:
        logger.warning("Snapping error in meeting optimization: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": e.message, "details": e.details},
        ) from e
    except DisconnectedNetworkError as e:
        logger.warning("Disconnected network in meeting optimization: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": e.message, "details": e.details},
        ) from e
    except NetworkAcquisitionError as e:
        logger.error("Network acquisition error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"message": e.message, "details": e.details},
        ) from e
    except MeetPointException as e:
        logger.error("Domain exception: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": e.message, "details": e.details},
        ) from e


@router.get(
    "/network/info",
    response_model=NetworkInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get network cache and configuration info",
    description="Returns metadata about cached road networks, storage location, and network configuration.",
)
async def get_network_info() -> NetworkInfoResponse:
    """Retrieve road network cache status and settings."""
    info = network_service.get_cache_info()
    return NetworkInfoResponse(**info)
