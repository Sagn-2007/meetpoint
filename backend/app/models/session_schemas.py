"""Pydantic schemas for collaborative session management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class CreateSessionRequest(BaseModel):
    """Payload for creating a new collaborative meeting session."""

    title: str = Field(..., min_length=1, max_length=255, description="Session title")
    description: Optional[str] = Field(None, max_length=1000, description="Optional session description")
    network_type: Literal["walk", "drive"] = Field(
        "walk",
        description="Traversable network mode ('walk' or 'drive')",
    )
    optimization_objective: Literal["median", "center", "compare"] = Field(
        "median",
        description="Optimization objective ('median', 'center', or 'compare')",
    )
    top_k: int = Field(5, ge=1, le=20, description="Number of candidate recommendations to compute")


class CreateSessionResponse(BaseModel):
    """Response returned upon meeting session creation."""

    session_id: str
    invitation_code: str
    title: str
    description: Optional[str]
    host_token: str
    network_type: str
    optimization_objective: str
    top_k: int
    expires_at: datetime
    created_at: datetime


class SessionPublicResponse(BaseModel):
    """Public information about a meeting session."""

    session_id: str
    invitation_code: str
    title: str
    description: Optional[str]
    status: str
    network_type: str
    optimization_objective: str
    top_k: int
    result_is_stale: bool
    expires_at: datetime
    created_at: datetime
    participants_count: int
    is_expired: bool


class JoinSessionRequest(BaseModel):
    """Payload for joining an existing session."""

    display_name: str = Field(..., min_length=1, max_length=100, description="Participant display name")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Longitude")

    @field_validator("latitude", "longitude")
    @classmethod
    def validate_coord_pairs(cls, v: Optional[float], info) -> Optional[float]:
        return v


class JoinSessionResponse(BaseModel):
    """Response returned when joining a session."""

    session_id: str
    participant_id: str
    display_name: str
    participant_token: str
    location_submitted: bool
    latitude: Optional[float]
    longitude: Optional[float]


class ParticipantPublic(BaseModel):
    """Public view of a participant within a session."""

    id: str
    display_name: str
    latitude: Optional[float]
    longitude: Optional[float]
    location_submitted: bool
    is_online: bool
    joined_at: datetime


class LocationSubmitRequest(BaseModel):
    """Payload for submitting or updating participant location."""

    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude")
    token: Optional[str] = Field(None, description="Participant security token if not passed in header")


class LocationActionResponse(BaseModel):
    """Response for location submit or withdraw actions."""

    status: str
    participant_id: str
    location_submitted: bool
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    result_is_stale: bool = False


class UpdateSettingsRequest(BaseModel):
    """Payload for host updating session configuration."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    network_type: Optional[Literal["walk", "drive"]] = None
    optimization_objective: Optional[Literal["median", "center", "compare"]] = None
    top_k: Optional[int] = Field(None, ge=1, le=20)


class SessionResultResponse(BaseModel):
    """Response containing latest optimization result and staleness status."""

    session_id: str
    has_result: bool
    result_is_stale: bool
    result: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class SessionSnapshotData(BaseModel):
    """Snapshot data emitted to freshly connected WebSocket clients."""

    session: SessionPublicResponse
    participants: List[ParticipantPublic]
    latest_result: Optional[Dict[str, Any]] = None
    user_role: Literal["HOST", "PARTICIPANT", "VIEWER"]
    current_participant_id: Optional[str] = None


class WebSocketEvent(BaseModel):
    """Generic WebSocket message envelope."""

    type: str
    data: Dict[str, Any]
