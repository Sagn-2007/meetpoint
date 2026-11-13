"""Session management service for collaborative meeting planning."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import (
    DisconnectedNetworkError,
    GeographicSpreadError,
    MeetPointException,
    NetworkAcquisitionError,
    ParticipantCoordinateError,
    ParticipantSnappingError,
)
from app.core.logging import logger
from app.core.security import (
    generate_invitation_code,
    generate_secure_token,
    hash_token,
    verify_token,
)
from app.db.models.session_models import MeetingSession, SessionOptimization, SessionParticipant
from app.models.geometry import Coordinate
from app.models.schemas import OptimizationObjective, OptimizeMeetingRequest, Participant
from app.models.session_schemas import (
    ParticipantPublic,
    SessionPublicResponse,
    SessionSnapshotData,
)
from app.services.connection_manager import manager
from app.services.optimization_service import optimization_service


class SessionService:
    """Service encapsulating business logic and persistence for collaborative sessions."""

    async def create_session(
        self,
        db: AsyncSession,
        title: str,
        description: Optional[str] = None,
        network_type: str = "walk",
        optimization_objective: str = "median",
        top_k: int = 5,
    ) -> Tuple[MeetingSession, str]:
        """Create a new collaborative session, generate tokens, and persist to database."""
        host_token = generate_secure_token()
        host_token_hash = hash_token(host_token)

        # Generate unique invitation code
        invitation_code = ""
        for _ in range(5):
            candidate_code = generate_invitation_code(settings.INVITATION_CODE_LENGTH)
            result = await db.execute(
                select(MeetingSession).where(MeetingSession.invitation_code == candidate_code)
            )
            if not result.scalar_one_or_none():
                invitation_code = candidate_code
                break

        if not invitation_code:
            invitation_code = generate_invitation_code(10)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=settings.SESSION_EXPIRATION_HOURS)

        session = MeetingSession(
            title=title,
            description=description,
            invitation_code=invitation_code,
            host_token_hash=host_token_hash,
            network_type=network_type,
            optimization_objective=optimization_objective,
            top_k=top_k,
            status="active",
            result_is_stale=False,
            created_at=now,
            expires_at=expires_at,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        logger.info("Created collaborative session %s with code %s", session.id, invitation_code)
        return session, host_token

    async def get_session_by_code(
        self,
        db: AsyncSession,
        invitation_code: str,
    ) -> MeetingSession:
        """Retrieve a session by its invitation code, loading participants and optimizations."""
        stmt = (
            select(MeetingSession)
            .where(MeetingSession.invitation_code == invitation_code.upper().strip())
            .options(
                selectinload(MeetingSession.participants),
                selectinload(MeetingSession.optimizations),
            )
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meeting session with code '{invitation_code}' was not found.",
            )

        now = datetime.now(timezone.utc)
        if session.expires_at.tzinfo is None:
            expires_at = session.expires_at.replace(tzinfo=timezone.utc)
        else:
            expires_at = session.expires_at

        if now > expires_at and session.status == "active":
            session.status = "closed"
            session.closed_at = now
            await db.commit()
            await db.refresh(session)

        return session

    async def get_session_by_id(
        self,
        db: AsyncSession,
        session_id: str,
    ) -> MeetingSession:
        """Retrieve a session by UUID id, loading participants and optimizations."""
        stmt = (
            select(MeetingSession)
            .where(MeetingSession.id == session_id)
            .options(
                selectinload(MeetingSession.participants),
                selectinload(MeetingSession.optimizations),
            )
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meeting session '{session_id}' was not found.",
            )

        now = datetime.now(timezone.utc)
        expires_at = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at and session.status == "active":
            session.status = "closed"
            session.closed_at = now
            await db.commit()
            await db.refresh(session)

        return session

    def authenticate_token(
        self,
        session: MeetingSession,
        token: str,
    ) -> Tuple[str, Optional[SessionParticipant]]:
        """
        Authenticate a provided token against the session host and participants.
        Returns (role, participant_or_none) where role is 'HOST', 'PARTICIPANT', or 'VIEWER'.
        """
        if not token:
            return "VIEWER", None

        # Check host token
        if verify_token(token, session.host_token_hash):
            return "HOST", None

        # Check participant tokens (SHA-256 comparison)
        token_hash = hash_token(token)
        for participant in session.participants:
            if participant.left_at is None and participant.participant_token_hash == token_hash:
                return "PARTICIPANT", participant

        return "VIEWER", None

    async def join_session(
        self,
        db: AsyncSession,
        invitation_code: str,
        display_name: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Tuple[MeetingSession, SessionParticipant, str]:
        """Join an existing active meeting session as a participant."""
        session = await self.get_session_by_code(db, invitation_code)

        now = datetime.now(timezone.utc)
        expires_at = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This meeting session has expired.",
            )

        if session.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This meeting session is closed and is no longer accepting participants.",
            )

        participant_token = generate_secure_token()
        participant_token_hash = hash_token(participant_token)

        has_coords = latitude is not None and longitude is not None
        participant = SessionParticipant(
            session_id=session.id,
            display_name=display_name.strip(),
            participant_token_hash=participant_token_hash,
            latitude=latitude if has_coords else None,
            longitude=longitude if has_coords else None,
            location_submitted=has_coords,
            is_online=True,
            joined_at=now,
            last_updated_at=now,
        )
        db.add(participant)

        if has_coords and session.optimizations:
            session.result_is_stale = True

        await db.commit()
        await db.refresh(participant)
        await db.refresh(session)

        # Broadcast participant_joined event
        participant_public = ParticipantPublic(
            id=participant.id,
            display_name=participant.display_name,
            latitude=participant.latitude,
            longitude=participant.longitude,
            location_submitted=participant.location_submitted,
            is_online=True,
            joined_at=participant.joined_at,
        )
        await manager.broadcast(
            session.id,
            {
                "type": "participant_joined",
                "data": participant_public.model_dump(mode="json"),
            },
        )

        return session, participant, participant_token

    async def submit_location(
        self,
        db: AsyncSession,
        session_id: str,
        token: str,
        latitude: float,
        longitude: float,
    ) -> Tuple[MeetingSession, SessionParticipant]:
        """Submit or update participant GPS coordinates."""
        session = await self.get_session_by_id(db, session_id)
        if session.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot submit location to a closed session.",
            )

        role, participant = self.authenticate_token(session, token)
        if role != "PARTICIPANT" or not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid participant credentials for location submission.",
            )

        now = datetime.now(timezone.utc)
        participant.latitude = latitude
        participant.longitude = longitude
        participant.location_submitted = True
        participant.last_updated_at = now

        # If previous optimization existed, mark as stale
        if session.optimizations:
            session.result_is_stale = True

        await db.commit()
        await db.refresh(participant)
        await db.refresh(session)

        # Broadcast participant_updated
        participant_public = ParticipantPublic(
            id=participant.id,
            display_name=participant.display_name,
            latitude=participant.latitude,
            longitude=participant.longitude,
            location_submitted=participant.location_submitted,
            is_online=manager.is_participant_online(session.id, participant.id),
            joined_at=participant.joined_at,
        )
        await manager.broadcast(
            session.id,
            {
                "type": "participant_updated",
                "data": participant_public.model_dump(mode="json"),
            },
        )

        if session.result_is_stale:
            await manager.broadcast(
                session.id,
                {
                    "type": "result_stale",
                    "data": {
                        "result_is_stale": True,
                        "reason": f"{participant.display_name} updated their location.",
                    },
                },
            )

        return session, participant

    async def withdraw_location(
        self,
        db: AsyncSession,
        session_id: str,
        token: str,
    ) -> Tuple[MeetingSession, SessionParticipant]:
        """Explicitly withdraw participant GPS coordinates."""
        session = await self.get_session_by_id(db, session_id)
        if session.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot withdraw location in a closed session.",
            )

        role, participant = self.authenticate_token(session, token)
        if role != "PARTICIPANT" or not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid participant credentials.",
            )

        now = datetime.now(timezone.utc)
        participant.latitude = None
        participant.longitude = None
        participant.location_submitted = False
        participant.last_updated_at = now

        if session.optimizations:
            session.result_is_stale = True

        await db.commit()
        await db.refresh(participant)
        await db.refresh(session)

        # Broadcast participant_updated
        participant_public = ParticipantPublic(
            id=participant.id,
            display_name=participant.display_name,
            latitude=None,
            longitude=None,
            location_submitted=False,
            is_online=manager.is_participant_online(session.id, participant.id),
            joined_at=participant.joined_at,
        )
        await manager.broadcast(
            session.id,
            {
                "type": "participant_updated",
                "data": participant_public.model_dump(mode="json"),
            },
        )

        if session.result_is_stale:
            await manager.broadcast(
                session.id,
                {
                    "type": "result_stale",
                    "data": {
                        "result_is_stale": True,
                        "reason": f"{participant.display_name} withdrew their location.",
                    },
                },
            )

        return session, participant

    async def update_settings(
        self,
        db: AsyncSession,
        session_id: str,
        host_token: str,
        settings_update: Dict[str, Any],
    ) -> MeetingSession:
        """Update session parameters (HOST only)."""
        session = await self.get_session_by_id(db, session_id)
        role, _ = self.authenticate_token(session, host_token)
        if role != "HOST":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the meeting host can change session settings.",
            )

        if session.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify a closed session.",
            )

        settings_changed_objective_or_network = False
        if "title" in settings_update and settings_update["title"] is not None:
            session.title = settings_update["title"]
        if "description" in settings_update and settings_update["description"] is not None:
            session.description = settings_update["description"]
        if "network_type" in settings_update and settings_update["network_type"] is not None:
            if session.network_type != settings_update["network_type"]:
                settings_changed_objective_or_network = True
            session.network_type = settings_update["network_type"]
        if "optimization_objective" in settings_update and settings_update["optimization_objective"] is not None:
            if session.optimization_objective != settings_update["optimization_objective"]:
                settings_changed_objective_or_network = True
            session.optimization_objective = settings_update["optimization_objective"]
        if "top_k" in settings_update and settings_update["top_k"] is not None:
            if session.top_k != settings_update["top_k"]:
                settings_changed_objective_or_network = True
            session.top_k = settings_update["top_k"]

        if settings_changed_objective_or_network and session.optimizations:
            session.result_is_stale = True

        await db.commit()
        await db.refresh(session)

        # Broadcast settings_updated
        await manager.broadcast(
            session.id,
            {
                "type": "settings_updated",
                "data": {
                    "title": session.title,
                    "description": session.description,
                    "network_type": session.network_type,
                    "optimization_objective": session.optimization_objective,
                    "top_k": session.top_k,
                    "result_is_stale": session.result_is_stale,
                },
            },
        )

        return session

    async def remove_participant(
        self,
        db: AsyncSession,
        session_id: str,
        host_token: str,
        participant_id: str,
    ) -> MeetingSession:
        """Remove a participant from the meeting (HOST only)."""
        session = await self.get_session_by_id(db, session_id)
        role, _ = self.authenticate_token(session, host_token)
        if role != "HOST":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the meeting host can remove participants.",
            )

        target_participant = None
        for p in session.participants:
            if p.id == participant_id and p.left_at is None:
                target_participant = p
                break

        if not target_participant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active participant '{participant_id}' not found.",
            )

        now = datetime.now(timezone.utc)
        target_participant.left_at = now
        target_participant.is_online = False

        if target_participant.location_submitted and session.optimizations:
            session.result_is_stale = True

        await db.commit()
        await db.refresh(session)

        # Broadcast participant_removed
        await manager.broadcast(
            session.id,
            {
                "type": "participant_removed",
                "data": {
                    "participant_id": target_participant.id,
                    "display_name": target_participant.display_name,
                },
            },
        )

        if session.result_is_stale:
            await manager.broadcast(
                session.id,
                {
                    "type": "result_stale",
                    "data": {
                        "result_is_stale": True,
                        "reason": f"{target_participant.display_name} was removed by the host.",
                    },
                },
            )

        return session

    async def leave_session(
        self,
        db: AsyncSession,
        session_id: str,
        token: str,
    ) -> MeetingSession:
        """Participant voluntarily leaves the meeting."""
        session = await self.get_session_by_id(db, session_id)
        role, participant = self.authenticate_token(session, token)
        if role != "PARTICIPANT" or not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid participant credentials.",
            )

        now = datetime.now(timezone.utc)
        participant.left_at = now
        participant.is_online = False

        if participant.location_submitted and session.optimizations:
            session.result_is_stale = True

        await db.commit()
        await db.refresh(session)

        # Broadcast participant_left
        await manager.broadcast(
            session.id,
            {
                "type": "participant_left",
                "data": {
                    "participant_id": participant.id,
                    "display_name": participant.display_name,
                },
            },
        )

        if session.result_is_stale:
            await manager.broadcast(
                session.id,
                {
                    "type": "result_stale",
                    "data": {
                        "result_is_stale": True,
                        "reason": f"{participant.display_name} left the meeting.",
                    },
                },
            )

        return session

    async def close_session(
        self,
        db: AsyncSession,
        session_id: str,
        host_token: str,
    ) -> MeetingSession:
        """Close the session permanently (HOST only)."""
        session = await self.get_session_by_id(db, session_id)
        role, _ = self.authenticate_token(session, host_token)
        if role != "HOST":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the meeting host can close the session.",
            )

        now = datetime.now(timezone.utc)
        session.status = "closed"
        session.closed_at = now

        await db.commit()
        await db.refresh(session)

        # Broadcast session_closed
        await manager.broadcast(
            session.id,
            {
                "type": "session_closed",
                "data": {
                    "closed_at": now.isoformat(),
                    "message": "The host has closed this meeting session.",
                },
            },
        )

        return session

    async def optimize_session(
        self,
        db: AsyncSession,
        session_id: str,
        host_token: str,
    ) -> Dict[str, Any]:
        """Trigger meeting point optimization for all eligible participants (HOST only)."""
        session = await self.get_session_by_id(db, session_id)
        role, _ = self.authenticate_token(session, host_token)
        if role != "HOST":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the meeting host can trigger optimization.",
            )

        if session.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot run optimization on a closed session.",
            )

        now = datetime.now(timezone.utc)
        expires_at = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This meeting session has expired.",
            )

        # Find active participants with submitted coordinates
        active_participants = [
            p for p in session.participants
            if p.left_at is None and p.location_submitted and p.latitude is not None and p.longitude is not None
        ]

        if len(active_participants) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Optimization requires at least 2 participants with submitted locations. Currently found {len(active_participants)}.",
            )

        # Broadcast optimization_started
        await manager.broadcast(
            session.id,
            {
                "type": "optimization_started",
                "data": {"session_id": session.id, "participants_count": len(active_participants)},
            },
        )

        # Build request for existing optimization engine
        participant_inputs = [
            Participant(
                id=p.id,
                label=p.display_name,
                latitude=p.latitude,
                longitude=p.longitude,
            )
            for p in active_participants
        ]

        objective_enum = (
            OptimizationObjective.MEDIAN
            if session.optimization_objective == "median"
            else OptimizationObjective.CENTER
            if session.optimization_objective == "center"
            else OptimizationObjective.COMPARE
        )

        opt_request = OptimizeMeetingRequest(
            participants=participant_inputs,
            network_type=session.network_type,
            objective=objective_enum,
            top_k=session.top_k,
        )

        try:
            # Run existing optimization engine asynchronously in thread pool to avoid blocking event loop
            response = await asyncio.to_thread(
                optimization_service.optimize_meeting_location,
                opt_request,
            )
            result_dict = response.model_dump(mode="json")
        except (ParticipantCoordinateError, GeographicSpreadError) as e:
            logger.warning("Coordinate/spread error in session optimization %s: %s", session.id, e)
            await manager.broadcast(
                session.id,
                {"type": "optimization_failed", "data": {"error": e.message if hasattr(e, 'message') else str(e)}},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Optimization request rejected: {e.message if hasattr(e, 'message') else str(e)}",
            ) from e
        except (ParticipantSnappingError, DisconnectedNetworkError) as e:
            logger.warning("Routing or network error in session optimization %s: %s", session.id, e)
            await manager.broadcast(
                session.id,
                {"type": "optimization_failed", "data": {"error": e.message if hasattr(e, 'message') else str(e)}},
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Optimization failed: {e.message if hasattr(e, 'message') else str(e)}",
            ) from e
        except NetworkAcquisitionError as e:
            logger.error("OSM acquisition error in session optimization %s: %s", session.id, e)
            await manager.broadcast(
                session.id,
                {"type": "optimization_failed", "data": {"error": "Failed to acquire road network from OpenStreetMap"}},
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"OpenStreetMap network acquisition failed: {str(e)}",
            ) from e
        except Exception as e:
            logger.error("Optimization failed for session %s: %s", session.id, e, exc_info=True)
            await manager.broadcast(
                session.id,
                {
                    "type": "optimization_failed",
                    "data": {"error": str(e)},
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Optimization failed: {str(e)}",
            ) from e

        # Store optimization record
        optimization_record = SessionOptimization(
            session_id=session.id,
            objective=session.optimization_objective,
            network_type=session.network_type,
            result_json=json.dumps(result_dict),
            created_at=now,
        )
        db.add(optimization_record)
        session.result_is_stale = False
        await db.commit()
        await db.refresh(session)

        # Broadcast optimization_completed
        await manager.broadcast(
            session.id,
            {
                "type": "optimization_completed",
                "data": {
                    "result": result_dict,
                    "result_is_stale": False,
                    "created_at": now.isoformat(),
                },
            },
        )

        return result_dict

    async def get_session_results(
        self,
        db: AsyncSession,
        session_id: str,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve latest optimization result and staleness status."""
        session = await self.get_session_by_id(db, session_id)

        # Enforce authorization boundaries
        if token:
            role, participant = self.authenticate_token(session, token)
            if role not in ("HOST", "PARTICIPANT"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid credentials for session.",
                )
            if role == "PARTICIPANT" and (not participant or participant.left_at is not None):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Participant is no longer active in this session.",
                )
        elif settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token is required to access session results.",
            )

        if not session.optimizations:
            return {
                "session_id": session.id,
                "has_result": False,
                "result_is_stale": session.result_is_stale,
                "result": None,
                "created_at": None,
            }

        latest = session.optimizations[0]
        return {
            "session_id": session.id,
            "has_result": True,
            "result_is_stale": session.result_is_stale,
            "result": json.loads(latest.result_json),
            "created_at": latest.created_at,
        }

    def build_snapshot(
        self,
        session: MeetingSession,
        user_role: str,
        current_participant_id: Optional[str] = None,
    ) -> SessionSnapshotData:
        """Construct full state snapshot for a session."""
        now = datetime.now(timezone.utc)
        expires_at = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)
        is_expired = now > expires_at

        active_participants = [p for p in session.participants if p.left_at is None]

        participants_public = [
            ParticipantPublic(
                id=p.id,
                display_name=p.display_name,
                latitude=p.latitude,
                longitude=p.longitude,
                location_submitted=p.location_submitted,
                is_online=manager.is_participant_online(session.id, p.id),
                joined_at=p.joined_at,
            )
            for p in active_participants
        ]

        latest_result = None
        if session.optimizations:
            try:
                latest_result = json.loads(session.optimizations[0].result_json)
            except Exception:
                pass

        session_public = SessionPublicResponse(
            session_id=session.id,
            invitation_code=session.invitation_code,
            title=session.title,
            description=session.description,
            status=session.status,
            network_type=session.network_type,
            optimization_objective=session.optimization_objective,
            top_k=session.top_k,
            result_is_stale=session.result_is_stale,
            expires_at=session.expires_at,
            created_at=session.created_at,
            participants_count=len(active_participants),
            is_expired=is_expired,
        )

        return SessionSnapshotData(
            session=session_public,
            participants=participants_public,
            latest_result=latest_result,
            user_role=user_role,
            current_participant_id=current_participant_id,
        )

    async def mark_expired_sessions(self, db: AsyncSession) -> list[str]:
        """Find active sessions that passed expires_at, mark them closed, broadcast closure and disconnect sockets."""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(MeetingSession).where(
                MeetingSession.status == "active",
                MeetingSession.expires_at < now,
            )
        )
        expired_sessions = list(result.scalars().all())
        closed_ids: list[str] = []

        for session in expired_sessions:
            session.status = "closed"
            session.closed_at = now
            closed_ids.append(session.id)

        if closed_ids:
            await db.commit()
            for session_id in closed_ids:
                # Broadcast session_closed
                await manager.broadcast(
                    session_id,
                    {
                        "type": "session_closed",
                        "data": {
                            "closed_at": now.isoformat(),
                            "message": "This meeting session has expired and is now closed.",
                        },
                    },
                )
                # Disconnect active WebSockets in that room
                await manager.close_room(session_id, code=4003, reason="Session expired and closed")
        return closed_ids

    async def purge_retained_sessions(self, db: AsyncSession, retention_hours: int = 48) -> int:
        """Permanently delete sessions older than retention_hours (cascades to participants & optimizations)."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=retention_hours)
        result = await db.execute(
            select(MeetingSession).where(
                MeetingSession.status == "closed",
                or_(
                    MeetingSession.closed_at < cutoff,
                    MeetingSession.expires_at < cutoff,
                ),
            )
        )
        retained = list(result.scalars().all())
        count = len(retained)
        for s in retained:
            await db.delete(s)
        if count > 0:
            await db.commit()
            logger.info("Purged %d expired sessions older than retention window (%dh)", count, retention_hours)
        return count

    async def run_cleanup(self, db: AsyncSession, retention_hours: int | None = None) -> dict[str, Any]:
        """Execute full expiration check and retention purge cycle."""
        hours = retention_hours if retention_hours is not None else settings.SESSION_RETENTION_HOURS
        closed = await self.mark_expired_sessions(db)
        purged = await self.purge_retained_sessions(db, retention_hours=hours)
        return {
            "closed_sessions_count": len(closed),
            "purged_sessions_count": purged,
            "closed_session_ids": closed,
        }


session_service = SessionService()
