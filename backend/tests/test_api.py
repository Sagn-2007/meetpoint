"""End-to-end integration tests for FastAPI endpoints."""

from fastapi.testclient import TestClient

from app.models.geometry import BoundingBox
from app.services.network_service import network_service


def test_health_check_endpoint(api_client: TestClient):
    """GET /health must return 200 and healthy status."""
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "meetpoint-engine"
    assert "version" in data


def test_network_info_endpoint(api_client: TestClient):
    """GET /api/v1/network/info must return 200 and network cache statistics."""
    response = api_client.get("/api/v1/network/info")
    assert response.status_code == 200
    data = response.json()
    assert "cached_networks_count" in data
    assert "default_network_type" in data
    assert "cache_directory" in data
    assert "cached_files" in data


def test_optimize_endpoint_with_registered_graph(api_client: TestClient, synthetic_line_graph):
    """
    POST /api/v1/meeting/optimize using a pre-registered synthetic graph in network_service cache.
    """
    bbox = BoundingBox(min_lat=22.45, min_lon=88.25, max_lat=22.55, max_lon=88.35)
    cache_key = network_service.get_cache_key(bbox, "drive")
    network_service.register_graph(cache_key, synthetic_line_graph)

    payload = {
        "participants": [
            {"id": "p1", "latitude": 22.50, "longitude": 88.30, "label": "Participant 1"},
            {"id": "p2", "latitude": 22.50, "longitude": 88.31, "label": "Participant 2"},
            {"id": "p3", "latitude": 22.50, "longitude": 88.32, "label": "Participant 3"},
        ],
        "bounding_box": {
            "min_lat": 22.45,
            "min_lon": 88.25,
            "max_lat": 22.55,
            "max_lon": 88.35,
        },
        "network_type": "drive",
    }

    response = api_client.post("/api/v1/meeting/optimize", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["optimal_node_id"] == 2
    assert data["optimal_location"]["latitude"] == 22.50
    assert data["optimal_location"]["longitude"] == 88.31
    assert data["aggregate_distance_m"] == 2000.0
    assert data["max_distance_m"] == 1000.0
    assert round(data["avg_distance_m"], 2) == 666.67
    assert len(data["individual_distances"]) == 3
    assert data["metadata"]["candidate_nodes_evaluated"] == 3


def test_optimize_endpoint_auto_bbox_generation(api_client: TestClient, synthetic_line_graph):
    """
    POST /api/v1/meeting/optimize when bounding_box is omitted:
    The engine should compute the bounding box automatically from participant coordinates.
    """
    # Calculate what auto-bbox will be generated
    from app.models.geometry import Coordinate
    coords = [Coordinate(latitude=22.50, longitude=88.30), Coordinate(latitude=22.50, longitude=88.32)]
    auto_bbox = BoundingBox.from_coordinates(coords, padding_ratio=0.20, min_padding_deg=0.015)
    cache_key = network_service.get_cache_key(auto_bbox, "drive")
    network_service.register_graph(cache_key, synthetic_line_graph)

    payload = {
        "participants": [
            {"id": "p1", "latitude": 22.50, "longitude": 88.30},
            {"id": "p2", "latitude": 22.50, "longitude": 88.32},
        ],
        "network_type": "drive",
    }

    response = api_client.post("/api/v1/meeting/optimize", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["optimal_node_id"] in [1, 2, 3]
    assert data["metadata"]["cache_hit"] is True


def test_optimize_endpoint_validation_error_fewer_participants(api_client: TestClient):
    """Validation error: fewer than 2 participants."""
    payload = {
        "participants": [
            {"id": "solo", "latitude": 22.50, "longitude": 88.30},
        ],
    }
    response = api_client.post("/api/v1/meeting/optimize", json=payload)
    assert response.status_code == 422


def test_optimize_endpoint_invalid_coordinates(api_client: TestClient):
    """Validation error: latitude > 90."""
    payload = {
        "participants": [
            {"id": "p1", "latitude": 95.0, "longitude": 88.30},
            {"id": "p2", "latitude": 22.50, "longitude": 88.32},
        ],
    }
    response = api_client.post("/api/v1/meeting/optimize", json=payload)
    assert response.status_code == 422


def test_optimize_endpoint_disconnected_network(api_client: TestClient, synthetic_disconnected_graph):
    """Unprocessable Entity 422 when participants are on disconnected network components."""
    bbox = BoundingBox(min_lat=22.40, min_lon=88.20, max_lat=22.70, max_lon=88.50)
    cache_key = network_service.get_cache_key(bbox, "walk")
    network_service.register_graph(cache_key, synthetic_disconnected_graph)

    payload = {
        "participants": [
            {"id": "p1", "latitude": 22.50, "longitude": 88.30},  # Component A
            {"id": "p2", "latitude": 22.60, "longitude": 88.40},  # Component B
        ],
        "bounding_box": {
            "min_lat": 22.40,
            "min_lon": 88.20,
            "max_lat": 22.70,
            "max_lon": 88.50,
        },
    }
    response = api_client.post("/api/v1/meeting/optimize", json=payload)
    assert response.status_code == 422
    assert "No candidate meeting point is reachable" in response.text


def test_optimize_endpoint_snapping_error_out_of_bounds(api_client: TestClient, synthetic_line_graph):
    """Snapping error 422 when participant exceeds max snapping distance."""
    bbox = BoundingBox(min_lat=22.45, min_lon=88.25, max_lat=22.55, max_lon=88.35)
    cache_key = network_service.get_cache_key(bbox, "walk")
    network_service.register_graph(cache_key, synthetic_line_graph)

    payload = {
        "participants": [
            {"id": "p1", "latitude": 22.50, "longitude": 88.30},
            {"id": "p2", "latitude": 25.00, "longitude": 90.00},  # Very far away
        ],
        "bounding_box": {
            "min_lat": 22.45,
            "min_lon": 88.25,
            "max_lat": 22.55,
            "max_lon": 88.35,
        },
        "max_snap_distance_m": 500.0,
    }
    response = api_client.post("/api/v1/meeting/optimize", json=payload)
    assert response.status_code == 422
    assert "too far" in response.text
