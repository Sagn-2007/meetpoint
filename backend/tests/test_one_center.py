"""Tests for Network 1-Center optimization, tie-breaking, and Top-K ranking."""

import networkx as nx
import pytest

from app.algorithms.dijkstra import compute_all_participant_distances, to_simple_digraph
from app.algorithms.one_center import solve_network_1_center
from app.algorithms.one_median import solve_network_1_median
from app.core.exceptions import DisconnectedNetworkError


@pytest.fixture
def median_vs_center_graph() -> nx.MultiDiGraph:
    """
    Synthetic graph where 1-Median and 1-Center yield DIFFERENT optimal meeting locations.

    Graph layout:
    Node 1 <---> Node 2 <---> Node 3 <---> Node 4
    Lengths:
      1 <-> 2: 100.0m
      2 <-> 3: 100.0m
      3 <-> 4: 500.0m

    Participants at Nodes 1, 2, and 4:
      - At Node 1: d(P1)=0,   d(P2)=100, d(P3)=700 -> Sum = 800m,  Max = 700m
      - At Node 2: d(P1)=100, d(P2)=0,   d(P3)=600 -> Sum = 700m,  Max = 600m  (Optimal 1-Median!)
      - At Node 3: d(P1)=200, d(P2)=100, d(P3)=500 -> Sum = 800m,  Max = 500m  (Optimal 1-Center!)
      - At Node 4: d(P1)=700, d(P2)=600, d(P3)=0   -> Sum = 1300m, Max = 700m
    """
    G = nx.MultiDiGraph()
    G.graph["crs"] = "EPSG:4326"

    G.add_node(1, y=22.50, x=88.30)
    G.add_node(2, y=22.50, x=88.31)
    G.add_node(3, y=22.50, x=88.32)
    G.add_node(4, y=22.50, x=88.37)

    # 1 <-> 2
    G.add_edge(1, 2, length=100.0)
    G.add_edge(2, 1, length=100.0)

    # 2 <-> 3
    G.add_edge(2, 3, length=100.0)
    G.add_edge(3, 2, length=100.0)

    # 3 <-> 4
    G.add_edge(3, 4, length=500.0)
    G.add_edge(4, 3, length=500.0)

    return G


def test_one_center_vs_one_median_difference(median_vs_center_graph):
    """
    Verify mathematical ground truth that 1-Median and 1-Center produce different optimal nodes.
    1-Median must select Node 2 (Sum=700).
    1-Center must select Node 3 (Max=500).
    """
    simple_g = to_simple_digraph(median_vs_center_graph)
    # Participants at 1, 2, and 4
    dists = compute_all_participant_distances(simple_g, snapped_nodes=[1, 2, 4])

    median_res = solve_network_1_median(simple_g, dists)
    center_res = solve_network_1_center(simple_g, dists)

    # 1-Median optimizes total distance
    assert median_res.optimal_node_id == 2
    assert median_res.aggregate_distance_m == 700.0
    assert median_res.max_distance_m == 600.0

    # 1-Center optimizes worst-case individual distance
    assert center_res.optimal_node_id == 3
    assert center_res.max_distance_m == 500.0
    assert center_res.aggregate_distance_m == 800.0

    # Different optimal meeting points
    assert median_res.optimal_node_id != center_res.optimal_node_id


def test_one_center_first_tie_break_aggregate_distance():
    """
    When two candidates have identical max_distance, the first tie-breaker is aggregate_distance.
    Participants at 1 and 2.
    Candidate A: dists (100, 300) -> Max = 300, Sum = 400
    Candidate B: dists (250, 300) -> Max = 300, Sum = 550
    Candidate A must win because 400 < 550.
    """
    G = nx.DiGraph()
    G.add_node(1, y=22.50, x=88.30)
    G.add_node(2, y=22.50, x=88.35)
    G.add_node("cand_A", y=22.51, x=88.31)
    G.add_node("cand_B", y=22.51, x=88.34)

    G.add_edge(1, "cand_A", length=100.0)
    G.add_edge(2, "cand_A", length=300.0)

    G.add_edge(1, "cand_B", length=250.0)
    G.add_edge(2, "cand_B", length=300.0)

    dists = compute_all_participant_distances(G, snapped_nodes=[1, 2])
    res = solve_network_1_center(G, dists)

    assert res.optimal_node_id == "cand_A"
    assert res.max_distance_m == 300.0
    assert res.aggregate_distance_m == 400.0


def test_one_center_final_tie_break_node_id():
    """
    When two candidates have identical max_distance AND identical aggregate_distance,
    the tie is broken deterministically by node ID string representation.
    Candidate "alpha" and Candidate "beta":
    Both have Max = 200, Sum = 300.
    "alpha" < "beta", so "alpha" must be selected.
    """
    G = nx.DiGraph()
    G.add_node(1, y=22.50, x=88.30)
    G.add_node(2, y=22.50, x=88.35)
    G.add_node("beta", y=22.51, x=88.33)
    G.add_node("alpha", y=22.51, x=88.32)

    G.add_edge(1, "beta", length=100.0)
    G.add_edge(2, "beta", length=200.0)

    G.add_edge(1, "alpha", length=100.0)
    G.add_edge(2, "alpha", length=200.0)

    dists = compute_all_participant_distances(G, snapped_nodes=[1, 2])
    res = solve_network_1_center(G, dists)

    assert res.optimal_node_id == "alpha"
    assert res.max_distance_m == 200.0
    assert res.aggregate_distance_m == 300.0


def test_one_center_disconnected_network(synthetic_disconnected_graph):
    """Disconnected graph must raise DisconnectedNetworkError for 1-Center."""
    simple_g = to_simple_digraph(synthetic_disconnected_graph)
    # 1 in component A, 3 in component B
    dists = compute_all_participant_distances(simple_g, snapped_nodes=[1, 3])

    with pytest.raises(DisconnectedNetworkError) as exc:
        solve_network_1_center(simple_g, dists)
    assert "No candidate meeting point is reachable" in str(exc.value)


def test_one_center_top_k_ranking_and_deduplication(median_vs_center_graph):
    """
    Verify Top-K candidate recommendations are ordered by 1-Center ranking:
    1. Node 3 (Max=500, Sum=800)
    2. Node 2 (Max=600, Sum=700)
    3. Node 1 (Max=700, Sum=800)
    4. Node 4 (Max=700, Sum=1300)
    """
    simple_g = to_simple_digraph(median_vs_center_graph)
    dists = compute_all_participant_distances(simple_g, snapped_nodes=[1, 2, 4])

    res = solve_network_1_center(simple_g, dists, top_k=4)

    assert len(res.ranked_candidates) == 4
    ranks = [c.node_id for c in res.ranked_candidates]
    assert ranks == [3, 2, 1, 4]
    assert res.ranked_candidates[0].rank == 1
    assert res.ranked_candidates[1].rank == 2
    assert res.ranked_candidates[0].node_id == res.optimal_node_id
