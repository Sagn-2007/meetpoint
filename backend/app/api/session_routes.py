"""REST API routes for collaborative meeting sessions."""

from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.session import get_db
from app.models.session_schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    JoinSessionRequest,
    JoinSessionResponse,
    LocationActionResponse,
    LocationSubmitRequest,
    SessionPublicResponse,
    SessionResultResponse,
    UpdateSettingsRequest,
)
from app.services.session_service import session_service

router = APIRouter(prefix="/sessions", tags=["Collaborative Sessions"])


def get_token(
    request: Request,
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token"),
    authorization: Optional[str] = Header(None),
    token_param: Optional[str] = Query(None, alias="token"),
) -> Optional[str]:
    """Extract authentication token from headers or query parameters."""
    if x_session_token:
        return x_session_token
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    if token_param:
        return token_param
    return None


@router.post(
    "",
    response_model=CreateSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create collaborative meeting session",
    description="Creates a new meeting session with host token and shareable invitation code.",
)
async def create_session(
    payload: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
) -> CreateSessionResponse:
    session, host_token = await session_service.create_session(
        db=db,
        title=payload.title,
        description=payload.description,
        network_type=payload.network_type,
        optimization_objective=payload.optimization_objective,
        top_k=payload.top_k,
    )
    return CreateSessionResponse(
        session_id=session.id,
        invitation_code=session.invitation_code,
        title=session.title,
        description=session.description,
        host_token=host_token,
        network_type=session.network_type,
        optimization_objective=session.optimization_objective,
        top_k=session.top_k,
        expires_at=session.expires_at,
        created_at=session.created_at,
    )


@router.get(
    "/{invitation_code}",
    response_model=SessionPublicResponse,
    status_code=status.HTTP_200_OK,
    summary="Get session by invitation code",
    description="Retrieves public information about an active or closed session.",
)
async def get_session(
    invitation_code: str,
    db: AsyncSession = Depends(get_db),
) -> SessionPublicResponse:
    session = await session_service.get_session_by_code(db, invitation_code)
    snapshot = session_service.build_snapshot(session, user_role="VIEWER")
    return snapshot.session


@router.post(
    "/{invitation_code}/join",
    response_model=JoinSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join meeting session",
    description="Join session using invitation code and display name. Returns participant credentials.",
)
async def join_session(
    invitation_code: str,
    payload: JoinSessionRequest,
    db: AsyncSession = Depends(get_db),
) -> JoinSessionResponse:
    session, participant, participant_token = await session_service.join_session(
        db=db,
        invitation_code=invitation_code,
        display_name=payload.display_name,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    return JoinSessionResponse(
        session_id=session.id,
        participant_id=participant.id,
        display_name=participant.display_name,
        participant_token=participant_token,
        location_submitted=participant.location_submitted,
        latitude=participant.latitude,
        longitude=participant.longitude,
    )


@router.post(
    "/{session_id}/location",
    response_model=LocationActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit or update participant location",
    description="Participant explicitly submits or updates GPS coordinates.",
)
async def submit_location(
    session_id: str,
    payload: LocationSubmitRequest,
    token: Optional[str] = Depends(get_token),
    db: AsyncSession = Depends(get_db),
) -> LocationActionResponse:
    auth_token = payload.token or token
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Participant token is required.",
        )
    session, participant = await session_service.submit_location(
        db=db,
        session_id=session_id,
        token=auth_token,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    return LocationActionResponse(
        status="success",
        participant_id=participant.id,
        location_submitted=participant.location_submitted,
        latitude=participant.latitude,
        longitude=participant.longitude,
        result_is_stale=session.result_is_stale,
    )


@router.delete(
    "/{session_id}/location",
    response_model=LocationActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Withdraw participant location",
    description="Participant removes their shared location coordinates.",
)
async def withdraw_location(
    session_id: str,
    token: Optional[str] = Depends(get_token),
    db: AsyncSession = Depends(get_db),
) -> LocationActionResponse:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Participant token is required.",
        )
    session, participant = await session_service.withdraw_location(
        db=db,
        session_id=session_id,
        token=token,
    )
    return LocationActionResponse(
        status="success",
        participant_id=participant.id,
        location_submitted=False,
        latitude=None,
        longitude=None,
        result_is_stale=session.result_is_stale,
    )


@router.post(
    "/{session_id}/optimize",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Calculate optimal meeting point (Host only)",
    description="Initiates meeting location optimization for participants with submitted coordinates.",
)
async def optimize_session(
    session_id: str,
    token: Optional[str] = Depends(get_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Host token is required.",
        )
    return await session_service.optimize_session(
        db=db,
        session_id=session_id,
        host_token=token,
    )


@router.get(
    "/{session_id}/results",
    response_model=SessionResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Get latest session optimization results",
    description="Retrieves the most recent calculation result and staleness status.",
)
async def get_results(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionResultResponse:
    result_data = await session_service.get_session_results(db=db, session_id=session_id)
    return SessionResultResponse(**result_data)


@router.patch(
    "/{session_id}/settings",
    response_model=SessionPublicResponse,
    status_code=status.HTTP_200_OK,
    summary="Update session settings (Host only)",
    description="Allows the host to change title, description, network mode, objective, or top_k.",
)
async def update_settings(
    session_id: str,
    payload: UpdateSettingsRequest,
    token: Optional[str] = Depends(get_token),
    db: AsyncSession = Depends(get_db),
) -> SessionPublicResponse:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Host token is required.",
        )
    session = await session_service.update_settings(
        db=db,
        session_id=session_id,
        host_token=token,
        settings_update=payload.model_dump(exclude_unset=True),
    )
    snapshot = session_service.build_snapshot(session, user_role="HOST")
    return snapshot.session


@router.delete(
    "/{session_id}/participants/{participant_id}",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Remove participant (Host only)",
    description="Host removes a participant from the meeting.",
)
async def remove_participant(
    session_id: str,
    participant_id: str,
    token: Optional[str] = Depends(get_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Host token is required.",
        )
    await session_service.remove_participant(
        db=db,
        session_id=session_id,
        host_token=token,
        participant_id=participant_id,
    )
    return {"status": "success", "message": f"Participant {participant_id} removed."}


@router.post(
    "/{session_id}/leave",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Leave session",
    description="Participant voluntarily leaves the collaborative session.",
)
async def leave_session(
    session_id: str,
    token: Optional[str] = Depends(get_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Participant token is required.",
        )
    await session_service.leave_session(
        db=db,
        session_id=session_id,
        token=token,
    )
    return {"status": "success", "message": "Successfully left session."}


@router.post(
    "/{session_id}/close",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Close meeting session (Host only)",
    description="Host permanently closes the session.",
)
async def close_session(
    session_id: str,
    token: Optional[str] = Depends(get_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Host token is required.",
        )
    await session_service.close_session(
        db=db,
        session_id=session_id,
        host_token=token,
    )
    return {"status": "success", "message": "Meeting session closed."}
