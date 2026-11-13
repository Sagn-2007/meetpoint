import React from 'react';
import { OptimizeMeetingResponse } from '../../types';
import { Sparkles, MapPin, Gauge, Clock, Copy, Check } from 'lucide-react';
import { formatCoordinate, formatDistance, formatMs } from '../../utils/formatters';

interface OptimalMeetingCardProps {
  result: OptimizeMeetingResponse;
}

export const OptimalMeetingCard: React.FC<OptimalMeetingCardProps> = ({ result }) => {
  const [copied, setCopied] = React.useState(false);

  const handleCopyCoords = () => {
    navigator.clipboard.writeText(formatCoordinate(result.optimal_location));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-gradient-to-br from-indigo-900 to-indigo-950 text-white p-4 rounded-2xl shadow-lg border border-indigo-800 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 rounded-lg bg-indigo-500/30 flex items-center justify-center text-amber-300">
            <Sparkles className="w-4 h-4" />
          </div>
          <span className="font-bold text-sm tracking-tight">Optimal Meeting Point</span>
        </div>
        <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-200 border border-indigo-400/30">
          {result.objective}
        </span>
      </div>

      {/* Coordinate & Copy */}
      <div className="bg-white/10 backdrop-blur-xs p-2.5 rounded-xl border border-white/10 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <MapPin className="w-4 h-4 text-indigo-300" />
          <span className="font-mono text-xs font-semibold text-white">
            {formatCoordinate(result.optimal_location)}
          </span>
        </div>
        <button
          onClick={handleCopyCoords}
          className="text-indigo-200 hover:text-white p-1 rounded hover:bg-white/10 transition-colors"
          title="Copy coordinates"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-300" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Metric Tiles */}
      <div className="grid grid-cols-3 gap-2 text-center pt-1">
        <div className="bg-white/5 p-2 rounded-xl border border-white/5">
          <span className="block text-[10px] text-indigo-200 font-medium">Total Travel</span>
          <span className="font-bold text-sm text-amber-300">
            {formatDistance(result.aggregate_distance_m)}
          </span>
        </div>
        <div className="bg-white/5 p-2 rounded-xl border border-white/5">
          <span className="block text-[10px] text-indigo-200 font-medium">Max Journey</span>
          <span className="font-bold text-sm text-white">
            {formatDistance(result.max_distance_m)}
          </span>
        </div>
        <div className="bg-white/5 p-2 rounded-xl border border-white/5">
          <span className="block text-[10px] text-indigo-200 font-medium">Average Trip</span>
          <span className="font-bold text-sm text-indigo-100">
            {formatDistance(result.avg_distance_m)}
          </span>
        </div>
      </div>

      {/* Diagnostic Metadata Footer */}
      <div className="flex items-center justify-between text-[11px] text-indigo-300/80 pt-1 border-t border-white/10 font-mono">
        <div className="flex items-center space-x-1">
          <Gauge className="w-3 h-3 text-indigo-400" />
          <span>{result.metadata.candidate_nodes_evaluated} nodes evaluated</span>
        </div>
        <div className="flex items-center space-x-1">
          <Clock className="w-3 h-3 text-indigo-400" />
          <span>{formatMs(result.metadata.execution_time_ms)}</span>
          {result.metadata.cache_hit && (
            <span className="bg-emerald-500/20 text-emerald-300 text-[9px] px-1 rounded ml-1 font-sans">
              cached
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
