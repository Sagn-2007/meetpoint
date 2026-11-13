"""Participant coordinate snapping service using spatial indexing."""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.spatial import KDTree
import networkx as nx

from app.core.config import settings
from app.core.exceptions import ParticipantSnappingError
from app.core.logging import logger

EARTH_RADIUS_M = 6371000.0


@dataclass(frozen=True)
class SnappedParticipant:
    """Participant coordinate snapped to a graph node."""

    node_id: int | str
    latitude: float
    longitude: float
    snap_distance_m: float


class GraphSpatialIndex:
    """Spatial 3D KDTree index over graph node coordinates for fast nearest-neighbor snapping."""

    def __init__(self, graph: nx.Graph | nx.DiGraph | nx.MultiDiGraph):
        if len(graph) == 0:
            raise ParticipantSnappingError("Cannot create spatial index for an empty graph")

        self.node_ids = list(graph.nodes)
        lats = np.array([float(graph.nodes[n].get("y", 0.0)) for n in self.node_ids], dtype=np.float64)
        lons = np.array([float(graph.nodes[n].get("x", 0.0)) for n in self.node_ids], dtype=np.float64)

        self.coords_3d = self._to_cartesian_3d(lats, lons)
        self.kdtree = KDTree(self.coords_3d)

    @staticmethod
    def _to_cartesian_3d(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
        """Convert WGS84 lat/lon arrays to 3D Cartesian coordinates on a spherical Earth."""
        rad_lat = np.radians(lats)
        rad_lon = np.radians(lons)
        x = EARTH_RADIUS_M * np.cos(rad_lat) * np.cos(rad_lon)
        y = EARTH_RADIUS_M * np.cos(rad_lat) * np.sin(rad_lon)
        z = EARTH_RADIUS_M * np.sin(rad_lat)
        return np.column_stack([x, y, z])

    def snap(
        self,
        lat: float,
        lon: float,
        max_snap_distance_m: float | None = None,
    ) -> SnappedParticipant:
        """
        Snap a single (lat, lon) to the nearest node in the spatial index.

        Parameters
        ----------
        lat : float
            Latitude in degrees [-90, 90].
        lon : float
            Longitude in degrees [-180, 180].
        max_snap_distance_m : float | None
            Maximum acceptable snapping distance in metres.

        Returns
        -------
        SnappedParticipant
            Information on the snapped node and snapping distance.
        """
        query_pt = self._to_cartesian_3d(np.array([lat]), np.array([lon]))
        chord_dist, idx = self.kdtree.query(query_pt)

        chord = float(chord_dist[0])
        node_idx = int(idx[0])
        snapped_node_id = self.node_ids[node_idx]

        # Convert 3D Euclidean chord distance to true great-circle arc distance:
        # arc = 2 * R * arcsin(chord / (2 * R))
        ratio = min(1.0, max(-1.0, chord / (2.0 * EARTH_RADIUS_M)))
        arc_distance_m = 2.0 * EARTH_RADIUS_M * np.arcsin(ratio)

        threshold = max_snap_distance_m if max_snap_distance_m is not None else settings.MAX_SNAP_DISTANCE_M
        if arc_distance_m > threshold:
            msg = (
                f"Participant coordinate ({lat:.6f}, {lon:.6f}) is too far ({arc_distance_m:.1f}m) "
                f"from the nearest road network node (limit: {threshold:.1f}m)."
            )
            logger.warning(msg)
            raise ParticipantSnappingError(
                msg,
                details={
                    "latitude": lat,
                    "longitude": lon,
                    "snap_distance_m": arc_distance_m,
                    "max_threshold_m": threshold,
                    "nearest_node_id": snapped_node_id,
                },
            )

        # Retrieve true node lat/lon from the Cartesian coords or node table
        return SnappedParticipant(
            node_id=snapped_node_id,
            latitude=float(np.degrees(np.arcsin(self.coords_3d[node_idx, 2] / EARTH_RADIUS_M))),
            longitude=float(np.degrees(np.arctan2(self.coords_3d[node_idx, 1], self.coords_3d[node_idx, 0]))),
            snap_distance_m=arc_distance_m,
        )


class SnappingService:
    """Service responsible for snapping participants to graph nodes."""

    def __init__(self) -> None:
        # Cache spatial index per graph object id
        self._index_cache: dict[int, GraphSpatialIndex] = {}

    def get_spatial_index(self, graph: nx.Graph | nx.DiGraph | nx.MultiDiGraph) -> GraphSpatialIndex:
        """Get or create a spatial index for the given graph."""
        graph_id = id(graph)
        if graph_id not in self._index_cache:
            self._index_cache[graph_id] = GraphSpatialIndex(graph)
        return self._index_cache[graph_id]

    def snap_coordinate(
        self,
        graph: nx.Graph | nx.DiGraph | nx.MultiDiGraph,
        lat: float,
        lon: float,
        max_snap_distance_m: float | None = None,
    ) -> SnappedParticipant:
        """Snap a single coordinate to the graph."""
        index = self.get_spatial_index(graph)
        return index.snap(lat, lon, max_snap_distance_m=max_snap_distance_m)


snapping_service = SnappingService()
