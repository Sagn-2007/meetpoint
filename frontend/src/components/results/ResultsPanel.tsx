import React, { useState } from 'react';
import {
  CandidateRecommendation,
  OptimizeMeetingResponse,
  Participant,
} from '../../types';
import { OptimalMeetingCard } from './OptimalMeetingCard';
import { ComparisonView } from './ComparisonView';
import { CandidateList } from './CandidateList';
import { RouteList } from './RouteList';
import { Navigation, Sparkles } from 'lucide-react';

interface ResultsPanelProps {
  result: OptimizeMeetingResponse;
  participants: Participant[];
  selectedCandidateNodeId: number | string | null;
  onSelectCandidate: (candidate: CandidateRecommendation) => void;
  visibleRouteIds: Set<string>;
  onToggleRouteVisibility: (participantId: string) => void;
  compareActiveView: 'median' | 'center';
  onSwitchCompareView: (view: 'median' | 'center') => void;
}

export const ResultsPanel: React.FC<ResultsPanelProps> = ({
  result,
  participants,
  selectedCandidateNodeId,
  onSelectCandidate,
  visibleRouteIds,
  onToggleRouteVisibility,
  compareActiveView,
  onSwitchCompareView,
}) => {
  const [activeTab, setActiveTab] = useState<'routes' | 'alternatives'>('routes');

  // Display result depending on compare view if in compare mode
  const displayedResult =
    result.objective === 'compare'
      ? compareActiveView === 'center' && result.center_result
        ? {
            ...result,
            optimal_node_id: result.center_result.optimal_node_id,
            optimal_location: result.center_result.optimal_location,
            aggregate_distance_m: result.center_result.aggregate_distance_m,
            max_distance_m: result.center_result.max_distance_m,
            avg_distance_m: result.center_result.avg_distance_m,
            individual_distances: result.center_result.individual_distances,
            candidates: result.center_result.candidates,
          }
        : result.median_result
        ? {
            ...result,
            optimal_node_id: result.median_result.optimal_node_id,
            optimal_location: result.median_result.optimal_location,
            aggregate_distance_m: result.median_result.aggregate_distance_m,
            max_distance_m: result.median_result.max_distance_m,
            avg_distance_m: result.median_result.avg_distance_m,
            individual_distances: result.median_result.individual_distances,
            candidates: result.median_result.candidates,
          }
        : result
      : result;

  return (
    <div className="space-y-4 pt-3 border-t border-slate-200">
      {/* 1. Optimal Result Card */}
      <OptimalMeetingCard result={displayedResult} />

      {/* 2. Comparison Summary if objective is 'compare' */}
      {result.comparison && (
        <ComparisonView
          comparison={result.comparison}
          medianResult={result.median_result}
          centerResult={result.center_result}
          activeView={compareActiveView}
          onSwitchView={onSwitchCompareView}
        />
      )}

      {/* 3. Tab Buttons: Routes vs Alternatives */}
      <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('routes')}
          className={`flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center space-x-1.5 ${
            activeTab === 'routes'
              ? 'bg-white text-indigo-600 shadow-xs'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <Navigation className="w-3.5 h-3.5" />
          <span>Individual Routes</span>
        </button>
        <button
          onClick={() => setActiveTab('alternatives')}
          className={`flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center space-x-1.5 ${
            activeTab === 'alternatives'
              ? 'bg-white text-indigo-600 shadow-xs'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Top Alternatives ({displayedResult.candidates.length})</span>
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'routes' ? (
        <RouteList
          routes={displayedResult.individual_distances}
          participants={participants}
          visibleRouteIds={visibleRouteIds}
          onToggleRouteVisibility={onToggleRouteVisibility}
          networkType={displayedResult.metadata.network_type}
        />
      ) : (
        <CandidateList
          candidates={displayedResult.candidates}
          selectedCandidateNodeId={selectedCandidateNodeId}
          onSelectCandidate={onSelectCandidate}
          bestAggregateDist={displayedResult.aggregate_distance_m}
        />
      )}
    </div>
  );
};
