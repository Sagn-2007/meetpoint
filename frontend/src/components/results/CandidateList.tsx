import React from 'react';
import { CandidateRecommendation } from '../../types';
import { formatCoordinate, formatDistance } from '../../utils/formatters';

interface CandidateListProps {
  candidates: CandidateRecommendation[];
  selectedCandidateNodeId: number | string | null;
  onSelectCandidate: (candidate: CandidateRecommendation) => void;
  bestAggregateDist: number;
}

export const CandidateList: React.FC<CandidateListProps> = ({
  candidates,
  selectedCandidateNodeId,
  onSelectCandidate,
  bestAggregateDist,
}) => {
  if (candidates.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-xs text-slate-900">
          Ranked Alternatives (Top {candidates.length})
        </span>
        <span className="text-[11px] text-slate-400">Click to locate on map</span>
      </div>

      <div className="space-y-1.5 max-h-[220px] overflow-y-auto pr-0.5">
        {candidates.map((cand) => {
          const isSelected = selectedCandidateNodeId === cand.node_id;
          const isWinner = cand.rank === 1;
          const delta = cand.aggregate_distance_m - bestAggregateDist;

          return (
            <div
              key={`cand-item-${cand.node_id}-${cand.rank}`}
              onClick={() => onSelectCandidate(cand)}
              className={`p-2.5 rounded-xl border text-xs cursor-pointer transition-all flex items-center justify-between ${
                isSelected
                  ? 'bg-indigo-50 border-indigo-400 ring-1 ring-indigo-400 shadow-xs'
                  : isWinner
                  ? 'bg-amber-50/50 border-amber-200 hover:border-amber-300'
                  : 'bg-white border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="flex items-center space-x-2.5 min-w-0">
                <span
                  className={`w-5 h-5 rounded-full flex items-center justify-center font-bold text-[10px] flex-shrink-0 ${
                    isWinner
                      ? 'bg-amber-400 text-amber-950 font-extrabold shadow-xs'
                      : 'bg-slate-700 text-white'
                  }`}
                >
                  #{cand.rank}
                </span>

                <div className="min-w-0">
                  <div className="flex items-center space-x-1.5">
                    <span className="font-semibold text-slate-800">
                      {isWinner ? 'Optimal Choice' : `Option #${cand.rank}`}
                    </span>
                    {delta > 0 && (
                      <span className="text-[10px] text-slate-400 font-normal">
                        (+{formatDistance(delta)})
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] font-mono text-slate-400 truncate">
                    {formatCoordinate(cand.location)}
                  </div>
                </div>
              </div>

              <div className="text-right flex-shrink-0 pl-2">
                <div className="font-bold text-slate-900">
                  {formatDistance(cand.aggregate_distance_m)}
                </div>
                <div className="text-[10px] text-slate-400">
                  Max: {formatDistance(cand.max_distance_m)}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
