"""API Request and Response Pydantic schemas for MeetPoint."""

from __future__ import annotations
from enum import Enum
import uuid
from typing import Any
from pydantic import BaseModel, Field

from app.models.geometry import BoundingBox, Coordinate


class OptimizationObjective(str, Enum):
    """Supported optimization objectives."""

    MEDIAN = "median"
    CENTER = "center"
    COMPARE = "compare"


class Participant(BaseModel):
    """Participant location representation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8], description="Unique participant identifier")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees [-90, 90]")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees [-180, 180]")
    label: str | None = Field(default=None, description="Optional human-readable label for participant")

    def to_coordinate(self) -> Coordinate:
        """Convert to Coordinate model."""
        return Coordinate(latitude=self.latitude, longitude=self.longitude)


class OptimizeMeetingRequest(BaseModel):
    """Request model for meeting point optimization."""

    participants: list[Participant] = Field(
        ...,
        min_length=2,
        description="List of at least 2 participants with coordinates",
        examples=[
            [
                {"id": "user-1", "latitude": 22.5726, "longitude": 88.3639, "label": "Alice"},
                {"id": "user-2", "latitude": 22.5800, "longitude": 88.3700, "label": "Bob"},
            ]
        ],
    )
    bounding_box: BoundingBox | None = Field(
        default=None,
        description="Geographic bounding box for the road network. If omitted, computed automatically from participant locations.",
    )
    network_type: str = Field(
        default="walk",
        description="OSM network mode, e.g., 'walk', 'drive', 'bike'. Default is 'walk'.",
    )
    objective: OptimizationObjective = Field(
        default=OptimizationObjective.MEDIAN,
        description="Optimization objective: 'median' (Network 1-Median), 'center' (Network 1-Center), or 'compare'.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of top candidate meeting locations to return (1 to 20, default: 5).",
    )
    max_snap_distance_m: float | None = Field(
        default=None,
        description="Maximum permissible snapping distance in metres from coordinate to road network node.",
    )


class ParticipantRouteResult(BaseModel):
    """Calculated route metrics and geometry for an individual participant."""

    participant_id: str
    label: str | None = None
    original_latitude: float
    original_longitude: float
    snapped_node_id: int | str
    snapped_latitude: float
    snapped_longitude: float
    snap_distance_m: float
    route_distance_m: float
    route_node_ids: list[int | str] = Field(
        default_factory=list,
        description="Ordered sequence of graph node identifiers along the shortest path",
    )
    route_coordinates: list[Coordinate] = Field(
        default_factory=list,
        description="Ordered sequence of GPS coordinates along the shortest path",
    )
    segment_count: int = Field(
        default=0,
        description="Number of traversable route segments",
    )


class CandidateRecommendation(BaseModel):
    """Ranked alternative candidate meeting location."""

    rank: int = Field(..., description="Rank according to the active optimization objective (1 is top)")
    node_id: int | str
    location: Coordinate
    aggregate_distance_m: float
    max_distance_m: float
    avg_distance_m: float
    individual_distances_m: list[float] = Field(
        default_factory=list,
        description="Distances from each participant to this candidate in metres",
    )


class ComparisonSummary(BaseModel):
    """Comparative summary comparing Network 1-Median and Network 1-Center results."""

    median_node_id: int | str
    median_location: Coordinate
    median_aggregate_distance_m: float
    median_max_distance_m: float
    median_avg_distance_m: float
    center_node_id: int | str
    center_location: Coordinate
    center_aggregate_distance_m: float
    center_max_distance_m: float
    center_avg_distance_m: float
    same_optimal_node: bool
    aggregate_distance_difference_m: float = Field(
        ...,
        description="Difference in aggregate distance (center aggregate - median aggregate in metres)",
    )
    max_distance_difference_m: float = Field(
        ...,
        description="Difference in maximum individual distance (median max - center max in metres)",
    )
    explanation: str = Field(
        default=(
            "1-Median minimizes the total distance travelled by everyone. "
            "1-Center minimizes the longest individual journey."
        ),
        description="Clear explanation of the conceptual and mathematical differences",
    )


class ObjectiveResult(BaseModel):
    """Complete results for a specific optimization objective."""

    objective: OptimizationObjective
    optimal_node_id: int | str
    optimal_location: Coordinate
    aggregate_distance_m: float
    max_distance_m: float
    avg_distance_m: float
    individual_distances: list[ParticipantRouteResult]
    candidates: list[CandidateRecommendation] = Field(default_factory=list)


class OptimizationMetadata(BaseModel):
    """Diagnostic and performance metadata for the optimization process."""

    network_type: str
    total_network_nodes: int
    total_network_edges: int
    candidate_nodes_evaluated: int
    execution_time_ms: float
    cache_hit: bool
    bounding_box: BoundingBox
    objective: OptimizationObjective = OptimizationObjective.MEDIAN
    top_k: int = 5


class OptimizeMeetingResponse(BaseModel):
    """Response containing the optimal meeting location, routes, and candidate alternatives."""

    optimal_node_id: int | str
    optimal_location: Coordinate
    objective: OptimizationObjective = OptimizationObjective.MEDIAN
    aggregate_distance_m: float
    individual_distances: list[ParticipantRouteResult]
    max_distance_m: float
    avg_distance_m: float
    candidates: list[CandidateRecommendation] = Field(
        default_factory=list,
        description="Top K ranked candidate alternatives",
    )
    comparison: ComparisonSummary | None = Field(
        default=None,
        description="Populated when objective is 'compare'",
    )
    median_result: ObjectiveResult | None = Field(
        default=None,
        description="Detailed Network 1-Median results when objective is 'compare'",
    )
    center_result: ObjectiveResult | None = Field(
        default=None,
        description="Detailed Network 1-Center results when objective is 'compare'",
    )
    metadata: OptimizationMetadata


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = "healthy"
    service: str = "meetpoint-engine"
    version: str = "1.0.0"


class NetworkInfoResponse(BaseModel):
    """Network cache and configuration summary."""

    cached_networks_count: int
    default_network_type: str
    cache_directory: str
    cached_files: list[str]
    active_network: dict[str, Any] | None = None
