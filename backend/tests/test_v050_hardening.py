"""Comprehensive test suite for MeetPoint v0.5.0 Production Readiness & Security Hardening."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import networkx as nx
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import Settings, settings
from app.core.exceptions import GeographicSpreadError
from app.core.rate_limit import ClientIpResolver, SlidingWindowRateLimiter, rate_limiter
from app.db.models.session_models import MeetingSession, SessionOptimization, SessionParticipant
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.geometry import BoundingBox, Coordinate
from app.models.schemas import OptimizeMeetingRequest, Participant
from app.services.network_service import BoundedGraphCache, NetworkService
from app.services.optimization_service import optimization_service
from app.services.session_service import session_service


# ==============================================================================
# A1: CORS CONFIGURATION TESTS
# ==============================================================================

def test_cors_configuration_environment_origins() -> None:
    """Test that CORS origins are properly parsed and default localhost is used in dev."""
    # Test custom origins string
    custom_settings = Settings(
        ENVIRONMENT="production",
        CORS_ORIGINS="https://meetpoint.app,https://admin.meetpoint.app",
        DATABASE_URL="postgresql+asyncpg://prod_user:secret_pass@prod-db.example.com/meetpoint",
        SYNC_DATABASE_URL="postgresql+psycopg2://prod_user:secret_pass@prod-db.example.com/meetpoint",
    )
    origins = custom_settings.get_cors_origins()
    assert origins == ["https://meetpoint.app", "https://admin.meetpoint.app"]

    # Test rejection of wildcard origin in production
    wildcard_settings = Settings(
        ENVIRONMENT="production",
        CORS_ORIGINS="*",
        DATABASE_URL="postgresql+asyncpg://prod_user:secret_pass@prod-db.example.com/meetpoint",
        SYNC_DATABASE_URL="postgresql+psycopg2://prod_user:secret_pass@prod-db.example.com/meetpoint",
    )
    with pytest.raises(ValueError, match=r"Wildcard '\*' in MEETPOINT_CORS_ORIGINS is forbidden"):
        wildcard_settings.get_cors_origins()

    # Test development fallback contains localhost
    dev_settings = Settings(ENVIRONMENT="development", CORS_ORIGINS="")
    dev_origins = dev_settings.get_cors_origins()
    assert "http://localhost:5173" in dev_origins


def test_cors_preflight_headers(api_client: TestClient) -> None:
    """Test that OPTIONS preflight returns expected CORS headers."""
    resp = api_client.options(
        "/api/v1/sessions",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,X-Session-Token",
        },
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert resp.headers.get("access-control-allow-credentials") == "true"
    assert "X-Session-Token" in resp.headers.get("access-control-allow-headers", "")


# ==============================================================================
# A2: RATE LIMITING & TRUSTED PROXY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_sliding_window_rate_limiter_enforcement() -> None:
    """Test in-memory sliding window rate limiter triggers 429 when limit exceeded."""
    limiter = SlidingWindowRateLimiter()
    key = "test_ip_1"

    # Should allow 3 requests
    for _ in range(3):
        await limiter.check_rate_limit(key, max_requests=3, window_seconds=60.0)

    # 4th request must raise 429
    with pytest.raises(Exception) as excinfo:
        await limiter.check_rate_limit(key, max_requests=3, window_seconds=60.0)

    from fastapi import HTTPException
    assert isinstance(excinfo.value, HTTPException)
    assert excinfo.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Retry-After" in excinfo.value.headers
    assert excinfo.value.detail["limit"] == 3


def test_trusted_proxy_ip_resolver() -> None:
    """Test that client IP resolver does not trust X-Forwarded-For from untrusted peers."""
    resolver = ClientIpResolver(trusted_proxies_csv="10.0.0.1,172.16.0.0/16")

    class MockRequest:
        def __init__(self, host: str, headers: dict):
            self.client = type("Client", (), {"host": host})()
            self.headers = headers

    # Case 1: Direct untrusted peer attempts spoofing via X-Forwarded-For
    untrusted_req = MockRequest(
        host="203.0.113.50",
        headers={"X-Forwarded-For": "198.51.100.1"},
    )
    assert resolver.resolve_client_ip(untrusted_req) == "203.0.113.50"

    # Case 2: Trusted proxy peer (e.g. 10.0.0.1) forwarding genuine client IP
    trusted_req = MockRequest(
        host="10.0.0.1",
        headers={"X-Forwarded-For": "198.51.100.1, 10.0.0.1"},
    )
    assert resolver.resolve_client_ip(trusted_req) == "198.51.100.1"

    # Case 3: Trusted proxy with CF-Connecting-IP
    cf_req = MockRequest(
        host="10.0.0.1",
        headers={"CF-Connecting-IP": "198.51.100.77"},
    )
    assert resolver.resolve_client_ip(cf_req) == "198.51.100.77"


# ==============================================================================
# A3: WEBSOCKET FIRST-MESSAGE AUTHENTICATION TESTS
# ==============================================================================

def test_websocket_first_message_auth_host(api_client: TestClient) -> None:
    """Host connects via clean WS URL, sends authenticate message, receives snapshot."""
    resp = api_client.post("/api/v1/sessions", json={"title": "Handshake Host Test"})
    data = resp.json()
    session_id = data["session_id"]
    host_token = data["host_token"]

    # Connect with clean WS URL (zero tokens in URL)
    with api_client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
        # Send first-message authenticate frame
        ws.send_json({"type": "authenticate", "token": host_token})

        # Server responds with initial snapshot
        msg = ws.receive_json()
        assert msg["type"] == "session_snapshot"
        assert msg["data"]["user_role"] == "HOST"
        assert msg["data"]["session"]["session_id"] == session_id


def test_websocket_first_message_auth_participant(api_client: TestClient) -> None:
    """Participant connects via clean WS URL, authenticates, and marks online."""
    create_resp = api_client.post("/api/v1/sessions", json={"title": "Handshake Participant Test"})
    invitation_code = create_resp.json()["invitation_code"]
    session_id = create_resp.json()["session_id"]

    join_resp = api_client.post(
        f"/api/v1/sessions/{invitation_code}/join",
        json={"display_name": "Bob Participant"},
    )
    p_token = join_resp.json()["participant_token"]
    p_id = join_resp.json()["participant_id"]

    with api_client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
        ws.send_json({"type": "authenticate", "token": p_token})

        msg = ws.receive_json()
        assert msg["type"] == "session_snapshot"
        assert msg["data"]["user_role"] == "PARTICIPANT"
        assert msg["data"]["current_participant_id"] == p_id


def test_websocket_first_message_invalid_token_rejected(api_client: TestClient) -> None:
    """Connecting via handshake and providing invalid token closes with 4003."""
    resp = api_client.post("/api/v1/sessions", json={"title": "Invalid Token Test"})
    session_id = resp.json()["session_id"]

    with pytest.raises(WebSocketDisconnect) as excinfo:
        with api_client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
            ws.send_json({"type": "authenticate", "token": "invalid_token_xyz"})
            ws.receive_json()
    assert excinfo.value.code == 4003


def test_websocket_first_message_non_authenticate_rejected(api_client: TestClient) -> None:
    """Connecting via clean URL and sending 'ping' before 'authenticate' closes with 4003."""
    resp = api_client.post("/api/v1/sessions", json={"title": "Non-Auth First Msg Test"})
    session_id = resp.json()["session_id"]

    with pytest.raises(WebSocketDisconnect) as excinfo:
        with api_client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
            ws.send_json({"type": "ping"})
            ws.receive_json()
    assert excinfo.value.code == 4003


def test_websocket_legacy_query_token_forbidden(api_client: TestClient) -> None:
    """Attempting to transmit raw credentials via ?token= query parameter is strictly rejected."""
    resp = api_client.post("/api/v1/sessions", json={"title": "Legacy Query Token Test"})
    session_id = resp.json()["session_id"]
    host_token = resp.json()["host_token"]

    with pytest.raises(WebSocketDisconnect) as excinfo:
        with api_client.websocket_connect(f"/api/v1/sessions/{session_id}/ws?token={host_token}"):
            pass
    assert excinfo.value.code == 4003


def test_websocket_closed_session_rejected(api_client: TestClient) -> None:
    """Closed sessions reject WebSocket connection attempts."""
    resp = api_client.post("/api/v1/sessions", json={"title": "Closed Session WS Test"})
    session_id = resp.json()["session_id"]
    host_token = resp.json()["host_token"]

    # Close session
    api_client.post(
        f"/api/v1/sessions/{session_id}/close",
        headers={"X-Session-Token": host_token},
    )

    with pytest.raises(WebSocketDisconnect) as excinfo:
        with api_client.websocket_connect(f"/api/v1/sessions/{session_id}/ws"):
            pass
    assert excinfo.value.code == 4003


# ==============================================================================
# A4: AUTHORIZATION AUDIT TESTS
# ==============================================================================

def test_results_endpoint_token_authorization(api_client: TestClient) -> None:
    """Results endpoint honors member token and rejects invalid credentials."""
    resp = api_client.post("/api/v1/sessions", json={"title": "Auth Audit Results"})
    session_id = resp.json()["session_id"]
    host_token = resp.json()["host_token"]

    # Valid host token succeeds
    res_host = api_client.get(
        f"/api/v1/sessions/{session_id}/results",
        headers={"X-Session-Token": host_token},
    )
    assert res_host.status_code == status.HTTP_200_OK

    # Bogus token fails with 403 Forbidden
    res_bad = api_client.get(
        f"/api/v1/sessions/{session_id}/results",
        headers={"X-Session-Token": "bogus_token_123"},
    )
    assert res_bad.status_code == status.HTTP_403_FORBIDDEN


def test_removed_participant_token_revocation(api_client: TestClient) -> None:
    """When a participant is removed by the host, their token is revoked from future actions."""
    create_resp = api_client.post("/api/v1/sessions", json={"title": "Revocation Test"})
    session_id = create_resp.json()["session_id"]
    code = create_resp.json()["invitation_code"]
    host_token = create_resp.json()["host_token"]

    # Participant joins
    join_resp = api_client.post(
        f"/api/v1/sessions/{code}/join",
        json={"display_name": "Eve Excluded"},
    )
    p_id = join_resp.json()["participant_id"]
    p_token = join_resp.json()["participant_token"]

    # Host removes participant
    del_resp = api_client.delete(
        f"/api/v1/sessions/{session_id}/participants/{p_id}",
        headers={"X-Session-Token": host_token},
    )
    assert del_resp.status_code == status.HTTP_200_OK

    # Eve attempts to submit location using old token -> 403 Forbidden
    loc_resp = api_client.post(
        f"/api/v1/sessions/{session_id}/location",
        json={"latitude": 22.50, "longitude": 88.30, "token": p_token},
    )
    assert loc_resp.status_code == status.HTTP_403_FORBIDDEN


def test_participant_cannot_trigger_host_actions(api_client: TestClient) -> None:
    """Participants cannot update settings, trigger optimization, or close room."""
    create_resp = api_client.post("/api/v1/sessions", json={"title": "Host Action Isolation"})
    session_id = create_resp.json()["session_id"]
    code = create_resp.json()["invitation_code"]

    join_resp = api_client.post(f"/api/v1/sessions/{code}/join", json={"display_name": "Regular User"})
    p_token = join_resp.json()["participant_token"]

    # Participant attempts settings update -> 403
    patch_resp = api_client.patch(
        f"/api/v1/sessions/{session_id}/settings",
        json={"title": "Hacked Title"},
        headers={"X-Session-Token": p_token},
    )
    assert patch_resp.status_code == status.HTTP_403_FORBIDDEN

    # Participant attempts to close session -> 403
    close_resp = api_client.post(
        f"/api/v1/sessions/{session_id}/close",
        headers={"X-Session-Token": p_token},
    )
    assert close_resp.status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# B1: BOUNDED LRU GRAPH CACHE TESTS
# ==============================================================================

def test_bounded_graph_cache_lru_eviction() -> None:
    """LRU memory cache evicts the least recently accessed graph when maxsize is exceeded."""
    cache = BoundedGraphCache(maxsize=3)
    g1, g2, g3, g4 = nx.MultiDiGraph(), nx.MultiDiGraph(), nx.MultiDiGraph(), nx.MultiDiGraph()

    cache.put("k1", g1)
    cache.put("k2", g2)
    cache.put("k3", g3)
    assert len(cache) == 3

    # Access k1 to make it most recently used
    _ = cache.get("k1")

    # Insert k4 -> should evict k2 (oldest), preserving k1, k3, k4
    cache.put("k4", g4)
    assert len(cache) == 3
    assert cache.get("k2") is None
    assert cache.get("k1") is not None
    assert cache.get("k3") is not None
    assert cache.get("k4") is not None


def test_corrupted_graphml_disk_recovery(tmp_path: Path) -> None:
    """Loading a corrupted GraphML file removes the invalid file safely without fatal crash."""
    net_service = NetworkService(cache_dir=tmp_path)
    bbox = BoundingBox(min_lat=22.50, min_lon=88.30, max_lat=22.51, max_lon=88.31)
    cache_key = net_service.get_cache_key(bbox, "walk")
    corrupt_file = tmp_path / f"{cache_key}.graphml"

    # Write corrupt non-XML data
    corrupt_file.write_text("CORRUPT_NOT_XML_GARBAGE")

    with patch("osmnx.graph_from_bbox") as mock_download:
        fake_graph = nx.MultiDiGraph()
        fake_graph.add_node(1, x=88.305, y=22.505)
        fake_graph.add_node(2, x=88.306, y=22.506)
        fake_graph.add_edge(1, 2, length=100.0)
        mock_download.return_value = fake_graph

        graph, hit = net_service.get_road_network(bbox, "walk")
        assert hit is False
        assert len(graph) == 2
        # Corrupt file was replaced or removed
        assert mock_download.called


# ==============================================================================
# B2: OSM BOUNDING BOX & GEOGRAPHIC DISPERSION SAFEGUARDS
# ==============================================================================

def test_geographic_dispersion_safeguard_rejected() -> None:
    """Participants located across wide inter-city distances are rejected with clear error."""
    # Paris and Berlin (~870 km apart)
    req = OptimizeMeetingRequest(
        participants=[
            Participant(id="p1", latitude=48.8566, longitude=2.3522, label="Paris"),
            Participant(id="p2", latitude=52.5200, longitude=13.4050, label="Berlin"),
        ]
    )
    with pytest.raises(GeographicSpreadError) as excinfo:
        optimization_service.optimize_meeting_location(req)

    assert "too geographically dispersed" in excinfo.value.message
    assert excinfo.value.details["limit_km"] == settings.MAX_PARTICIPANT_PAIRWISE_DISTANCE_KM


def test_excessive_bounding_box_diameter_rejected() -> None:
    """Bounding box with diagonal diameter exceeding 80 km is rejected."""
    # Bounding box spanning 200 km
    huge_bbox = BoundingBox(min_lat=20.0, min_lon=80.0, max_lat=22.0, max_lon=82.0)
    req = OptimizeMeetingRequest(
        participants=[
            Participant(id="p1", latitude=20.5, longitude=80.5),
            Participant(id="p2", latitude=20.6, longitude=80.6),
        ],
        bounding_box=huge_bbox,
    )
    with pytest.raises(GeographicSpreadError) as excinfo:
        optimization_service.optimize_meeting_location(req)

    assert "Requested geographic area is too large" in excinfo.value.message


# ==============================================================================
# B3: AUTOMATED SESSION EXPIRATION & PURGE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_session_expiration_and_retention_purge() -> None:
    """Expired sessions are auto-marked closed and aged sessions are purged."""
    import uuid
    async with AsyncSessionLocal() as db:
        # 1. Create a session that expired 1 hour ago
        now = datetime.now(timezone.utc)
        code1 = f"E{uuid.uuid4().hex[:7].upper()}"
        code2 = f"P{uuid.uuid4().hex[:7].upper()}"
        past_expired = MeetingSession(
            title="Expired Auto Test",
            invitation_code=code1,
            host_token_hash="dummy_hash_1",
            status="active",
            created_at=now - timedelta(hours=25),
            expires_at=now - timedelta(hours=1),
        )
        # 2. Create an old session that has been closed longer than retention window (50 hours ago)
        old_retained = MeetingSession(
            title="Purge Candidate Test",
            invitation_code=code2,
            host_token_hash="dummy_hash_2",
            status="closed",
            created_at=now - timedelta(hours=60),
            expires_at=now - timedelta(hours=55),
            closed_at=now - timedelta(hours=50),
        )
        db.add_all([past_expired, old_retained])
        await db.commit()

        # Run cleanup
        cleanup_report = await session_service.run_cleanup(db, retention_hours=48)
        assert past_expired.id in cleanup_report["closed_session_ids"]
        assert cleanup_report["purged_sessions_count"] >= 1

        # Verify past_expired status is now closed
        refreshed = await session_service.get_session_by_id(db, past_expired.id)
        assert refreshed.status == "closed"


# ==============================================================================
# STAGE C & E: DATABASE SAFETY, REQUEST ID, AND HEALTH MONITORING
# ==============================================================================

def test_production_safety_check_blocks_default_credentials() -> None:
    """Settings.validate_production_safety blocks default dev credentials in production."""
    insecure_settings = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql+asyncpg://meetpoint:meetpoint@localhost:5432/meetpoint",
        SYNC_DATABASE_URL="postgresql+psycopg2://meetpoint:meetpoint@localhost:5432/meetpoint",
        CORS_ORIGINS="https://meetpoint.example.com",
    )
    with pytest.raises(ValueError, match="Refusing to start in production environment"):
        insecure_settings.validate_production_safety()


def test_request_id_middleware(api_client: TestClient) -> None:
    """Incoming requests receive an X-Request-ID correlation header in response."""
    resp = api_client.get("/health")
    assert resp.status_code == status.HTTP_200_OK
    assert "X-Request-ID" in resp.headers
    assert len(resp.headers["X-Request-ID"]) >= 8


def test_health_check_database_connectivity(api_client: TestClient) -> None:
    """Health endpoint reports engine status and active database connectivity."""
    resp = api_client.get("/health")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["version"] == settings.VERSION
