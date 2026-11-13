"""Road network acquisition, validation, and caching service using OSMnx."""

from __future__ import annotations
import collections
import math
import os
from pathlib import Path
import threading
from typing import Any
import networkx as nx
import osmnx as ox

from app.core.config import settings
from app.core.exceptions import NetworkAcquisitionError
from app.core.logging import logger
from app.models.geometry import BoundingBox

EARTH_RADIUS_M = 6371000.0


class BoundedGraphCache:
    """Thread-safe LRU in-memory cache for road networks."""

    def __init__(self, maxsize: int) -> None:
        self.maxsize = maxsize
        self._cache: collections.OrderedDict[str, nx.MultiDiGraph] = collections.OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> nx.MultiDiGraph | None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    def put(self, key: str, graph: nx.MultiDiGraph) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = graph
            while len(self._cache) > self.maxsize:
                evicted_key, _ = self._cache.popitem(last=False)
                logger.info("Evicted graph from memory LRU cache: %s", evicted_key)

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._cache

    def __getitem__(self, key: str) -> nx.MultiDiGraph:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            raise KeyError(key)

    def __setitem__(self, key: str, graph: nx.MultiDiGraph) -> None:
        self.put(key, graph)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._cache.keys())


def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in metres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_M * c


class NetworkService:
    """Manages acquisition, disk/memory caching, and inspection of directed road networks."""

    def __init__(self, cache_dir: Path | None = None, max_in_memory: int | None = None) -> None:
        self.cache_dir = cache_dir or settings.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        max_graphs = max_in_memory or settings.MAX_IN_MEMORY_GRAPHS
        self._memory_cache = BoundedGraphCache(maxsize=max_graphs)
        self._download_lock = threading.Lock()
        # Set OSMnx Overpass timeout
        try:
            ox.settings.timeout = settings.OVERPASS_TIMEOUT
        except Exception:
            pass

    @staticmethod
    def get_cache_key(bbox: BoundingBox, network_type: str) -> str:
        """Create a deterministic cache key for a given bounding box and network mode."""
        return (
            f"osm_{network_type}_{bbox.min_lat:.4f}_{bbox.min_lon:.4f}_"
            f"{bbox.max_lat:.4f}_{bbox.max_lon:.4f}"
        )

    def _get_cache_filepath(self, cache_key: str) -> Path:
        """Get the full path to the cached GraphML file."""
        return self.cache_dir / f"{cache_key}.graphml"

    def register_graph(self, key: str, graph: nx.MultiDiGraph | nx.DiGraph) -> None:
        """Manually register a graph in memory cache (e.g. for synthetic tests)."""
        if not isinstance(graph, nx.MultiDiGraph):
            multi_g = nx.MultiDiGraph(graph)
            multi_g.graph.update(graph.graph)
            self._memory_cache[key] = multi_g
        else:
            self._memory_cache[key] = graph

    def clear_cache(self) -> None:
        """Clear memory cache."""
        self._memory_cache.clear()

    def get_road_network(
        self,
        bounding_box: BoundingBox,
        network_type: str = "drive",
        force_reload: bool = False,
    ) -> tuple[nx.MultiDiGraph, bool]:
        """
        Retrieve a directed drivable road network within the bounding box.
        
        Attempts to read from memory cache, then disk cache, before querying OpenStreetMap.

        Parameters
        ----------
        bounding_box : BoundingBox
            Geographic bounding box.
        network_type : str, default 'drive'
            Network mode filter ('drive', 'walk', 'bike', etc.).
        force_reload : bool, default False
            If True, ignore cache and re-download from OSM.

        Returns
        -------
        tuple[nx.MultiDiGraph, bool]
            Tuple of (directed road graph, cache_hit flag).
        """
        cache_key = self.get_cache_key(bounding_box, network_type)

        # 1. Check in-memory cache
        if not force_reload and cache_key in self._memory_cache:
            logger.info("Retrieved road network from memory cache: key=%s", cache_key)
            return self._memory_cache[cache_key], True

        cache_path = self._get_cache_filepath(cache_key)

        # 2. Check on-disk GraphML cache
        if not force_reload and settings.ENABLE_DISK_CACHE and cache_path.is_file():
            try:
                logger.info("Loading road network from disk cache: %s", cache_path)
                graph = ox.load_graphml(cache_path)
                self._validate_and_sanitize_graph(graph)
                self._memory_cache[cache_key] = graph
                return graph, True
            except Exception as e:
                logger.warning(
                    "Corrupted or unreadable cached graphml file %s: %s. Removing and re-downloading.",
                    cache_path,
                    e,
                )
                try:
                    cache_path.unlink(missing_ok=True)
                except Exception as del_err:
                    logger.warning("Could not unlink corrupt cache file %s: %s", cache_path, del_err)

        # 3. Download from OpenStreetMap via OSMnx (synchronized to avoid duplicate downloads)
        with self._download_lock:
            # Re-check memory cache in case another thread downloaded while waiting
            if not force_reload and cache_key in self._memory_cache:
                return self._memory_cache[cache_key], True

            logger.info(
                "Downloading road network from OpenStreetMap for bbox=%s network_type=%s",
                bounding_box,
                network_type,
            )
            try:
                # OSMnx 2.x expects bbox as (left, bottom, right, top) = (min_lon, min_lat, max_lon, max_lat)
                osmnx_bbox = bounding_box.to_osmnx_bbox()
                graph = ox.graph_from_bbox(
                    bbox=osmnx_bbox,
                    network_type=network_type,
                    simplify=True,
                    retain_all=False,
                )
            except Exception as e:
                msg = f"Failed to acquire road network from OpenStreetMap: {e}"
                logger.error(msg)
                raise NetworkAcquisitionError(msg, details={"bbox": bounding_box.model_dump(), "error": str(e)}) from e

            if graph is None or len(graph) == 0:
                msg = f"OpenStreetMap returned an empty road network for the requested bounding box: {bounding_box}"
                logger.error(msg)
                raise NetworkAcquisitionError(msg, details={"bbox": bounding_box.model_dump()})

            # Sanitize and ensure length attribute on all edges
            self._validate_and_sanitize_graph(graph)

            # 4. Save to disk cache
            if settings.ENABLE_DISK_CACHE:
                try:
                    ox.save_graphml(graph, filepath=cache_path)
                    logger.info("Saved road network to disk cache at: %s", cache_path)
                except Exception as e:
                    logger.warning("Could not persist graph to disk cache %s: %s", cache_path, e)

            self._memory_cache[cache_key] = graph
            return graph, False

    def _validate_and_sanitize_graph(self, graph: nx.MultiDiGraph) -> None:
        """
        Ensure all nodes have numeric x, y coordinates and all edges have numeric length attributes in metres.
        """
        for node, data in graph.nodes(data=True):
            if "x" not in data or "y" not in data:
                raise NetworkAcquisitionError(f"Node {node} is missing coordinates (x, y)")
            data["x"] = float(data["x"])
            data["y"] = float(data["y"])

        for u, v, k, data in graph.edges(keys=True, data=True):
            if "length" not in data or data["length"] is None:
                # Compute geodesic distance from node coordinates
                u_lat, u_lon = graph.nodes[u]["y"], graph.nodes[u]["x"]
                v_lat, v_lon = graph.nodes[v]["y"], graph.nodes[v]["x"]
                data["length"] = calculate_haversine_distance(u_lat, u_lon, v_lat, v_lon)
            else:
                data["length"] = float(data["length"])

    def get_cache_info(self) -> dict[str, Any]:
        """Return information about cached road networks."""
        files = list(self.cache_dir.glob("*.graphml"))
        return {
            "cached_networks_count": len(files),
            "in_memory_cached_count": len(self._memory_cache),
            "max_in_memory_graphs": self._memory_cache.maxsize,
            "default_network_type": settings.DEFAULT_NETWORK_TYPE,
            "cache_directory": str(self.cache_dir),
            "cached_files": [f.name for f in files],
        }

    @staticmethod
    def get_component_info(graph: nx.DiGraph | nx.MultiDiGraph) -> dict[str, Any]:
        """Inspect directed connectivity and components in the graph."""
        strongly_connected = list(nx.strongly_connected_components(graph))
        weakly_connected = list(nx.weakly_connected_components(graph))
        return {
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
            "is_strongly_connected": len(strongly_connected) == 1,
            "strongly_connected_components_count": len(strongly_connected),
            "weakly_connected_components_count": len(weakly_connected),
            "largest_scc_size": max(len(c) for c in strongly_connected) if strongly_connected else 0,
            "largest_wcc_size": max(len(c) for c in weakly_connected) if weakly_connected else 0,
        }


network_service = NetworkService()
