"""Domain models and schemas."""

from app.models.geometry import BoundingBox, Coordinate
from app.models.schemas import (
    CandidateRecommendation,
    ComparisonSummary,
    HealthResponse,
    NetworkInfoResponse,
    ObjectiveResult,
    OptimizationMetadata,
    OptimizationObjective,
    OptimizeMeetingRequest,
    OptimizeMeetingResponse,
    Participant,
    ParticipantRouteResult,
)

__all__ = [
    "Coordinate",
    "BoundingBox",
    "Participant",
    "OptimizationObjective",
    "OptimizeMeetingRequest",
    "ParticipantRouteResult",
    "CandidateRecommendation",
    "ComparisonSummary",
    "ObjectiveResult",
    "OptimizationMetadata",
    "OptimizeMeetingResponse",
    "HealthResponse",
    "NetworkInfoResponse",
]
