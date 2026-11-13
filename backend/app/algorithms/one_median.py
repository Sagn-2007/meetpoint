"""Network 1-Median optimization algorithm on road network graphs."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence
import networkx as nx

from app.core.exceptions import DisconnectedNetworkError
from app.core.logging import logger


@dataclass(frozen=True)
class RankedCandidateInfo:
    """Information for a ranked candidate meeting location."""

    rank: int
    node_id: int | str
    latitude: float
    longitude: float
    aggregate_distance_m: float
    max_distance_m: float
    avg_distance_m: float
    individual_distances_m: list[float]


@dataclass(frozen=True)
class OneMedianResult:
    """Result of the Network 1-Median optimization."""

    optimal_node_id: int | str
    latitude: float
    longitude: float
    aggregate_distance_m: float
    individual_distances_m: list[float]
    max_distance_m: float
    avg_distance_m: float
    eligible_candidate_count: int
    ranked_candidates: list[RankedCandidateInfo] = field(default_factory=list)


def solve_network_1_median(
    graph: nx.DiGraph | nx.MultiDiGraph,
    participant_distances: Sequence[dict[int | str, float]],
    candidate_node_ids: Sequence[int | str] | None = None,
    top_k: int = 5,
) -> OneMedianResult:
    """
    Find the optimal meeting location that minimizes the sum of shortest-path
    travel distances from all participants to the candidate node (Network 1-Median).

    Mathematical objective:
        minimize: SUM(distance(participant_i, candidate))

    Tie-breaking strategy:
        1. Primary: minimize aggregate distance
        2. First tie-breaker: minimize maximum individual distance (minimax fairness)
        3. Final tie-breaker: deterministic node ID string comparison

    Parameters
    ----------
    graph : nx.DiGraph | nx.MultiDiGraph
        Directed graph with spatial node attributes 'y' (latitude) and 'x' (longitude).
    participant_distances : Sequence[dict[int | str, float]]
        List of distance maps from each participant's snapped node to all reachable nodes.
    candidate_node_ids : Sequence[int | str] | None
        Optional subset of nodes to evaluate. If None, all nodes reachable by all participants are evaluated.
    top_k : int, default 5
        Number of ranked candidate recommendations to return.

    Returns
    -------
    OneMedianResult
        Comprehensive optimization results including optimal candidate, distance statistics,
        and top-K ranked alternatives.

    Raises
    ------
    DisconnectedNetworkError
        If there is no candidate node reachable by all participants.
    """
    if not participant_distances:
        raise ValueError("participant_distances list cannot be empty")

    n_participants = len(participant_distances)

    # Eligible candidates MUST be reachable from every single participant
    reachable_sets = [set(d.keys()) for d in participant_distances]
    common_reachable: set[int | str] = set.intersection(*reachable_sets)

    if candidate_node_ids is not None:
        eligible_candidates = common_reachable.intersection(candidate_node_ids)
    else:
        eligible_candidates = common_reachable

    if not eligible_candidates:
        logger.warning(
            "1-Median optimization failed: no common reachable node found among %d participants.",
            n_participants,
        )
        raise DisconnectedNetworkError(
            "No candidate meeting point is reachable by all participants. "
            "The participants may be situated in disconnected network components "
            "or isolated by one-way road restrictions."
        )

    # Score every eligible candidate
    scored_candidates = []
    for candidate in eligible_candidates:
        dists = [participant_distances[i][candidate] for i in range(n_participants)]
        agg_dist = sum(dists)
        max_dist = max(dists)
        avg_dist = agg_dist / n_participants

        node_data = graph.nodes[candidate]
        lat = float(node_data.get("y", 0.0))
        lon = float(node_data.get("x", 0.0))

        scored_candidates.append(
            {
                "node_id": candidate,
                "latitude": lat,
                "longitude": lon,
                "aggregate_distance": agg_dist,
                "max_distance": max_dist,
                "avg_distance": avg_dist,
                "individual_distances": dists,
            }
        )

    # Sort according to 1-Median objective:
    # 1. Primary: lowest aggregate_distance
    # 2. Tie-break 1: lowest max_distance (minimax)
    # 3. Tie-break 2: deterministic node ID string
    def median_sort_key(item: dict) -> tuple:
        return (
            round(item["aggregate_distance"], 6),
            round(item["max_distance"], 6),
            str(type(item["node_id"])),
            str(item["node_id"]),
        )

    scored_candidates.sort(key=median_sort_key)

    # Build top-K list avoiding duplicate or geographically indistinguishable candidates
    seen_locations: set[tuple[float, float]] = set()
    ranked_candidates: list[RankedCandidateInfo] = []

    for item in scored_candidates:
        loc_key = (round(item["latitude"], 6), round(item["longitude"], 6))
        if loc_key in seen_locations:
            continue
        seen_locations.add(loc_key)

        rank = len(ranked_candidates) + 1
        ranked_candidates.append(
            RankedCandidateInfo(
                rank=rank,
                node_id=item["node_id"],
                latitude=item["latitude"],
                longitude=item["longitude"],
                aggregate_distance_m=item["aggregate_distance"],
                max_distance_m=item["max_distance"],
                avg_distance_m=item["avg_distance"],
                individual_distances_m=item["individual_distances"],
            )
        )
        if len(ranked_candidates) >= top_k:
            break

    best = ranked_candidates[0]

    return OneMedianResult(
        optimal_node_id=best.node_id,
        latitude=best.latitude,
        longitude=best.longitude,
        aggregate_distance_m=best.aggregate_distance_m,
        individual_distances_m=best.individual_distances_m,
        max_distance_m=best.max_distance_m,
        avg_distance_m=best.avg_distance_m,
        eligible_candidate_count=len(eligible_candidates),
        ranked_candidates=ranked_candidates,
    )
