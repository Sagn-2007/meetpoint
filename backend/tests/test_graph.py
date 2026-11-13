"""Tests for graph construction, sanitization, spatial snapping, and caching."""

from pathlib import Path
import networkx as nx
import pytest

from app.algorithms.dijkstra import to_simple_digraph
from app.core.exceptions import ParticipantSnappingError
from app.models.geometry import BoundingBox
from app.services.network_service import NetworkService, calculate_haversine_distance
from app.services.snapping_service import SnappingService


def test_haversine_calculation():
    """Haversine distance between two known points."""
    # (0, 0) to (0, 1) on equator is ~111.19 km
    dist = calculate_haversine_distance(0.0, 0.0, 0.0, 1.0)
    assert 111_000 < dist < 112_000


def test_to_simple_digraph_parallel_edges():
    """Simple DiGraph conversion must select the minimum edge length between parallel multiedges."""
    G = nx.MultiDiGraph()
    G.add_node(1, y=22.5, x=88.3)
    G.add_node(2, y=22.6, x=88.4)

    # Add parallel edges with lengths 200, 50, and 120
    G.add_edge(1, 2, length=200.0)
    G.add_edge(1, 2, length=50.0)
    G.add_edge(1, 2, length=120.0)

    simple_g = to_simple_digraph(G, weight="length")

    assert not simple_g.is_multigraph()
    assert simple_g.has_edge(1, 2)
    assert simple_g[1][2]["length"] == 50.0
    assert simple_g.nodes[1]["y"] == 22.5


def test_spatial_snapping_exact_match(synthetic_line_graph):
    """Snapping a coordinate that exactly matches a node should return 0m snap distance."""
    snapping = SnappingService()
    result = snapping.snap_coordinate(synthetic_line_graph, lat=22.50, lon=88.31)

    assert result.node_id == 2
    assert result.snap_distance_m < 1.0


def test_spatial_snapping_offset(synthetic_line_graph):
    """Snapping a coordinate offset slightly from Node 1 should snap to Node 1."""
    snapping = SnappingService()
    # Node 1 is at (22.50, 88.30)
    result = snapping.snap_coordinate(synthetic_line_graph, lat=22.5001, lon=88.3001)

    assert result.node_id == 1
    assert 0 < result.snap_distance_m < 50.0


def test_spatial_snapping_max_distance_exceeded(synthetic_line_graph):
    """Participant too far from any graph node should raise ParticipantSnappingError."""
    snapping = SnappingService()
    # Point at (30.0, 95.0) is hundreds of km away from the synthetic nodes around (22.50, 88.30)
    with pytest.raises(ParticipantSnappingError) as exc:
        snapping.snap_coordinate(
            synthetic_line_graph,
            lat=30.0,
            lon=95.0,
            max_snap_distance_m=1000.0,
        )
    assert "too far" in str(exc.value)


def test_graph_component_info(synthetic_disconnected_graph):
    """Component inspection correctly identifies disconnected components."""
    net_service = NetworkService()
    info = net_service.get_component_info(synthetic_disconnected_graph)

    assert info["node_count"] == 4
    assert info["weakly_connected_components_count"] == 2
    assert not info["is_strongly_connected"]


def test_network_service_caching(tmp_path: Path, synthetic_line_graph):
    """Verify disk saving and cache-hit retrieval."""
    service = NetworkService(cache_dir=tmp_path)
    bbox = BoundingBox(min_lat=22.49, min_lon=88.29, max_lat=22.51, max_lon=88.33)

    cache_key = service.get_cache_key(bbox, "drive")
    service.register_graph(cache_key, synthetic_line_graph)

    # Retrieval from memory cache
    retrieved_g, cache_hit = service.get_road_network(bbox, "drive")
    assert cache_hit is True
    assert retrieved_g.number_of_nodes() == 3

    # Clear memory cache and test disk persistence
    service.clear_cache()
    # Save graph to disk cache
    import osmnx as ox
    ox.save_graphml(synthetic_line_graph, service._get_cache_filepath(cache_key))

    loaded_g, disk_cache_hit = service.get_road_network(bbox, "drive")
    assert disk_cache_hit is True
    assert loaded_g.number_of_nodes() == 3
