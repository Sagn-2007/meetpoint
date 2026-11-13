"""High-level meeting point optimization orchestration service."""

from __future__ import annotations
import time
from typing import Sequence
import networkx as nx

from app.algorithms.dijkstra import (
    compute_all_participant_paths_and_distances,
    reconstruct_route_coordinates,
    to_simple_digraph,
)
from app.algorithms.one_center import OneCenterResult, solve_network_1_center
from app.algorithms.one_median import OneMedianResult, solve_network_1_median
from app.core.config import settings
from app.core.exceptions import DisconnectedNetworkError, ParticipantCoordinateError
from app.core.logging import logger
from app.models.geometry import BoundingBox, Coordinate
from app.models.schemas import (
    CandidateRecommendation,
    ComparisonSummary,
    ObjectiveResult,
    OptimizationMetadata,
    OptimizationObjective,
    OptimizeMeetingRequest,
    OptimizeMeetingResponse,
    Participant,
    ParticipantRouteResult,
)
from app.services.network_service import NetworkService, network_service
from app.services.snapping_service import SnappedParticipant, SnappingService, snapping_service


class OptimizationService:
    """Orchestrates road network retrieval, snapping, Dijkstra pathing, and multi-objective solving."""

    def __init__(
        self,
        net_service: NetworkService | None = None,
        snap_service: SnappingService | None = None,
    ) -> None:
        self.network_service = net_service or network_service
        self.snapping_service = snap_service or snapping_service

    @staticmethod
    def _build_individual_routes(
        graph: nx.DiGraph | nx.MultiDiGraph,
        participants: list[Participant],
        snapped_participants_info: list[SnappedParticipant],
        paths_maps: list[dict[int | str, list[int | str]]],
        target_node: int | str,
        individual_distances_m: list[float],
    ) -> list[ParticipantRouteResult]:
        """Reconstruct the actual traversed shortest paths and coordinates for each participant."""
        results: list[ParticipantRouteResult] = []

        for i, p in enumerate(participants):
            snapped_info = snapped_participants_info[i]
            route_dist = individual_distances_m[i]

            # Retrieve the reconstructed node sequence
            path_nodes = paths_maps[i].get(target_node, [snapped_info.node_id])
            route_coords = reconstruct_route_coordinates(graph, path_nodes)
            segment_count = max(0, len(path_nodes) - 1)

            results.append(
                ParticipantRouteResult(
                    participant_id=p.id,
                    label=p.label,
                    original_latitude=p.latitude,
                    original_longitude=p.longitude,
                    snapped_node_id=snapped_info.node_id,
                    snapped_latitude=snapped_info.latitude,
                    snapped_longitude=snapped_info.longitude,
                    snap_distance_m=round(snapped_info.snap_distance_m, 2),
                    route_distance_m=round(route_dist, 2),
                    route_node_ids=path_nodes,
                    route_coordinates=route_coords,
                    segment_count=segment_count,
                )
            )

        return results

    @staticmethod
    def _to_candidate_recommendations(ranked_candidates: Sequence) -> list[CandidateRecommendation]:
        """Convert algorithm RankedCandidateInfo objects to API CandidateRecommendation models."""
        recommendations: list[CandidateRecommendation] = []
        for rc in ranked_candidates:
            recommendations.append(
                CandidateRecommendation(
                    rank=rc.rank,
                    node_id=rc.node_id,
                    location=Coordinate(
                        latitude=round(rc.latitude, 6),
                        longitude=round(rc.longitude, 6),
                    ),
                    aggregate_distance_m=round(rc.aggregate_distance_m, 2),
                    max_distance_m=round(rc.max_distance_m, 2),
                    avg_distance_m=round(rc.avg_distance_m, 2),
                    individual_distances_m=[round(d, 2) for d in rc.individual_distances_m],
                )
            )
        return recommendations

    def optimize_meeting_location(
        self,
        request: OptimizeMeetingRequest,
        custom_graph: nx.MultiDiGraph | nx.DiGraph | None = None,
    ) -> OptimizeMeetingResponse:
        """
        Execute the end-to-end optimization workflow to find the optimal meeting node(s).

        Parameters
        ----------
        request : OptimizeMeetingRequest
            Participant coordinates, network configuration, optimization objective, and top_k.
        custom_graph : nx.MultiDiGraph | nx.DiGraph | None
            Optional pre-loaded graph to bypass OSM download (useful in testing).

        Returns
        -------
        OptimizeMeetingResponse
            The optimal meeting location, reconstructed routes, and ranked candidate alternatives.
        """
        start_time = time.perf_counter()

        # 1. Determine bounding box
        coords = [p.to_coordinate() for p in request.participants]
        if request.bounding_box is not None:
            bbox = request.bounding_box
        else:
            bbox = BoundingBox.from_coordinates(
                coords,
                padding_ratio=settings.DEFAULT_BBOX_PADDING_RATIO,
                min_padding_deg=settings.MIN_BBOX_PADDING_DEG,
            )

        logger.info(
            "Optimizing meeting location for %d participants within bbox=%s, objective=%s, top_k=%d",
            len(request.participants),
            bbox,
            request.objective.value,
            request.top_k,
        )

        # 2. Acquire road network
        if custom_graph is not None:
            if not isinstance(custom_graph, nx.MultiDiGraph):
                graph = nx.MultiDiGraph(custom_graph)
                graph.graph.update(custom_graph.graph)
            else:
                graph = custom_graph
            cache_hit = False
        else:
            graph, cache_hit = self.network_service.get_road_network(
                bounding_box=bbox,
                network_type=request.network_type,
            )

        # 3. Snap each participant to the nearest road network node
        snapped_nodes: list[int | str] = []
        snapped_participants_info: list[SnappedParticipant] = []

        for p in request.participants:
            snapped = self.snapping_service.snap_coordinate(
                graph=graph,
                lat=p.latitude,
                lon=p.longitude,
                max_snap_distance_m=request.max_snap_distance_m,
            )
            snapped_nodes.append(snapped.node_id)
            snapped_participants_info.append(snapped)

        # 4. Prepare graph and compute single-source Dijkstra paths and distances from each participant
        simple_graph = to_simple_digraph(graph, weight="length")
        participant_distances, participant_paths = compute_all_participant_paths_and_distances(
            graph=simple_graph,
            snapped_nodes=snapped_nodes,
            weight="length",
        )

        # 5. Solve optimization according to requested objective
        comparison_summary: ComparisonSummary | None = None
        median_obj_result: ObjectiveResult | None = None
        center_obj_result: ObjectiveResult | None = None

        if request.objective == OptimizationObjective.MEDIAN:
            median_res = solve_network_1_median(
                graph=simple_graph,
                participant_distances=participant_distances,
                top_k=request.top_k,
            )
            primary_optimal_node = median_res.optimal_node_id
            primary_lat = median_res.latitude
            primary_lon = median_res.longitude
            primary_agg_dist = median_res.aggregate_distance_m
            primary_max_dist = median_res.max_distance_m
            primary_avg_dist = median_res.avg_distance_m
            candidates_rec = self._to_candidate_recommendations(median_res.ranked_candidates)
            individual_routes = self._build_individual_routes(
                graph=simple_graph,
                participants=request.participants,
                snapped_participants_info=snapped_participants_info,
                paths_maps=participant_paths,
                target_node=primary_optimal_node,
                individual_distances_m=median_res.individual_distances_m,
            )
            candidate_count = median_res.eligible_candidate_count

        elif request.objective == OptimizationObjective.CENTER:
            center_res = solve_network_1_center(
                graph=simple_graph,
                participant_distances=participant_distances,
                top_k=request.top_k,
            )
            primary_optimal_node = center_res.optimal_node_id
            primary_lat = center_res.latitude
            primary_lon = center_res.longitude
            primary_agg_dist = center_res.aggregate_distance_m
            primary_max_dist = center_res.max_distance_m
            primary_avg_dist = center_res.avg_distance_m
            candidates_rec = self._to_candidate_recommendations(center_res.ranked_candidates)
            individual_routes = self._build_individual_routes(
                graph=simple_graph,
                participants=request.participants,
                snapped_participants_info=snapped_participants_info,
                paths_maps=participant_paths,
                target_node=primary_optimal_node,
                individual_distances_m=center_res.individual_distances_m,
            )
            candidate_count = center_res.eligible_candidate_count

        else:
            # OptimizationObjective.COMPARE
            median_res = solve_network_1_median(
                graph=simple_graph,
                participant_distances=participant_distances,
                top_k=request.top_k,
            )
            center_res = solve_network_1_center(
                graph=simple_graph,
                participant_distances=participant_distances,
                top_k=request.top_k,
            )

            # Build routes for both
            median_routes = self._build_individual_routes(
                graph=simple_graph,
                participants=request.participants,
                snapped_participants_info=snapped_participants_info,
                paths_maps=participant_paths,
                target_node=median_res.optimal_node_id,
                individual_distances_m=median_res.individual_distances_m,
            )
            center_routes = self._build_individual_routes(
                graph=simple_graph,
                participants=request.participants,
                snapped_participants_info=snapped_participants_info,
                paths_maps=participant_paths,
                target_node=center_res.optimal_node_id,
                individual_distances_m=center_res.individual_distances_m,
            )

            median_candidates = self._to_candidate_recommendations(median_res.ranked_candidates)
            center_candidates = self._to_candidate_recommendations(center_res.ranked_candidates)

            median_obj_result = ObjectiveResult(
                objective=OptimizationObjective.MEDIAN,
                optimal_node_id=median_res.optimal_node_id,
                optimal_location=Coordinate(
                    latitude=round(median_res.latitude, 6),
                    longitude=round(median_res.longitude, 6),
                ),
                aggregate_distance_m=round(median_res.aggregate_distance_m, 2),
                max_distance_m=round(median_res.max_distance_m, 2),
                avg_distance_m=round(median_res.avg_distance_m, 2),
                individual_distances=median_routes,
                candidates=median_candidates,
            )

            center_obj_result = ObjectiveResult(
                objective=OptimizationObjective.CENTER,
                optimal_node_id=center_res.optimal_node_id,
                optimal_location=Coordinate(
                    latitude=round(center_res.latitude, 6),
                    longitude=round(center_res.longitude, 6),
                ),
                aggregate_distance_m=round(center_res.aggregate_distance_m, 2),
                max_distance_m=round(center_res.max_distance_m, 2),
                avg_distance_m=round(center_res.avg_distance_m, 2),
                individual_distances=center_routes,
                candidates=center_candidates,
            )

            agg_diff = round(center_res.aggregate_distance_m - median_res.aggregate_distance_m, 2)
            max_diff = round(median_res.max_distance_m - center_res.max_distance_m, 2)

            comparison_summary = ComparisonSummary(
                median_node_id=median_res.optimal_node_id,
                median_location=Coordinate(
                    latitude=round(median_res.latitude, 6),
                    longitude=round(median_res.longitude, 6),
                ),
                median_aggregate_distance_m=round(median_res.aggregate_distance_m, 2),
                median_max_distance_m=round(median_res.max_distance_m, 2),
                median_avg_distance_m=round(median_res.avg_distance_m, 2),
                center_node_id=center_res.optimal_node_id,
                center_location=Coordinate(
                    latitude=round(center_res.latitude, 6),
                    longitude=round(center_res.longitude, 6),
                ),
                center_aggregate_distance_m=round(center_res.aggregate_distance_m, 2),
                center_max_distance_m=round(center_res.max_distance_m, 2),
                center_avg_distance_m=round(center_res.avg_distance_m, 2),
                same_optimal_node=(median_res.optimal_node_id == center_res.optimal_node_id),
                aggregate_distance_difference_m=agg_diff,
                max_distance_difference_m=max_diff,
                explanation=(
                    "1-Median minimizes the total distance travelled by everyone. "
                    "1-Center minimizes the longest individual journey."
                ),
            )

            # Default primary view to Median
            primary_optimal_node = median_res.optimal_node_id
            primary_lat = median_res.latitude
            primary_lon = median_res.longitude
            primary_agg_dist = median_res.aggregate_distance_m
            primary_max_dist = median_res.max_distance_m
            primary_avg_dist = median_res.avg_distance_m
            candidates_rec = median_candidates
            individual_routes = median_routes
            candidate_count = median_res.eligible_candidate_count

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        metadata = OptimizationMetadata(
            network_type=request.network_type,
            total_network_nodes=graph.number_of_nodes(),
            total_network_edges=graph.number_of_edges(),
            candidate_nodes_evaluated=candidate_count,
            execution_time_ms=round(elapsed_ms, 2),
            cache_hit=cache_hit,
            bounding_box=bbox,
            objective=request.objective,
            top_k=request.top_k,
        )

        return OptimizeMeetingResponse(
            optimal_node_id=primary_optimal_node,
            optimal_location=Coordinate(
                latitude=round(primary_lat, 6),
                longitude=round(primary_lon, 6),
            ),
            objective=request.objective,
            aggregate_distance_m=round(primary_agg_dist, 2),
            individual_distances=individual_routes,
            max_distance_m=round(primary_max_dist, 2),
            avg_distance_m=round(primary_avg_dist, 2),
            candidates=candidates_rec,
            comparison=comparison_summary,
            median_result=median_obj_result,
            center_result=center_obj_result,
            metadata=metadata,
        )


optimization_service = OptimizationService()
