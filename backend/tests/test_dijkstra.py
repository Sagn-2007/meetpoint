"""Tests for Dijkstra shortest-path calculations and one-way road restrictions."""

import networkx as nx
import pytest

from app.algorithms.dijkstra import (
    compute_all_participant_distances,
    compute_single_source_distances,
    to_simple_digraph,
)


def test_dijkstra_line_graph(synthetic_line_graph):
    """Shortest path distances on bidirectional line graph."""
    simple_g = to_simple_digraph(synthetic_line_graph)

    # From Node 1: 1->1 = 0, 1->2 = 1000, 1->3 = 2000
    dists_from_1 = compute_single_source_distances(simple_g, source_node=1)
    assert dists_from_1[1] == 0.0
    assert dists_from_1[2] == 1000.0
    assert dists_from_1[3] == 2000.0

    # From Node 2: 2->1 = 1000, 2->2 = 0, 2->3 = 1000
    dists_from_2 = compute_single_source_distances(simple_g, source_node=2)
    assert dists_from_2[1] == 1000.0
    assert dists_from_2[2] == 0.0
    assert dists_from_2[3] == 1000.0


def test_dijkstra_one_way_restrictions(synthetic_oneway_graph):
    """One-way street restrictions must strictly prevent reverse traversals."""
    simple_g = to_simple_digraph(synthetic_oneway_graph)

    dists_from_1 = compute_single_source_distances(simple_g, source_node=1)
    assert dists_from_1[1] == 0.0
    assert dists_from_1[2] == 500.0
    assert dists_from_1[3] == 1000.0

    # From Node 2: can reach 2 and 3, but CANNOT reach 1
    dists_from_2 = compute_single_source_distances(simple_g, source_node=2)
    assert 1 not in dists_from_2
    assert dists_from_2[2] == 0.0
    assert dists_from_2[3] == 500.0

    # From Node 3: can only reach 3, neither 1 nor 2
    dists_from_3 = compute_single_source_distances(simple_g, source_node=3)
    assert 1 not in dists_from_3
    assert 2 not in dists_from_3
    assert dists_from_3[3] == 0.0


def test_dijkstra_respects_weights_over_hop_count():
    """Dijkstra must pick the minimum total distance path even if it has more hops."""
    G = nx.DiGraph()
    G.add_node(1, y=0.0, x=0.0)
    G.add_node(2, y=0.0, x=1.0)
    G.add_node(3, y=0.0, x=2.0)

    # Direct 1-hop path with high cost: 1 -> 3 (cost 500)
    G.add_edge(1, 3, length=500.0)
    # 2-hop path with low cost: 1 -> 2 (30) -> 3 (40) = 70
    G.add_edge(1, 2, length=30.0)
    G.add_edge(2, 3, length=40.0)

    dists = compute_single_source_distances(G, source_node=1)
    assert dists[3] == 70.0


def test_dijkstra_nonexistent_node():
    """Querying a nonexistent source node must raise KeyError."""
    G = nx.DiGraph()
    G.add_node(1, y=0.0, x=0.0)

    with pytest.raises(KeyError):
        compute_single_source_distances(G, source_node=999)


def test_compute_all_participant_distances_caching(synthetic_line_graph):
    """When multiple participants share a snapped node, Dijkstra is computed only once."""
    simple_g = to_simple_digraph(synthetic_line_graph)
    # 3 participants: two at node 1, one at node 3
    snapped = [1, 1, 3]
    all_dists = compute_all_participant_distances(simple_g, snapped)

    assert len(all_dists) == 3
    # Distance dicts for the first two participants should be identical objects
    assert all_dists[0] is all_dists[1]
    assert all_dists[0][2] == 1000.0
    assert all_dists[2][2] == 1000.0
