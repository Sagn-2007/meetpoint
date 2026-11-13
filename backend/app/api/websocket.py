"""WebSocket endpoint for real-time collaborative session updates."""

from __future__ import annotations

import json
from typing import Optional
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.session_schemas import ParticipantPublic
from app.services.connection_manager import manager
from app.services.session_service import session_service

router = APIRouter(tags=["WebSocket"])


@router.websocket("/sessions/{session_id}/ws")
async def session_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None),
) -> None:
    """
    Real-time bidirectional WebSocket endpoint for collaborative sessions.
    Authenticates hosts and participants, emits initial state snapshot,
    and synchronizes state changes across all clients in the room.
    """
    # Authenticate before accepting or accept and verify
    async with AsyncSessionLocal() as db:
        try:
            session = await session_service.get_session_by_id(db, session_id)
        except Exception:
            # Session not found or error
            await websocket.close(code=4004, reason="Session not found")
            return

        role, participant = session_service.authenticate_token(session, token or "")
        if role not in ("HOST", "PARTICIPANT"):
            await websocket.close(code=4003, reason="Unauthorized: Valid host or participant token required")
            return

        participant_id = participant.id if participant else None

        # If participant joined, set is_online = True
        if participant:
            participant.is_online = True
            await db.commit()

        # Connect to connection manager
        await manager.connect(
            session_id=session_id,
            websocket=websocket,
            participant_id=participant_id,
            role=role,
        )

        # Send initial full state snapshot to the connecting client
        snapshot = session_service.build_snapshot(
            session=session,
            user_role=role,
            current_participant_id=participant_id,
        )
        await manager.send_personal(
            websocket,
            {
                "type": "session_snapshot",
                "data": snapshot.model_dump(mode="json"),
            },
        )

        # Notify other room members that participant is online
        if participant:
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
                session_id,
                {
                    "type": "participant_updated",
                    "data": participant_public.model_dump(mode="json"),
                },
                exclude=websocket,
            )

    # Listen loop for incoming messages (e.g. ping/pong, heartbeat)
    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                msg = json.loads(raw_message)
                msg_type = msg.get("type")
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
            except Exception:
                # Non-JSON or ignored message
                pass
    except WebSocketDisconnect:
        logger.info("Client disconnected from session %s", session_id)
    except Exception as e:
        logger.warning("WebSocket exception for session %s: %s", session_id, e)
    finally:
        await manager.disconnect(websocket)
        # Update participant online status if no remaining connections
        if participant_id:
            is_still_online = manager.is_participant_online(session_id, participant_id)
            if not is_still_online:
                try:
                    async with AsyncSessionLocal() as db:
                        p_session = await session_service.get_session_by_id(db, session_id)
                        for p in p_session.participants:
                            if p.id == participant_id:
                                p.is_online = False
                                await db.commit()
                                participant_public = ParticipantPublic(
                                    id=p.id,
                                    display_name=p.display_name,
                                    latitude=p.latitude,
                                    longitude=p.longitude,
                                    location_submitted=p.location_submitted,
                                    is_online=False,
                                    joined_at=p.joined_at,
                                )
                                await manager.broadcast(
                                    session_id,
                                    {
                                        "type": "participant_updated",
                                        "data": participant_public.model_dump(mode="json"),
                                    },
                                )
                                break
                except Exception as e:
                    logger.warning("Error updating offline status: %s", e)
