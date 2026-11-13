"""Pytest fixtures for synthetic road network graphs and test clients."""

from __future__ import annotations
import networkx as nx
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def reset_rate_limiter_fixture():
    """Ensure rate limiter state is clean for each test execution."""
    from app.core.rate_limit import rate_limiter
    rate_limiter.reset()


@pytest.fixture
def api_client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def synthetic_line_graph() -> nx.MultiDiGraph:
    """
    Synthetic bidirectional line graph:
    Node 1 (22.50, 88.30) <---> Node 2 (22.50, 88.31) <---> Node 3 (22.50, 88.32)
    Each segment is 1000.0 metres.
    """
    G = nx.MultiDiGraph()
    G.graph["crs"] = "EPSG:4326"

    G.add_node(1, y=22.50, x=88.30)
    G.add_node(2, y=22.50, x=88.31)
    G.add_node(3, y=22.50, x=88.32)

    # 1 <-> 2
    G.add_edge(1, 2, length=1000.0, oneway=False)
    G.add_edge(2, 1, length=1000.0, oneway=False)

    # 2 <-> 3
    G.add_edge(2, 3, length=1000.0, oneway=False)
    G.add_edge(3, 2, length=1000.0, oneway=False)

    return G


@pytest.fixture
def synthetic_oneway_graph() -> nx.MultiDiGraph:
    """
    Synthetic directed graph with one-way roads:
    Node 1 ---> Node 2 ---> Node 3
    Node 3 can NOT travel back to Node 1 or Node 2.
    """
    G = nx.MultiDiGraph()
    G.graph["crs"] = "EPSG:4326"

    G.add_node(1, y=22.50, x=88.30)
    G.add_node(2, y=22.50, x=88.31)
    G.add_node(3, y=22.50, x=88.32)

    G.add_edge(1, 2, length=500.0, oneway=True)
    G.add_edge(2, 3, length=500.0, oneway=True)

    return G


@pytest.fixture
def synthetic_disconnected_graph() -> nx.MultiDiGraph:
    """
    Synthetic graph with two completely disconnected components:
    Component A: Node 1 <-> Node 2
    Component B: Node 3 <-> Node 4
    """
    G = nx.MultiDiGraph()
    G.graph["crs"] = "EPSG:4326"

    G.add_node(1, y=22.50, x=88.30)
    G.add_node(2, y=22.50, x=88.31)
    G.add_node(3, y=22.60, x=88.40)
    G.add_node(4, y=22.60, x=88.41)

    G.add_edge(1, 2, length=600.0, oneway=False)
    G.add_edge(2, 1, length=600.0, oneway=False)

    G.add_edge(3, 4, length=700.0, oneway=False)
    G.add_edge(4, 3, length=700.0, oneway=False)

    return G


@pytest.fixture
def synthetic_tiebreak_graph() -> nx.MultiDiGraph:
    """
    Synthetic graph designed to test tie-breaking.
    
    Layout:
    Participants at Node 1 and Node 4.
    Candidate A (Node 2):
      Dist from 1 = 100, Dist from 4 = 100 -> Sum = 200, Max = 100
    Candidate B (Node 3):
      Dist from 1 = 50, Dist from 4 = 150 -> Sum = 200, Max = 150
      
    Both have Aggregate Distance = 200.
    Tie-breaking rule 1 (Minimax): Candidate A has lower max distance (100 < 150), so A wins!
    """
    G = nx.MultiDiGraph()
    G.graph["crs"] = "EPSG:4326"

    G.add_node(1, y=22.50, x=88.30)
    G.add_node(2, y=22.51, x=88.31)  # Candidate A
    G.add_node(3, y=22.52, x=88.32)  # Candidate B
    G.add_node(4, y=22.53, x=88.33)

    # Participant 1 at 1
    G.add_edge(1, 2, length=100.0)
    G.add_edge(1, 3, length=50.0)

    # Participant 2 at 4
    G.add_edge(4, 2, length=100.0)
    G.add_edge(4, 3, length=150.0)

    # Return edges to ensure reachable
    G.add_edge(2, 1, length=100.0)
    G.add_edge(3, 1, length=50.0)
    G.add_edge(2, 4, length=100.0)
    G.add_edge(3, 4, length=150.0)

    return G


@pytest.fixture
def synthetic_id_tiebreak_graph() -> nx.MultiDiGraph:
    """
    Synthetic graph where two candidates have IDENTICAL aggregate distance
    AND IDENTICAL maximum distance.
    Candidate 10 and Candidate 20:
    Distances from P1: 100 for both.
    Distances from P2: 100 for both.
    Sum = 200, Max = 100 for both.
    Tie-breaking rule 2 (Node ID): Node 10 should be selected deterministically over 20.
    """
    G = nx.MultiDiGraph()
    G.graph["crs"] = "EPSG:4326"

    G.add_node(1, y=22.50, x=88.30)
    G.add_node(2, y=22.50, x=88.32)
    G.add_node(10, y=22.51, x=88.31)
    G.add_node(20, y=22.49, x=88.31)

    # 1 -> 10, 1 -> 20
    G.add_edge(1, 10, length=100.0)
    G.add_edge(1, 20, length=100.0)

    # 2 -> 10, 2 -> 20
    G.add_edge(2, 10, length=100.0)
    G.add_edge(2, 20, length=100.0)

    return G
