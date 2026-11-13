"""Tests for comparative optimization, Top-K candidates, and Phase 2 API extensions."""

import pytest
from fastapi.testclient import TestClient

from app.models.geometry import BoundingBox
from app.models.schemas import OptimizationObjective
from app.services.network_service import network_service


def test_api_objective_center(api_client: TestClient, synthetic_line_graph):
    """POST /api/v1/meeting/optimize with objective='center'."""
    bbox = BoundingBox(min_lat=22.45, min_lon=88.25, max_lat=22.55, max_lon=88.35)
    cache_key = network_service.get_cache_key(bbox, "walk")
    network_service.register_graph(cache_key, synthetic_line_graph)

    payload = {
        "participants": [
            {"id": "p1", "latitude": 22.50, "longitude": 88.30},
            {"id": "p2", "latitude": 22.50, "longitude": 88.32},
        ],
        "bounding_box": bbox.model_dump(),
        "objective": "center",
        "top_k": 3,
    }

    response = api_client.post("/api/v1/meeting/optimize", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["objective"] == "center"
    assert data["optimal_node_id"] == 2
    assert len(data["candidates"]) == 3
    assert data["candidates"][0]["rank"] == 1
    assert data["candidates"][0]["node_id"] == data["optimal_node_id"]


def test_api_objective_compare(api_client: TestClient):
    """
    POST /api/v1/meeting/optimize with objective='compare' on graph where median != center.
    """
    import networkx as nx
    G = nx.MultiDiGraph()
    G.graph["crs"] = "EPSG:4326"
    G.add_node(1, y=22.50, x=88.30)
    G.add_node(2, y=22.50, x=88.31)
    G.add_node(3, y=22.50, x=88.32)
    G.add_node(4, y=22.50, x=88.37)

    G.add_edge(1, 2, length=100.0)
    G.add_edge(2, 1, length=100.0)
    G.add_edge(2, 3, length=100.0)
    G.add_edge(3, 2, length=100.0)
    G.add_edge(3, 4, length=500.0)
    G.add_edge(4, 3, length=500.0)

    bbox = BoundingBox(min_lat=22.40, min_lon=88.20, max_lat=22.60, max_lon=88.50)
    cache_key = network_service.get_cache_key(bbox, "walk")
    network_service.register_graph(cache_key, G)

    payload = {
        "participants": [
            {"id": "p1", "latitude": 22.50, "longitude": 88.30},
            {"id": "p2", "latitude": 22.50, "longitude": 88.31},
            {"id": "p3", "latitude": 22.50, "longitude": 88.37},
        ],
        "bounding_box": bbox.model_dump(),
        "objective": "compare",
        "top_k": 4,
    }

    response = api_client.post("/api/v1/meeting/optimize", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["objective"] == "compare"
    assert data["comparison"] is not None

    comp = data["comparison"]
    assert comp["median_node_id"] == 2
    assert comp["center_node_id"] == 3
    assert comp["same_optimal_node"] is False
    assert comp["median_aggregate_distance_m"] == 700.0
    assert comp["center_max_distance_m"] == 500.0
    assert "1-Median minimizes the total distance" in comp["explanation"]

    # Verify both detailed objective results
    assert data["median_result"]["optimal_node_id"] == 2
    assert data["center_result"]["optimal_node_id"] == 3
    assert len(data["median_result"]["individual_distances"]) == 3
    assert len(data["center_result"]["individual_distances"]) == 3


def test_api_validation_invalid_objective(api_client: TestClient):
    """Invalid objective string must return HTTP 422."""
    payload = {
        "participants": [
            {"id": "p1", "latitude": 22.50, "longitude": 88.30},
            {"id": "p2", "latitude": 22.50, "longitude": 88.32},
        ],
        "objective": "invalid_mode",
    }
    response = api_client.post("/api/v1/meeting/optimize", json=payload)
    assert response.status_code == 422


def test_api_validation_top_k_bounds(api_client: TestClient):
    """top_k < 1 or > 20 must return HTTP 422."""
    base_payload = {
        "participants": [
            {"id": "p1", "latitude": 22.50, "longitude": 88.30},
            {"id": "p2", "latitude": 22.50, "longitude": 88.32},
        ],
    }

    # top_k = 0
    resp_zero = api_client.post("/api/v1/meeting/optimize", json={**base_payload, "top_k": 0})
    assert resp_zero.status_code == 422

    # top_k = 25 (exceeds max 20)
    resp_exceed = api_client.post("/api/v1/meeting/optimize", json={**base_payload, "top_k": 25})
    assert resp_exceed.status_code == 422


def test_api_network_type_default_walk(api_client: TestClient, synthetic_line_graph):
    """When network_type is not provided, default must be 'walk'."""
    bbox = BoundingBox(min_lat=22.45, min_lon=88.25, max_lat=22.55, max_lon=88.35)
    cache_key = network_service.get_cache_key(bbox, "walk")
    network_service.register_graph(cache_key, synthetic_line_graph)

    payload = {
        "participants": [
            {"id": "p1", "latitude": 22.50, "longitude": 88.30},
            {"id": "p2", "latitude": 22.50, "longitude": 88.32},
        ],
        "bounding_box": bbox.model_dump(),
    }
    response = api_client.post("/api/v1/meeting/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["network_type"] == "walk"


def test_api_network_type_configurable_drive(api_client: TestClient, synthetic_line_graph):
    """When network_type='drive' is provided, it should be honored."""
    bbox = BoundingBox(min_lat=22.45, min_lon=88.25, max_lat=22.55, max_lon=88.35)
    cache_key = network_service.get_cache_key(bbox, "drive")
    network_service.register_graph(cache_key, synthetic_line_graph)

    payload = {
        "participants": [
            {"id": "p1", "latitude": 22.50, "longitude": 88.30},
            {"id": "p2", "latitude": 22.50, "longitude": 88.32},
        ],
        "bounding_box": bbox.model_dump(),
        "network_type": "drive",
    }
    response = api_client.post("/api/v1/meeting/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["network_type"] == "drive"
