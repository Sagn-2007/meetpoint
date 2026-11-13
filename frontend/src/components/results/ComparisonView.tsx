import React from 'react';
import { ComparisonSummary, ObjectiveResult } from '../../types';
import { Scale, CheckCircle2, AlertTriangle } from 'lucide-react';
import { formatCoordinate, formatDistance } from '../../utils/formatters';

interface ComparisonViewProps {
  comparison: ComparisonSummary;
  medianResult?: ObjectiveResult | null;
  centerResult?: ObjectiveResult | null;
  activeView: 'median' | 'center';
  onSwitchView: (view: 'median' | 'center') => void;
}

export const ComparisonView: React.FC<ComparisonViewProps> = ({
  comparison,
  activeView,
  onSwitchView,
}) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-3.5 shadow-xs space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-100">
        <div className="flex items-center space-x-2">
          <Scale className="w-4 h-4 text-indigo-600" />
          <span className="font-bold text-xs text-slate-900">Optimization Comparison</span>
        </div>

        {comparison.same_optimal_node ? (
          <span className="inline-flex items-center space-x-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-100">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            <span>Identical Winner</span>
          </span>
        ) : (
          <span className="inline-flex items-center space-x-1 text-[11px] font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-100">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            <span>Different Locations</span>
          </span>
        )}
      </div>

      {/* Explanation Banner */}
      <div className="p-2.5 bg-slate-50 rounded-xl text-slate-600 text-xs leading-relaxed border border-slate-100">
        {comparison.explanation}
      </div>

      {/* Side-by-Side Comparison Columns */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        {/* 1-Median Card */}
        <div
          onClick={() => onSwitchView('median')}
          className={`p-2.5 rounded-xl border cursor-pointer transition-all ${
            activeView === 'median'
              ? 'bg-indigo-50/60 border-indigo-400 ring-1 ring-indigo-400 shadow-xs'
              : 'bg-white border-slate-200 hover:border-slate-300'
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-bold text-indigo-950">1-Median</span>
            {activeView === 'median' && (
              <span className="text-[10px] bg-indigo-600 text-white px-1.5 py-0.2 rounded font-semibold">
                Viewing
              </span>
            )}
          </div>
          <div className="space-y-1 text-[11px]">
            <div>
              <span className="text-slate-400 block text-[10px]">Total Distance</span>
              <span className="font-bold text-slate-800 text-xs">
                {formatDistance(comparison.median_aggregate_distance_m)}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Max Individual</span>
              <span className="font-semibold text-slate-700">
                {formatDistance(comparison.median_max_distance_m)}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Location</span>
              <span className="font-mono text-[10px] text-slate-600 truncate block">
                {formatCoordinate(comparison.median_location)}
              </span>
            </div>
          </div>
        </div>

        {/* 1-Center Card */}
        <div
          onClick={() => onSwitchView('center')}
          className={`p-2.5 rounded-xl border cursor-pointer transition-all ${
            activeView === 'center'
              ? 'bg-indigo-50/60 border-indigo-400 ring-1 ring-indigo-400 shadow-xs'
              : 'bg-white border-slate-200 hover:border-slate-300'
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-bold text-indigo-950">1-Center</span>
            {activeView === 'center' && (
              <span className="text-[10px] bg-indigo-600 text-white px-1.5 py-0.2 rounded font-semibold">
                Viewing
              </span>
            )}
          </div>
          <div className="space-y-1 text-[11px]">
            <div>
              <span className="text-slate-400 block text-[10px]">Total Distance</span>
              <span className="font-bold text-slate-800 text-xs">
                {formatDistance(comparison.center_aggregate_distance_m)}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Max Individual</span>
              <span className="font-semibold text-slate-700">
                {formatDistance(comparison.center_max_distance_m)}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Location</span>
              <span className="font-mono text-[10px] text-slate-600 truncate block">
                {formatCoordinate(comparison.center_location)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Trade-off Summary if different */}
      {!comparison.same_optimal_node && (
        <div className="text-[11px] text-slate-600 bg-amber-50/70 p-2 rounded-xl border border-amber-200/60 space-y-1">
          <div className="font-semibold text-amber-900">Trade-Off Analysis:</div>
          <div>
            • 1-Median saves{' '}
            <span className="font-bold text-amber-950">
              {formatDistance(comparison.aggregate_distance_difference_m)}
            </span>{' '}
            in total group travel.
          </div>
          <div>
            • 1-Center reduces the worst journey by{' '}
            <span className="font-bold text-amber-950">
              {formatDistance(comparison.max_distance_difference_m)}
            </span>
            .
          </div>
        </div>
      )}
    </div>
  );
};
