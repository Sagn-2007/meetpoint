"""Tests for Dijkstra route reconstruction and geometric path extraction."""

import networkx as nx
import pytest

from app.algorithms.dijkstra import (
    compute_all_participant_paths_and_distances,
    compute_single_source_paths_and_distances,
    reconstruct_route_coordinates,
    to_simple_digraph,
)
from app.models.geometry import Coordinate
from app.models.schemas import OptimizeMeetingRequest, Participant
from app.services.optimization_service import optimization_service


def test_single_source_paths_and_distances_line_graph(synthetic_line_graph):
    """Verify Dijkstra returns exact path sequences and distances."""
    simple_g = to_simple_digraph(synthetic_line_graph)

    dists, paths = compute_single_source_paths_and_distances(simple_g, source_node=1)

    # 1 -> 3 must traverse 1 -> 2 -> 3
    assert dists[3] == 2000.0
    assert paths[3] == [1, 2, 3]

    # Reconstruct coordinates sequence
    coords = reconstruct_route_coordinates(simple_g, paths[3])
    assert len(coords) == 3
    assert coords[0] == Coordinate(latitude=22.50, longitude=88.30)
    assert coords[1] == Coordinate(latitude=22.50, longitude=88.31)
    assert coords[2] == Coordinate(latitude=22.50, longitude=88.32)


def test_route_reconstruction_co_located_node(synthetic_line_graph):
    """When participant is already at destination, path has 1 node and 0 segments."""
    simple_g = to_simple_digraph(synthetic_line_graph)
    dists, paths = compute_single_source_paths_and_distances(simple_g, source_node=2)

    assert dists[2] == 0.0
    assert paths[2] == [2]

    coords = reconstruct_route_coordinates(simple_g, paths[2])
    assert len(coords) == 1
    assert coords[0] == Coordinate(latitude=22.50, longitude=88.31)


def test_route_reconstruction_parallel_edges():
    """Route reconstruction must follow the minimum-length edge among parallel multiedges."""
    G = nx.MultiDiGraph()
    G.graph["crs"] = "EPSG:4326"

    G.add_node(1, y=20.0, x=80.0)
    G.add_node(2, y=20.1, x=80.1)

    # Parallel multiedges: 1000m, 150m, 500m
    G.add_edge(1, 2, length=1000.0)
    G.add_edge(1, 2, length=150.0)
    G.add_edge(1, 2, length=500.0)

    simple_g = to_simple_digraph(G)
    dists, paths = compute_single_source_paths_and_distances(simple_g, source_node=1)

    assert dists[2] == 150.0
    assert paths[2] == [1, 2]
    assert simple_g[1][2]["length"] == 150.0


def test_route_reconstruction_one_way_streets(synthetic_oneway_graph):
    """One-way street paths must respect forward directionality and reject backwards paths."""
    simple_g = to_simple_digraph(synthetic_oneway_graph)

    # 1 -> 2 -> 3
    dists_1, paths_1 = compute_single_source_paths_and_distances(simple_g, source_node=1)
    assert paths_1[3] == [1, 2, 3]
    assert dists_1[3] == 1000.0

    # From 3, node 1 is unreachable
    dists_3, paths_3 = compute_single_source_paths_and_distances(simple_g, source_node=3)
    assert 1 not in paths_3
    assert 1 not in dists_3


def test_optimization_service_includes_route_geometry(synthetic_line_graph):
    """The optimization service must return reconstructed routes with coordinates and segment counts."""
    p1 = Participant(id="p1", latitude=22.50, longitude=88.30)  # Node 1
    p2 = Participant(id="p2", latitude=22.50, longitude=88.32)  # Node 3

    req = OptimizeMeetingRequest(participants=[p1, p2])
    resp = optimization_service.optimize_meeting_location(req, custom_graph=synthetic_line_graph)

    # Meeting point at Node 2 (or 1/3)
    assert len(resp.individual_distances) == 2

    # Check route fields
    r1 = resp.individual_distances[0]
    assert len(r1.route_node_ids) >= 1
    assert len(r1.route_coordinates) == len(r1.route_node_ids)
    assert r1.segment_count == len(r1.route_node_ids) - 1
    assert isinstance(r1.route_coordinates[0], Coordinate)
