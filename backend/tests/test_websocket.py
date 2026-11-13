"""Automated tests for WebSocket real-time synchronization, first-message authentication, and event broadcasting."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


def test_websocket_unauthorized_token_rejected(api_client: TestClient) -> None:
    """Clients attempting to connect without valid credentials or using legacy token queries are rejected with code 4003."""
    # Create session
    resp = api_client.post("/api/v1/sessions", json={"title": "WS Auth Test"})
    session_id = resp.json()["session_id"]

    # 1. Attempting to use legacy ?token= query parameter is strictly forbidden and rejected
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with api_client.websocket_connect(f"/api/v1/sessions/{session_id}/ws?token=some_token"):
            pass
    assert excinfo.value.code == 4003

    # 2. Connect via handshake but send non-authenticate first message (e.g. ping) -> closed 4003
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with api_client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
            ws.send_json({"type": "ping"})
            ws.receive_json()
    assert excinfo.value.code == 4003

    # 3. Connect via handshake but send invalid credentials -> closed 4003
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with api_client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
            ws.send_json({"type": "authenticate", "token": "bogus_token_123"})
            ws.receive_json()
    assert excinfo.value.code == 4003


def test_websocket_nonexistent_session_rejected(api_client: TestClient) -> None:
    """Attempting to connect to nonexistent session is closed with code 4004."""
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with api_client.websocket_connect("/api/v1/sessions/nonexistent-uuid-1234/ws"):
            pass
    assert excinfo.value.code == 4004


def test_websocket_host_receives_snapshot(api_client: TestClient) -> None:
    """Host authenticates via first-message handshake and receives initial full session snapshot."""
    resp = api_client.post("/api/v1/sessions", json={"title": "Host Snapshot Test"})
    session_id = resp.json()["session_id"]
    host_token = resp.json()["host_token"]

    # Connect to clean URL without token query parameters
    with api_client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
        # Deliver first-message authentication handshake
        ws.send_json({"type": "authenticate", "token": host_token})

        msg = ws.receive_json()
        assert msg["type"] == "session_snapshot"
        data = msg["data"]
        assert data["user_role"] == "HOST"
        assert data["session"]["title"] == "Host Snapshot Test"
        assert data["session"]["session_id"] == session_id
        assert isinstance(data["participants"], list)


def test_websocket_participant_receives_snapshot_and_broadcast(api_client: TestClient) -> None:
    """Participant authenticates via handshake, receives snapshot, and room receives online update."""
    resp = api_client.post("/api/v1/sessions", json={"title": "Participant WS Test"})
    session_id = resp.json()["session_id"]
    code = resp.json()["invitation_code"]
    host_token = resp.json()["host_token"]

    join_resp = api_client.post(
        f"/api/v1/sessions/{code}/join",
        json={"display_name": "Maya", "latitude": 22.50, "longitude": 88.30},
    )
    p_token = join_resp.json()["participant_token"]
    p_id = join_resp.json()["participant_id"]

    # Host connects first
    with api_client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as host_ws:
        host_ws.send_json({"type": "authenticate", "token": host_token})
        host_snapshot = host_ws.receive_json()
        assert host_snapshot["type"] == "session_snapshot"

        # Participant connects
        with api_client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as p_ws:
            p_ws.send_json({"type": "authenticate", "token": p_token})

            # Participant receives snapshot
            p_snapshot = p_ws.receive_json()
            assert p_snapshot["type"] == "session_snapshot"
            assert p_snapshot["data"]["user_role"] == "PARTICIPANT"
            assert p_snapshot["data"]["current_participant_id"] == p_id

            # Host should receive participant_updated broadcast notifying participant is online
            host_event = host_ws.receive_json()
            assert host_event["type"] == "participant_updated"
            assert host_event["data"]["id"] == p_id
            assert host_event["data"]["is_online"] is True


def test_websocket_ping_pong(api_client: TestClient) -> None:
    """WebSocket client authenticates, sends ping, and receives pong."""
    resp = api_client.post("/api/v1/sessions", json={"title": "Heartbeat Test"})
    session_id = resp.json()["session_id"]
    host_token = resp.json()["host_token"]

    with api_client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
        ws.send_json({"type": "authenticate", "token": host_token})
        # Discard snapshot
        ws.receive_json()

        # Send ping
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"
