export interface Coordinate {
  latitude: number;
  longitude: number;
}

export interface BoundingBox {
  min_lat: number;
  min_lon: number;
  max_lat: number;
  max_lon: number;
}

export type OptimizationObjective = 'median' | 'center' | 'compare';

export type NetworkType = 'walk' | 'drive' | 'bike';

export interface Participant {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  color: string;
}

export interface ParticipantRouteResult {
  participant_id: string;
  label?: string | null;
  original_latitude: number;
  original_longitude: number;
  snapped_node_id: number | string;
  snapped_latitude: number;
  snapped_longitude: number;
  snap_distance_m: number;
  route_distance_m: number;
  route_node_ids: (number | string)[];
  route_coordinates: Coordinate[];
  segment_count: number;
}

export interface CandidateRecommendation {
  rank: number;
  node_id: number | string;
  location: Coordinate;
  aggregate_distance_m: number;
  max_distance_m: number;
  avg_distance_m: number;
  individual_distances_m: number[];
}

export interface ComparisonSummary {
  median_node_id: number | string;
  median_location: Coordinate;
  median_aggregate_distance_m: number;
  median_max_distance_m: number;
  median_avg_distance_m: number;
  center_node_id: number | string;
  center_location: Coordinate;
  center_aggregate_distance_m: number;
  center_max_distance_m: number;
  center_avg_distance_m: number;
  same_optimal_node: boolean;
  aggregate_distance_difference_m: number;
  max_distance_difference_m: number;
  explanation: string;
}

export interface ObjectiveResult {
  objective: OptimizationObjective;
  optimal_node_id: number | string;
  optimal_location: Coordinate;
  aggregate_distance_m: number;
  max_distance_m: number;
  avg_distance_m: number;
  individual_distances: ParticipantRouteResult[];
  candidates: CandidateRecommendation[];
}

export interface OptimizationMetadata {
  network_type: string;
  total_network_nodes: number;
  total_network_edges: number;
  candidate_nodes_evaluated: number;
  execution_time_ms: number;
  cache_hit: boolean;
  bounding_box: BoundingBox;
  objective: OptimizationObjective;
  top_k: number;
}

export interface OptimizeMeetingRequest {
  participants: Array<{
    id: string;
    latitude: number;
    longitude: number;
    label?: string;
  }>;
  bounding_box?: BoundingBox | null;
  network_type: string;
  objective: OptimizationObjective;
  top_k: number;
  max_snap_distance_m?: number | null;
}

export interface OptimizeMeetingResponse {
  optimal_node_id: number | string;
  optimal_location: Coordinate;
  objective: OptimizationObjective;
  aggregate_distance_m: number;
  individual_distances: ParticipantRouteResult[];
  max_distance_m: number;
  avg_distance_m: number;
  candidates: CandidateRecommendation[];
  comparison?: ComparisonSummary | null;
  median_result?: ObjectiveResult | null;
  center_result?: ObjectiveResult | null;
  metadata: OptimizationMetadata;
}

export interface ApiErrorResponse {
  message: string;
  details?: Record<string, unknown>;
}
