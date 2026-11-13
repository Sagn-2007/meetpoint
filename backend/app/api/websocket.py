"""WebSocket endpoint for real-time collaborative session updates."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
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
) -> None:
    """
    Real-time bidirectional WebSocket endpoint for collaborative sessions.
    Authenticates hosts and participants via a mandatory first-message handshake.

    Security specification:
    - Legacy ?token= query parameter is strictly forbidden and rejected with code 4003.
    - Sockets are accepted in an unauthenticated transport state and granted WS_AUTH_TIMEOUT_SECONDS
      to deliver an {"type": "authenticate", "token": "..."} message frame.
    - Unauthenticated sockets are NEVER registered with ConnectionManager and receive NO data.
    - Raw credentials never appear in URLs, access logs, or server telemetry.
    """
    # 1. Strictly forbid legacy query-token credentials to prevent token leakage in access logs
    if "token" in websocket.query_params:
        logger.warning(
            "Rejected WebSocket connection for session %s: query parameter token authentication is forbidden",
            session_id,
        )
        await websocket.close(
            code=4003,
            reason="Query parameter token authentication is forbidden; use first-message handshake",
        )
        return

    # 2. Check session existence and active lifecycle state
    async with AsyncSessionLocal() as db:
        try:
            session = await session_service.get_session_by_id(db, session_id)
        except Exception:
            # Session not found
            await websocket.close(code=4004, reason="Session not found")
            return

        now = datetime.now(timezone.utc)
        expires_at = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)
        if session.status == "closed" or now > expires_at:
            await websocket.close(code=4003, reason="Session is closed or expired")
            return

        # 3. Accept connection at transport level ONLY (not registered in ConnectionManager rooms)
        subprotocol = "meetpoint-auth" if websocket.headers.get("sec-websocket-protocol") == "meetpoint-auth" else None
        await websocket.accept(subprotocol=subprotocol)

        # 4. Enforce first-message authentication handshake within configured timeout
        try:
            raw_auth = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=settings.WS_AUTH_TIMEOUT_SECONDS,
            )
            auth_payload = json.loads(raw_auth)
            if not isinstance(auth_payload, dict) or auth_payload.get("type") != "authenticate":
                await websocket.close(code=4003, reason="First message must be authenticate")
                return
            auth_token = auth_payload.get("token") or auth_payload.get("data", {}).get("token")
            if not auth_token or not isinstance(auth_token, str):
                await websocket.close(code=4003, reason="Missing token in authenticate payload")
                return
        except asyncio.TimeoutError:
            logger.warning("WebSocket auth handshake timed out for session %s", session_id)
            await websocket.close(code=4003, reason="Authentication timeout")
            return
        except Exception:
            await websocket.close(code=4003, reason="Invalid authentication payload")
            return

        # 5. Verify token against database session
        role, participant = session_service.authenticate_token(session, auth_token)
        if role not in ("HOST", "PARTICIPANT"):
            await websocket.close(code=4003, reason="Unauthorized: Valid host or participant token required")
            return

        if role == "PARTICIPANT" and participant and participant.left_at is not None:
            await websocket.close(code=4003, reason="Unauthorized: Participant has left session")
            return

        participant_id = participant.id if participant else None

        # 6. Mark participant online upon verified authentication
        if participant:
            participant.is_online = True
            await db.commit()

        # 7. Register socket with ConnectionManager ONLY after full verification
        await manager.connect(
            session_id=session_id,
            websocket=websocket,
            participant_id=participant_id,
            role=role,
        )

        # 8. Send initial authoritative state snapshot to authenticated client
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

        # 9. Broadcast online status to room members
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
