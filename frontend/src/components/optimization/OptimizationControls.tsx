import React from 'react';
import { NetworkType, OptimizationObjective } from '../../types';
import { Footprints, Car, Scale, Users, Target, Loader2, AlertCircle } from 'lucide-react';

interface OptimizationControlsProps {
  objective: OptimizationObjective;
  onObjectiveChange: (obj: OptimizationObjective) => void;
  networkType: NetworkType;
  onNetworkTypeChange: (type: NetworkType) => void;
  topK: number;
  onTopKChange: (k: number) => void;
  onCalculate: () => void;
  isLoading: boolean;
  participantCount: number;
  errorMessage: string | null;
}

export const OptimizationControls: React.FC<OptimizationControlsProps> = ({
  objective,
  onObjectiveChange,
  networkType,
  onNetworkTypeChange,
  topK,
  onTopKChange,
  onCalculate,
  isLoading,
  participantCount,
  errorMessage,
}) => {
  const isReady = participantCount >= 2;

  return (
    <div className="space-y-4 pt-2 border-t border-slate-200">
      {/* 1. Objective Selector */}
      <div>
        <label className="block text-xs font-semibold text-slate-900 mb-1.5">
          Optimization Objective
        </label>
        <div className="grid grid-cols-3 gap-1.5">
          {/* 1-Median */}
          <button
            type="button"
            onClick={() => onObjectiveChange('median')}
            className={`p-2.5 rounded-xl border text-left transition-all ${
              objective === 'median'
                ? 'bg-indigo-50 border-indigo-500 ring-1 ring-indigo-500 shadow-xs'
                : 'bg-white border-slate-200 hover:border-slate-300 text-slate-700'
            }`}
          >
            <div className="flex items-center space-x-1.5 mb-1">
              <Users
                className={`w-3.5 h-3.5 ${
                  objective === 'median' ? 'text-indigo-600' : 'text-slate-400'
                }`}
              />
              <span className="font-bold text-xs">1-Median</span>
            </div>
            <p className="text-[10px] text-slate-500 leading-tight">
              Minimizes total distance for all
            </p>
          </button>

          {/* 1-Center */}
          <button
            type="button"
            onClick={() => onObjectiveChange('center')}
            className={`p-2.5 rounded-xl border text-left transition-all ${
              objective === 'center'
                ? 'bg-indigo-50 border-indigo-500 ring-1 ring-indigo-500 shadow-xs'
                : 'bg-white border-slate-200 hover:border-slate-300 text-slate-700'
            }`}
          >
            <div className="flex items-center space-x-1.5 mb-1">
              <Target
                className={`w-3.5 h-3.5 ${
                  objective === 'center' ? 'text-indigo-600' : 'text-slate-400'
                }`}
              />
              <span className="font-bold text-xs">1-Center</span>
            </div>
            <p className="text-[10px] text-slate-500 leading-tight">
              Minimizes longest trip (fairness)
            </p>
          </button>

          {/* Compare Both */}
          <button
            type="button"
            onClick={() => onObjectiveChange('compare')}
            className={`p-2.5 rounded-xl border text-left transition-all ${
              objective === 'compare'
                ? 'bg-indigo-50 border-indigo-500 ring-1 ring-indigo-500 shadow-xs'
                : 'bg-white border-slate-200 hover:border-slate-300 text-slate-700'
            }`}
          >
            <div className="flex items-center space-x-1.5 mb-1">
              <Scale
                className={`w-3.5 h-3.5 ${
                  objective === 'compare' ? 'text-indigo-600' : 'text-slate-400'
                }`}
              />
              <span className="font-bold text-xs">Compare</span>
            </div>
            <p className="text-[10px] text-slate-500 leading-tight">
              Evaluates both side-by-side
            </p>
          </button>
        </div>
      </div>

      {/* 2. Network Type & Top-K in 2 columns */}
      <div className="grid grid-cols-2 gap-3">
        {/* Network Mode */}
        <div>
          <label className="block text-xs font-semibold text-slate-900 mb-1.5">
            Network Mode
          </label>
          <div className="inline-flex w-full p-1 bg-slate-100 rounded-xl border border-slate-200">
            <button
              type="button"
              onClick={() => onNetworkTypeChange('walk')}
              className={`flex-1 py-1.5 text-xs font-medium rounded-lg flex items-center justify-center space-x-1.5 transition-all ${
                networkType === 'walk'
                  ? 'bg-white text-indigo-600 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Footprints className="w-3.5 h-3.5" />
              <span>Walk</span>
            </button>
            <button
              type="button"
              onClick={() => onNetworkTypeChange('drive')}
              className={`flex-1 py-1.5 text-xs font-medium rounded-lg flex items-center justify-center space-x-1.5 transition-all ${
                networkType === 'drive'
                  ? 'bg-white text-indigo-600 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Car className="w-3.5 h-3.5" />
              <span>Drive</span>
            </button>
          </div>
        </div>

        {/* Top-K Selector */}
        <div>
          <div className="flex justify-between items-center mb-1.5">
            <label className="text-xs font-semibold text-slate-900">
              Alternatives (Top-K)
            </label>
            <span className="text-xs font-mono font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.2 rounded border border-indigo-100">
              {topK}
            </span>
          </div>
          <input
            type="range"
            min={1}
            max={15}
            value={topK}
            onChange={(e) => onTopKChange(parseInt(e.target.value, 10))}
            className="w-full accent-indigo-600 h-1.5 bg-slate-200 rounded-lg cursor-pointer mt-2"
          />
        </div>
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-start space-x-2 text-rose-800 text-xs">
          <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold block mb-0.5">Calculation Error</span>
            <span>{errorMessage}</span>
          </div>
        </div>
      )}

      {/* 3. Primary Calculate Action Button */}
      <button
        type="button"
        onClick={onCalculate}
        disabled={!isReady || isLoading}
        className={`w-full py-3 px-4 rounded-xl font-bold text-sm shadow-md transition-all flex items-center justify-center space-x-2 ${
          !isReady
            ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed shadow-none'
            : isLoading
            ? 'bg-indigo-500 text-white cursor-wait'
            : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-200 hover:shadow-indigo-300 active:scale-[0.99]'
        }`}
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin text-white" />
            <span>Finding Optimal Meeting Point...</span>
          </>
        ) : (
          <>
            <Target className="w-4 h-4" />
            <span>
              {isReady
                ? 'Calculate Optimal Meeting Point'
                : `Add at least ${2 - participantCount} more participant${
                    2 - participantCount === 1 ? '' : 's'
                  }`}
            </span>
          </>
        )}
      </button>
    </div>
  );
};
