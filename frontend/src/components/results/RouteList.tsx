import React from 'react';
import { Participant, ParticipantRouteResult } from '../../types';
import { Eye, EyeOff } from 'lucide-react';
import { estimateDuration, formatDistance } from '../../utils/formatters';

interface RouteListProps {
  routes: ParticipantRouteResult[];
  participants: Participant[];
  visibleRouteIds: Set<string>;
  onToggleRouteVisibility: (participantId: string) => void;
  networkType: string;
}

export const RouteList: React.FC<RouteListProps> = ({
  routes,
  participants,
  visibleRouteIds,
  onToggleRouteVisibility,
  networkType,
}) => {
  if (routes.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-xs text-slate-900">
          Individual Routes & Distances
        </span>
        <span className="text-[11px] text-slate-400">
          {routes.length} paths calculated
        </span>
      </div>

      <div className="space-y-1.5 max-h-[220px] overflow-y-auto pr-0.5">
        {routes.map((route) => {
          const participant = participants.find((p) => p.id === route.participant_id);
          const isVisible = visibleRouteIds.has(route.participant_id);
          const pColor = participant ? participant.color : '#4f46e5';
          const pName = participant?.name || route.label || route.participant_id;

          return (
            <div
              key={`route-item-${route.participant_id}`}
              className="p-2.5 bg-white rounded-xl border border-slate-200 shadow-xs flex items-center justify-between text-xs hover:border-slate-300 transition-colors"
            >
              <div className="flex items-center space-x-2.5 min-w-0">
                <span
                  className="w-3.5 h-3.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: pColor }}
                />
                <div className="min-w-0">
                  <div className="font-semibold text-slate-800 truncate">{pName}</div>
                  <div className="flex items-center space-x-2 text-[11px] text-slate-400">
                    <span>{route.segment_count} segments</span>
                    <span>•</span>
                    <span>{estimateDuration(route.route_distance_m, networkType)}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-3 flex-shrink-0">
                <div className="text-right">
                  <span className="font-bold text-slate-900 block">
                    {formatDistance(route.route_distance_m)}
                  </span>
                  <span className="text-[10px] text-slate-400 block">
                    snap: {formatDistance(route.snap_distance_m)}
                  </span>
                </div>

                <button
                  onClick={() => onToggleRouteVisibility(route.participant_id)}
                  className={`p-1.5 rounded-lg transition-colors ${
                    isVisible
                      ? 'text-indigo-600 hover:bg-indigo-50'
                      : 'text-slate-300 hover:text-slate-500 hover:bg-slate-100'
                  }`}
                  title={isVisible ? 'Hide route on map' : 'Show route on map'}
                >
                  {isVisible ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
