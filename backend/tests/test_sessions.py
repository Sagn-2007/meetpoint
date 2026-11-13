"""Automated tests for collaborative meeting sessions, permissions, and location lifecycle."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import hash_token
from app.models.geometry import BoundingBox, Coordinate
from app.models.schemas import (
    CandidateRecommendation,
    OptimizationMetadata,
    OptimizationObjective,
    OptimizeMeetingResponse,
    ParticipantRouteResult,
)


@pytest.fixture
def mock_optimization_result() -> OptimizeMeetingResponse:
    """Fixture returning a mock OptimizeMeetingResponse for fast, deterministic testing."""
    return OptimizeMeetingResponse(
        optimal_node_id=2,
        optimal_location=Coordinate(latitude=22.505, longitude=88.305),
        objective=OptimizationObjective.MEDIAN,
        aggregate_distance_m=1500.0,
        max_distance_m=800.0,
        avg_distance_m=750.0,
        individual_distances=[
            ParticipantRouteResult(
                participant_id="p-1",
                label="Alice",
                original_latitude=22.50,
                original_longitude=88.30,
                snapped_node_id=1,
                snapped_latitude=22.50,
                snapped_longitude=88.30,
                snap_distance_m=0.0,
                route_distance_m=700.0,
                route_node_ids=[1, 2],
                route_coordinates=[Coordinate(latitude=22.50, longitude=88.30), Coordinate(latitude=22.505, longitude=88.305)],
                segment_count=1,
            ),
            ParticipantRouteResult(
                participant_id="p-2",
                label="Bob",
                original_latitude=22.51,
                original_longitude=88.31,
                snapped_node_id=3,
                snapped_latitude=22.51,
                snapped_longitude=88.31,
                snap_distance_m=0.0,
                route_distance_m=800.0,
                route_node_ids=[3, 2],
                route_coordinates=[Coordinate(latitude=22.51, longitude=88.31), Coordinate(latitude=22.505, longitude=88.305)],
                segment_count=1,
            ),
        ],
        candidates=[
            CandidateRecommendation(
                rank=1,
                node_id=2,
                location=Coordinate(latitude=22.505, longitude=88.305),
                aggregate_distance_m=1500.0,
                max_distance_m=800.0,
                avg_distance_m=750.0,
            )
        ],
        metadata=OptimizationMetadata(
            network_type="walk",
            total_network_nodes=3,
            total_network_edges=4,
            candidate_nodes_evaluated=3,
            execution_time_ms=12.5,
            cache_hit=False,
            bounding_box=BoundingBox(min_lat=22.4, max_lat=22.6, min_lon=88.2, max_lon=88.4),
            objective=OptimizationObjective.MEDIAN,
            top_k=5,
        ),
    )


def test_create_session(api_client: TestClient) -> None:
    """Test creating a collaborative session."""
    payload = {
        "title": "Strategy Sync",
        "description": "Quarterly planning meeting",
        "network_type": "walk",
        "optimization_objective": "median",
        "top_k": 5,
    }
    response = api_client.post("/api/v1/sessions", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data["title"] == "Strategy Sync"
    assert data["description"] == "Quarterly planning meeting"
    assert len(data["invitation_code"]) == 8
    assert "host_token" in data
    assert len(data["host_token"]) >= 32
    assert "session_id" in data


def test_invitation_code_uniqueness(api_client: TestClient) -> None:
    """Ensure generated invitation codes are distinct."""
    codes = set()
    for i in range(5):
        resp = api_client.post("/api/v1/sessions", json={"title": f"Meeting {i}"})
        assert resp.status_code == status.HTTP_201_CREATED
        code = resp.json()["invitation_code"]
        assert code not in codes
        codes.add(code)


def test_get_session_by_code(api_client: TestClient) -> None:
    """Retrieve public session details by invitation code."""
    create_resp = api_client.post("/api/v1/sessions", json={"title": "Coffee Break"})
    data = create_resp.json()
    code = data["invitation_code"]

    get_resp = api_client.get(f"/api/v1/sessions/{code}")
    assert get_resp.status_code == status.HTTP_200_OK
    session_info = get_resp.json()

    assert session_info["title"] == "Coffee Break"
    assert session_info["session_id"] == data["session_id"]
    assert "host_token" not in session_info
    assert session_info["participants_count"] == 0
    assert not session_info["is_expired"]


def test_join_session_and_token_generation(api_client: TestClient) -> None:
    """Join session as participant and receive unique credentials."""
    create_resp = api_client.post("/api/v1/sessions", json={"title": "Team Lunch"})
    code = create_resp.json()["invitation_code"]

    join_payload = {"display_name": "Alice"}
    join_resp = api_client.post(f"/api/v1/sessions/{code}/join", json=join_payload)
    assert join_resp.status_code == status.HTTP_201_CREATED
    participant = join_resp.json()

    assert participant["display_name"] == "Alice"
    assert "participant_token" in participant
    assert "participant_id" in participant
    assert participant["location_submitted"] is False


def test_join_with_initial_location(api_client: TestClient) -> None:
    """Join session with explicit coordinates provided during join."""
    create_resp = api_client.post("/api/v1/sessions", json={"title": "Hackathon Meet"})
    code = create_resp.json()["invitation_code"]

    join_payload = {
        "display_name": "Bob",
        "latitude": 22.5726,
        "longitude": 88.3639,
    }
    join_resp = api_client.post(f"/api/v1/sessions/{code}/join", json=join_payload)
    assert join_resp.status_code == status.HTTP_201_CREATED
    data = join_resp.json()
    assert data["location_submitted"] is True
    assert data["latitude"] == 22.5726
    assert data["longitude"] == 88.3639


def test_submit_and_withdraw_location(api_client: TestClient) -> None:
    """Participant submits coordinates then explicitly withdraws them."""
    create_resp = api_client.post("/api/v1/sessions", json={"title": "Project Standup"})
    code = create_resp.json()["invitation_code"]
    session_id = create_resp.json()["session_id"]

    join_resp = api_client.post(f"/api/v1/sessions/{code}/join", json={"display_name": "Charlie"})
    p_token = join_resp.json()["participant_token"]

    # Submit location
    loc_payload = {"latitude": 22.500, "longitude": 88.300, "token": p_token}
    loc_resp = api_client.post(f"/api/v1/sessions/{session_id}/location", json=loc_payload)
    assert loc_resp.status_code == status.HTTP_200_OK
    assert loc_resp.json()["location_submitted"] is True

    # Withdraw location
    withdraw_resp = api_client.delete(
        f"/api/v1/sessions/{session_id}/location",
        headers={"X-Session-Token": p_token},
    )
    assert withdraw_resp.status_code == status.HTTP_200_OK
    assert withdraw_resp.json()["location_submitted"] is False
    assert withdraw_resp.json()["latitude"] is None


def test_host_settings_update_and_authorization(api_client: TestClient) -> None:
    """Only host can update session settings; unauthorized callers are rejected."""
    create_resp = api_client.post("/api/v1/sessions", json={"title": "Original Title"})
    session_id = create_resp.json()["session_id"]
    code = create_resp.json()["invitation_code"]
    host_token = create_resp.json()["host_token"]

    join_resp = api_client.post(f"/api/v1/sessions/{code}/join", json={"display_name": "Dave"})
    participant_token = join_resp.json()["participant_token"]

    # Participant attempt (should fail 403)
    update_payload = {"title": "Participant Hijack"}
    fail_resp = api_client.patch(
        f"/api/v1/sessions/{session_id}/settings",
        json=update_payload,
        headers={"X-Session-Token": participant_token},
    )
    assert fail_resp.status_code == status.HTTP_403_FORBIDDEN

    # Host update (should succeed)
    host_resp = api_client.patch(
        f"/api/v1/sessions/{session_id}/settings",
        json={"title": "Updated Title", "top_k": 10},
        headers={"X-Session-Token": host_token},
    )
    assert host_resp.status_code == status.HTTP_200_OK
    assert host_resp.json()["title"] == "Updated Title"
    assert host_resp.json()["top_k"] == 10


def test_host_remove_participant(api_client: TestClient) -> None:
    """Host can remove participant; participant cannot remove others."""
    create_resp = api_client.post("/api/v1/sessions", json={"title": "Moderated Meeting"})
    session_id = create_resp.json()["session_id"]
    code = create_resp.json()["invitation_code"]
    host_token = create_resp.json()["host_token"]

    join_resp1 = api_client.post(f"/api/v1/sessions/{code}/join", json={"display_name": "Eve"})
    p1_id = join_resp1.json()["participant_id"]

    join_resp2 = api_client.post(f"/api/v1/sessions/{code}/join", json={"display_name": "Frank"})
    p2_token = join_resp2.json()["participant_token"]

    # Frank tries to remove Eve (should fail 403)
    del_fail = api_client.delete(
        f"/api/v1/sessions/{session_id}/participants/{p1_id}",
        headers={"X-Session-Token": p2_token},
    )
    assert del_fail.status_code == status.HTTP_403_FORBIDDEN

    # Host removes Eve (should succeed)
    del_ok = api_client.delete(
        f"/api/v1/sessions/{session_id}/participants/{p1_id}",
        headers={"X-Session-Token": host_token},
    )
    assert del_ok.status_code == status.HTTP_200_OK

    # Eve should no longer count in active participants
    get_resp = api_client.get(f"/api/v1/sessions/{code}")
    assert get_resp.json()["participants_count"] == 1


def test_participant_leave_and_host_close(api_client: TestClient) -> None:
    """Participant can leave session; host can close session."""
    create_resp = api_client.post("/api/v1/sessions", json={"title": "Closing Test"})
    session_id = create_resp.json()["session_id"]
    code = create_resp.json()["invitation_code"]
    host_token = create_resp.json()["host_token"]

    join_resp = api_client.post(f"/api/v1/sessions/{code}/join", json={"display_name": "Grace"})
    p_token = join_resp.json()["participant_token"]

    # Grace leaves
    leave_resp = api_client.post(
        f"/api/v1/sessions/{session_id}/leave",
        headers={"X-Session-Token": p_token},
    )
    assert leave_resp.status_code == status.HTTP_200_OK

    # Host closes session
    close_resp = api_client.post(
        f"/api/v1/sessions/{session_id}/close",
        headers={"X-Session-Token": host_token},
    )
    assert close_resp.status_code == status.HTTP_200_OK

    # Joining closed session fails
    join_after_close = api_client.post(f"/api/v1/sessions/{code}/join", json={"display_name": "Latecomer"})
    assert join_after_close.status_code == status.HTTP_400_BAD_REQUEST


def test_optimization_requires_at_least_two_participants(api_client: TestClient) -> None:
    """Optimization fails with 400 if fewer than 2 participants have submitted locations."""
    create_resp = api_client.post("/api/v1/sessions", json={"title": "Underpopulated Meeting"})
    session_id = create_resp.json()["session_id"]
    code = create_resp.json()["invitation_code"]
    host_token = create_resp.json()["host_token"]

    # 0 participants
    resp0 = api_client.post(
        f"/api/v1/sessions/{session_id}/optimize",
        headers={"X-Session-Token": host_token},
    )
    assert resp0.status_code == status.HTTP_400_BAD_REQUEST

    # 1 participant with location
    api_client.post(
        f"/api/v1/sessions/{code}/join",
        json={"display_name": "Solo", "latitude": 22.50, "longitude": 88.30},
    )
    resp1 = api_client.post(
        f"/api/v1/sessions/{session_id}/optimize",
        headers={"X-Session-Token": host_token},
    )
    assert resp1.status_code == status.HTTP_400_BAD_REQUEST


def test_optimization_and_staleness_lifecycle(
    api_client: TestClient,
    mock_optimization_result: OptimizeMeetingResponse,
) -> None:
    """Test full optimization cycle, result persistence, and staleness marking on location change."""
    create_resp = api_client.post("/api/v1/sessions", json={"title": "Full Lifecycle Sync"})
    session_id = create_resp.json()["session_id"]
    code = create_resp.json()["invitation_code"]
    host_token = create_resp.json()["host_token"]

    # 2 participants join with locations
    j1 = api_client.post(f"/api/v1/sessions/{code}/join", json={"display_name": "P1", "latitude": 22.50, "longitude": 88.30})
    p1_token = j1.json()["participant_token"]
    api_client.post(f"/api/v1/sessions/{code}/join", json={"display_name": "P2", "latitude": 22.51, "longitude": 88.31})

    # Host triggers optimize
    with patch(
        "app.services.session_service.optimization_service.optimize_meeting_location",
        return_value=mock_optimization_result,
    ):
        opt_resp = api_client.post(
            f"/api/v1/sessions/{session_id}/optimize",
            headers={"X-Session-Token": host_token},
        )
        assert opt_resp.status_code == status.HTTP_200_OK
        opt_data = opt_resp.json()
        assert opt_data["aggregate_distance_m"] == 1500.0

    # Get results endpoint
    results_resp = api_client.get(f"/api/v1/sessions/{session_id}/results")
    assert results_resp.status_code == status.HTTP_200_OK
    res_data = results_resp.json()
    assert res_data["has_result"] is True
    assert res_data["result_is_stale"] is False
    assert res_data["result"]["aggregate_distance_m"] == 1500.0

    # P1 changes location -> marks result as stale!
    api_client.post(
        f"/api/v1/sessions/{session_id}/location",
        json={"latitude": 22.505, "longitude": 88.305, "token": p1_token},
    )

    stale_check = api_client.get(f"/api/v1/sessions/{session_id}/results")
    assert stale_check.status_code == status.HTTP_200_OK
    assert stale_check.json()["result_is_stale"] is True


def test_token_hashing_security(api_client: TestClient) -> None:
    """Verify that plaintext tokens are never stored in the database."""
    from app.db.models.session_models import MeetingSession, SessionParticipant
    from app.db.session import AsyncSessionLocal
    import asyncio

    create_resp = api_client.post("/api/v1/sessions", json={"title": "Security Check"})
    data = create_resp.json()
    session_id = data["session_id"]
    code = data["invitation_code"]
    raw_host_token = data["host_token"]

    join_resp = api_client.post(f"/api/v1/sessions/{code}/join", json={"display_name": "Auditor"})
    raw_p_token = join_resp.json()["participant_token"]
    p_id = join_resp.json()["participant_id"]

    async def verify_db():
        async with AsyncSessionLocal() as session:
            db_session = await session.get(MeetingSession, session_id)
            assert db_session is not None
            # Plaintext host token must NOT equal the stored hash
            assert db_session.host_token_hash != raw_host_token
            assert db_session.host_token_hash == hash_token(raw_host_token)

            db_participant = await session.get(SessionParticipant, p_id)
            assert db_participant is not None
            # Plaintext participant token must NOT equal the stored hash
            assert db_participant.participant_token_hash != raw_p_token
            assert db_participant.participant_token_hash == hash_token(raw_p_token)

    asyncio.run(verify_db())
