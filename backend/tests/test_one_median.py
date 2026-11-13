"""Tests for Network 1-Median optimization, tie-breaking, and disconnected graphs."""

import pytest

from app.algorithms.dijkstra import compute_all_participant_distances, to_simple_digraph
from app.algorithms.one_median import solve_network_1_median
from app.core.exceptions import DisconnectedNetworkError


def test_one_median_three_participants_line_graph(synthetic_line_graph):
    """
    Line graph: 1 <-> 2 <-> 3 with lengths 1000m each.
    Participants at 1, 2, and 3.
    Candidates:
      Node 1: sum = 0 + 1000 + 2000 = 3000m
      Node 2: sum = 1000 + 0 + 1000 = 2000m (optimal)
      Node 3: sum = 2000 + 1000 + 0 = 3000m
    """
    simple_g = to_simple_digraph(synthetic_line_graph)
    dists = compute_all_participant_distances(simple_g, snapped_nodes=[1, 2, 3])

    result = solve_network_1_median(simple_g, participant_distances=dists)

    assert result.optimal_node_id == 2
    assert result.aggregate_distance_m == 2000.0
    assert result.individual_distances_m == [1000.0, 0.0, 1000.0]
    assert result.max_distance_m == 1000.0
    assert pytest.approx(result.avg_distance_m, rel=1e-3) == 666.6667
    assert result.latitude == 22.50
    assert result.longitude == 88.31


def test_one_median_oneway_restrictions(synthetic_oneway_graph):
    """
    One-way graph: 1 -> 2 -> 3 (500m each).
    Participants at 1 and 2.
    Reachable from 1: {1, 2, 3}
    Reachable from 2: {2, 3}
    Common reachable: {2, 3}
    Candidate 2: 500 + 0 = 500m (optimal)
    Candidate 3: 1000 + 500 = 1500m
    """
    simple_g = to_simple_digraph(synthetic_oneway_graph)
    dists = compute_all_participant_distances(simple_g, snapped_nodes=[1, 2])

    result = solve_network_1_median(simple_g, participant_distances=dists)

    assert result.optimal_node_id == 2
    assert result.aggregate_distance_m == 500.0
    assert result.individual_distances_m == [500.0, 0.0]


def test_one_median_disconnected_components(synthetic_disconnected_graph):
    """
    Disconnected graph: Component A (1 <-> 2) and Component B (3 <-> 4).
    Participant 1 at 1, Participant 2 at 3.
    Reachable from 1: {1, 2}
    Reachable from 3: {3, 4}
    Intersection is empty -> DisconnectedNetworkError must be raised.
    """
    simple_g = to_simple_digraph(synthetic_disconnected_graph)
    dists = compute_all_participant_distances(simple_g, snapped_nodes=[1, 3])

    with pytest.raises(DisconnectedNetworkError) as exc:
        solve_network_1_median(simple_g, participant_distances=dists)

    assert "No candidate meeting point is reachable by all participants" in str(exc.value)


def test_one_median_minimax_tie_breaking(synthetic_tiebreak_graph):
    """
    Tie-breaking Rule 1: Minimax fairness.
    Candidate 2 (Node 2): Sum = 200, Max = 100
    Candidate 3 (Node 3): Sum = 200, Max = 150
    Both candidates have aggregate sum of 200. Candidate 2 must win due to lower max distance.
    """
    simple_g = to_simple_digraph(synthetic_tiebreak_graph)
    # Participants at 1 and 4
    dists = compute_all_participant_distances(simple_g, snapped_nodes=[1, 4])

    result = solve_network_1_median(simple_g, participant_distances=dists)

    assert result.optimal_node_id == 2
    assert result.aggregate_distance_m == 200.0
    assert result.max_distance_m == 100.0


def test_one_median_id_tie_breaking(synthetic_id_tiebreak_graph):
    """
    Tie-breaking Rule 2: Deterministic Node ID sorting.
    Candidate 10 and Candidate 20:
    Both have aggregate distance = 200, and max distance = 100.
    Candidate 10 must win deterministically over Candidate 20.
    """
    simple_g = to_simple_digraph(synthetic_id_tiebreak_graph)
    # Participants at 1 and 2
    dists = compute_all_participant_distances(simple_g, snapped_nodes=[1, 2])

    result = solve_network_1_median(simple_g, participant_distances=dists)

    assert result.optimal_node_id == 10
    assert result.aggregate_distance_m == 200.0
    assert result.max_distance_m == 100.0
