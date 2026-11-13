"""Dijkstra shortest path computation and route reconstruction engine using NetworkX."""

from __future__ import annotations
import networkx as nx
from app.core.logging import logger
from app.models.geometry import Coordinate


def to_simple_digraph(graph: nx.DiGraph | nx.MultiDiGraph, weight: str = "length") -> nx.DiGraph:
    """
    Convert a MultiDiGraph to a simple DiGraph by retaining the minimum weight edge
    between any pair of nodes. Node attributes (such as 'x' and 'y') are preserved.
    """
    if not isinstance(graph, nx.MultiDiGraph):
        return graph

    simple_graph = nx.DiGraph()
    simple_graph.graph.update(graph.graph)

    # Copy all nodes with their spatial and metadata attributes
    for node, data in graph.nodes(data=True):
        simple_graph.add_node(node, **data)

    # Copy edges taking the minimum length among parallel edges
    for u, v, data in graph.edges(data=True):
        edge_weight = float(data.get(weight, float("inf")))
        if simple_graph.has_edge(u, v):
            if edge_weight < simple_graph[u][v][weight]:
                simple_graph[u][v].update(data)
                simple_graph[u][v][weight] = edge_weight
        else:
            edge_data = dict(data)
            edge_data[weight] = edge_weight
            simple_graph.add_edge(u, v, **edge_data)

    return simple_graph


def compute_single_source_paths_and_distances(
    graph: nx.DiGraph | nx.MultiDiGraph,
    source_node: int | str,
    weight: str = "length",
) -> tuple[dict[int | str, float], dict[int | str, list[int | str]]]:
    """
    Compute shortest path distances and node path sequences from source_node
    to all reachable nodes in the graph using Dijkstra's algorithm.

    Parameters
    ----------
    graph : nx.DiGraph | nx.MultiDiGraph
        Directed road network graph.
    source_node : int | str
        Origin node identifier.
    weight : str, default 'length'
        Edge attribute to use as weight (distance in metres).

    Returns
    -------
    tuple[dict[int | str, float], dict[int | str, list[int | str]]]
        - Dictionary mapping reachable target node IDs to shortest route distances in metres.
        - Dictionary mapping reachable target node IDs to ordered list of node IDs along the shortest path.
    """
    if source_node not in graph:
        raise KeyError(f"Source node {source_node} does not exist in graph")

    distances, paths = nx.single_source_dijkstra(graph, source=source_node, weight=weight)
    return distances, paths


def compute_single_source_distances(
    graph: nx.DiGraph | nx.MultiDiGraph,
    source_node: int | str,
    weight: str = "length",
) -> dict[int | str, float]:
    """
    Compute shortest path distance from source_node to all reachable nodes in the graph
    using Dijkstra's algorithm.
    """
    if source_node not in graph:
        raise KeyError(f"Source node {source_node} does not exist in graph")

    distances = nx.single_source_dijkstra_path_length(graph, source=source_node, weight=weight)
    return distances


def compute_all_participant_paths_and_distances(
    graph: nx.DiGraph | nx.MultiDiGraph,
    snapped_nodes: list[int | str],
    weight: str = "length",
) -> tuple[list[dict[int | str, float]], list[dict[int | str, list[int | str]]]]:
    """
    Compute single-source Dijkstra distance maps and route paths for all participants,
    caching results when multiple participants snap to the exact same node.

    Parameters
    ----------
    graph : nx.DiGraph | nx.MultiDiGraph
        Directed road network graph.
    snapped_nodes : list[int | str]
        List of snapped source node IDs, one per participant.
    weight : str, default 'length'
        Edge attribute to use as distance metric.

    Returns
    -------
    tuple[list[dict[int | str, float]], list[dict[int | str, list[int | str]]]]
        - List of distance maps per participant.
        - List of path sequences per participant.
    """
    all_dists: list[dict[int | str, float]] = []
    all_paths: list[dict[int | str, list[int | str]]] = []
    cache: dict[int | str, tuple[dict[int | str, float], dict[int | str, list[int | str]]]] = {}

    for node in snapped_nodes:
        if node in cache:
            dists, paths = cache[node]
        else:
            dists, paths = compute_single_source_paths_and_distances(graph, source_node=node, weight=weight)
            cache[node] = (dists, paths)
        all_dists.append(dists)
        all_paths.append(paths)

    return all_dists, all_paths


def compute_all_participant_distances(
    graph: nx.DiGraph | nx.MultiDiGraph,
    snapped_nodes: list[int | str],
    weight: str = "length",
) -> list[dict[int | str, float]]:
    """
    Compute single-source Dijkstra distance maps for all participants.
    """
    all_dists, _ = compute_all_participant_paths_and_distances(graph, snapped_nodes, weight=weight)
    return all_dists


def reconstruct_route_coordinates(
    graph: nx.DiGraph | nx.MultiDiGraph,
    path_node_ids: list[int | str],
) -> list[Coordinate]:
    """
    Extract the ordered sequence of GPS coordinates for a list of node IDs along a path.
    """
    coords: list[Coordinate] = []
    for node_id in path_node_ids:
        node_data = graph.nodes[node_id]
        coords.append(
            Coordinate(
                latitude=float(node_data.get("y", 0.0)),
                longitude=float(node_data.get("x", 0.0)),
            )
        )
    return coords
