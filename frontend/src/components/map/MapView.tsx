import React, { useEffect, useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import L, { LatLngExpression } from 'leaflet';
import {
  CandidateRecommendation,
  Coordinate,
  OptimizeMeetingResponse,
  Participant,
} from '../../types';
import {
  createCandidateIcon,
  createMeetingPointIcon,
  createParticipantIcon,
} from '../../utils/colors';
import { formatCoordinate, formatDistance } from '../../utils/formatters';
import { Trash2, MapPin, Sparkles } from 'lucide-react';

interface MapViewProps {
  participants: Participant[];
  onParticipantMove: (id: string, lat: number, lon: number) => void;
  onParticipantDelete: (id: string) => void;
  onMapClickAdd: (lat: number, lon: number) => void;
  clickToAddEnabled: boolean;
  result: OptimizeMeetingResponse | null;
  selectedCandidateNodeId: number | string | null;
  onSelectCandidate: (candidate: CandidateRecommendation) => void;
  visibleRouteIds: Set<string>;
}

// Subcomponent to handle map clicks
const MapClickHandler: React.FC<{
  onMapClick: (lat: number, lon: number) => void;
  enabled: boolean;
}> = ({ onMapClick, enabled }) => {
  useMapEvents({
    click: (e) => {
      if (enabled) {
        onMapClick(e.latlng.lat, e.latlng.lng);
      }
    },
  });
  return null;
};

// Subcomponent to automatically fit bounds to participants and optimal location
const AutoBounds: React.FC<{
  participants: Participant[];
  result: OptimizeMeetingResponse | null;
}> = ({ participants, result }) => {
  const map = useMap();

  useEffect(() => {
    const coords: [number, number][] = [];

    // Add all participant coordinates
    participants.forEach((p) => {
      coords.push([p.latitude, p.longitude]);
    });

    // Add optimal location
    if (result?.optimal_location) {
      coords.push([result.optimal_location.latitude, result.optimal_location.longitude]);
    }

    // Add candidate locations
    if (result?.candidates) {
      result.candidates.forEach((c) => {
        coords.push([c.location.latitude, c.location.longitude]);
      });
    }

    if (coords.length > 0) {
      const bounds = L.latLngBounds(coords);
      map.fitBounds(bounds, {
        padding: [50, 50],
        maxZoom: 16,
        animate: true,
      });
    }
  }, [participants.length, result?.optimal_node_id, map]);

  return null;
};

export const MapView: React.FC<MapViewProps> = ({
  participants,
  onParticipantMove,
  onParticipantDelete,
  onMapClickAdd,
  clickToAddEnabled,
  result,
  selectedCandidateNodeId,
  onSelectCandidate,
  visibleRouteIds,
}) => {
  // Center on first participant or default London (Westminster)
  const defaultCenter: LatLngExpression = useMemo(() => {
    if (participants.length > 0) {
      return [participants[0].latitude, participants[0].longitude];
    }
    return [51.5074, -0.1278];
  }, [participants]);

  return (
    <div className="relative w-full h-full bg-slate-100">
      <MapContainer
        center={defaultCenter}
        zoom={14}
        scrollWheelZoom={true}
        className="w-full h-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        <MapClickHandler onMapClick={onMapClickAdd} enabled={clickToAddEnabled} />
        <AutoBounds participants={participants} result={result} />

        {/* 1. Reconstructed Routes (Shortest Path Polylines) */}
        {result?.individual_distances.map((routeResult) => {
          if (!visibleRouteIds.has(routeResult.participant_id)) {
            return null;
          }

          const participant = participants.find((p) => p.id === routeResult.participant_id);
          const routeColor = participant ? participant.color : '#4f46e5';

          const polylinePoints: LatLngExpression[] = routeResult.route_coordinates.map(
            (c: Coordinate) => [c.latitude, c.longitude]
          );

          if (polylinePoints.length < 2) {
            return null;
          }

          return (
            <React.Fragment key={`route-${routeResult.participant_id}`}>
              {/* Outer halo polyline for crisp visibility */}
              <Polyline
                positions={polylinePoints}
                pathOptions={{
                  color: '#ffffff',
                  weight: 7,
                  opacity: 0.9,
                  lineCap: 'round',
                  lineJoin: 'round',
                }}
              />
              {/* Core colored polyline */}
              <Polyline
                positions={polylinePoints}
                pathOptions={{
                  color: routeColor,
                  weight: 4.5,
                  opacity: 0.95,
                  lineCap: 'round',
                  lineJoin: 'round',
                }}
              />
            </React.Fragment>
          );
        })}

        {/* 2. Participant Markers */}
        {participants.map((p) => {
          const icon = createParticipantIcon(p.color, p.name);
          const routeInfo = result?.individual_distances.find(
            (r) => r.participant_id === p.id
          );

          return (
            <Marker
              key={p.id}
              position={[p.latitude, p.longitude]}
              icon={icon}
              draggable={true}
              eventHandlers={{
                dragend: (e) => {
                  const marker = e.target;
                  const pos = marker.getLatLng();
                  onParticipantMove(p.id, pos.lat, pos.lng);
                },
              }}
            >
              <Popup>
                <div className="p-1 min-w-[200px]">
                  <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100">
                    <div className="flex items-center space-x-2">
                      <span
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: p.color }}
                      />
                      <span className="font-semibold text-sm text-slate-800">{p.name}</span>
                    </div>
                    <button
                      onClick={() => onParticipantDelete(p.id)}
                      className="text-slate-400 hover:text-rose-500 p-1 rounded transition-colors"
                      title="Remove participant"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="text-xs space-y-1 text-slate-600">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Position:</span>
                      <span className="font-mono text-[11px]">{formatCoordinate(p)}</span>
                    </div>

                    {routeInfo && (
                      <>
                        <div className="flex justify-between pt-1 border-t border-slate-100">
                          <span className="text-slate-400">Route Distance:</span>
                          <span className="font-semibold text-slate-800">
                            {formatDistance(routeInfo.route_distance_m)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Network Segments:</span>
                          <span className="font-medium text-slate-700">
                            {routeInfo.segment_count}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Snap Distance:</span>
                          <span className="text-slate-500">
                            {formatDistance(routeInfo.snap_distance_m)}
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                  <div className="mt-2 text-[10px] text-slate-400 italic text-center">
                    Drag pin to adjust location
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* 3. Alternative Candidates Markers (Rank 2..K) */}
        {result?.candidates.map((cand) => {
          // Skip rank 1 because it's the optimal meeting point
          if (cand.rank === 1) return null;

          const isSelected = selectedCandidateNodeId === cand.node_id;
          const candIcon = createCandidateIcon(cand.rank, isSelected);

          return (
            <Marker
              key={`cand-${cand.node_id}-${cand.rank}`}
              position={[cand.location.latitude, cand.location.longitude]}
              icon={candIcon}
              eventHandlers={{
                click: () => onSelectCandidate(cand),
              }}
            >
              <Popup>
                <div className="p-1 text-xs space-y-1.5 min-w-[190px]">
                  <div className="flex items-center space-x-1.5 font-bold text-slate-800 text-sm">
                    <span className="bg-slate-800 text-white px-1.5 py-0.5 rounded text-[10px]">
                      #{cand.rank}
                    </span>
                    <span>Alternative #{cand.rank}</span>
                  </div>
                  <div className="flex justify-between text-slate-600">
                    <span className="text-slate-400">Aggregate Dist:</span>
                    <span className="font-semibold">{formatDistance(cand.aggregate_distance_m)}</span>
                  </div>
                  <div className="flex justify-between text-slate-600">
                    <span className="text-slate-400">Max Journey:</span>
                    <span className="font-semibold">{formatDistance(cand.max_distance_m)}</span>
                  </div>
                  <div className="flex justify-between text-slate-600">
                    <span className="text-slate-400">Coordinates:</span>
                    <span className="font-mono text-[10px]">
                      {formatCoordinate(cand.location)}
                    </span>
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* 4. Optimal Meeting Point Marker (Beacon Pin) */}
        {result?.optimal_location && (
          <Marker
            position={[result.optimal_location.latitude, result.optimal_location.longitude]}
            icon={createMeetingPointIcon()}
          >
            <Popup>
              <div className="p-1 min-w-[220px]">
                <div className="flex items-center space-x-2 pb-2 mb-2 border-b border-indigo-100">
                  <div className="w-5 h-5 rounded-full bg-indigo-600 text-amber-300 flex items-center justify-center">
                    <Sparkles className="w-3.5 h-3.5" />
                  </div>
                  <span className="font-bold text-sm text-indigo-950">
                    Recommended Meeting Point
                  </span>
                </div>

                <div className="text-xs space-y-1.5 text-slate-700">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Coordinates:</span>
                    <span className="font-mono text-[11px] font-medium">
                      {formatCoordinate(result.optimal_location)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Aggregate Distance:</span>
                    <span className="font-bold text-indigo-600">
                      {formatDistance(result.aggregate_distance_m)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Max Journey:</span>
                    <span className="font-semibold text-slate-800">
                      {formatDistance(result.max_distance_m)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Average Journey:</span>
                    <span className="text-slate-700">
                      {formatDistance(result.avg_distance_m)}
                    </span>
                  </div>
                  <div className="flex justify-between pt-1 border-t border-slate-100 text-[11px]">
                    <span className="text-slate-400">Objective:</span>
                    <span className="font-semibold uppercase text-indigo-600 text-[10px]">
                      {result.objective}
                    </span>
                  </div>
                </div>
              </div>
            </Popup>
          </Marker>
        )}
      </MapContainer>

      {/* Floating Map Hint / Mode Overlay */}
      {clickToAddEnabled && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[400] bg-indigo-600 text-white px-4 py-2 rounded-full text-xs font-semibold shadow-lg flex items-center space-x-2 animate-bounce pointer-events-none">
          <MapPin className="w-4 h-4" />
          <span>Click anywhere on the map to add a participant</span>
        </div>
      )}
    </div>
  );
};
