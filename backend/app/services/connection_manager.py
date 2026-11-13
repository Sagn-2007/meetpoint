"""WebSocket connection manager for real-time collaborative sessions."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Set
from fastapi import WebSocket

from app.core.logging import logger


class ConnectionManager:
    """Manages active WebSocket connections grouped by session ID."""

    def __init__(self) -> None:
        # session_id -> Set of WebSockets
        self._rooms: Dict[str, Set[WebSocket]] = {}
        # websocket -> (session_id, participant_id)
        self._socket_meta: Dict[WebSocket, Dict[str, Optional[str]]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        session_id: str,
        websocket: WebSocket,
        participant_id: Optional[str] = None,
        role: str = "VIEWER",
    ) -> None:
        """Accept WebSocket connection and register it in the session room."""
        await websocket.accept()
        async with self._lock:
            if session_id not in self._rooms:
                self._rooms[session_id] = set()
            self._rooms[session_id].add(websocket)
            self._socket_meta[websocket] = {
                "session_id": session_id,
                "participant_id": participant_id,
                "role": role,
            }
        logger.info(
            "WebSocket connected to session %s (role=%s, participant_id=%s, total=%d)",
            session_id,
            role,
            participant_id,
            len(self._rooms.get(session_id, set())),
        )

    async def disconnect(self, websocket: WebSocket) -> Optional[Dict[str, Optional[str]]]:
        """Remove WebSocket connection from session room and clean up."""
        meta = None
        async with self._lock:
            meta = self._socket_meta.pop(websocket, None)
            if meta:
                session_id = meta.get("session_id")
                if session_id and session_id in self._rooms:
                    self._rooms[session_id].discard(websocket)
                    if not self._rooms[session_id]:
                        del self._rooms[session_id]
        if meta:
            logger.info(
                "WebSocket disconnected from session %s (participant_id=%s)",
                meta.get("session_id"),
                meta.get("participant_id"),
            )
        return meta

    def is_participant_online(self, session_id: str, participant_id: str) -> bool:
        """Check if any active WebSocket belongs to the given participant."""
        for ws, meta in self._socket_meta.items():
            if meta.get("session_id") == session_id and meta.get("participant_id") == participant_id:
                return True
        return False

    async def broadcast(
        self,
        session_id: str,
        message: Dict[str, Any],
        exclude: Optional[WebSocket] = None,
    ) -> None:
        """Broadcast JSON message to active clients in a session, optionally excluding one."""
        async with self._lock:
            sockets = [s for s in self._rooms.get(session_id, set()) if s != exclude]

        if not sockets:
            return

        dead_sockets: List[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_json(message)
            except Exception as e:
                logger.warning("Failed to send WebSocket message, scheduling disconnect: %s", e)
                dead_sockets.append(socket)

        if dead_sockets:
            for dead in dead_sockets:
                await self.disconnect(dead)

    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Send message directly to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning("Failed to send personal WebSocket message: %s", e)
            await self.disconnect(websocket)


# Global connection manager singleton
manager = ConnectionManager()
