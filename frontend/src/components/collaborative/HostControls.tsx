import React from 'react';
import { Calculator, RotateCcw, XCircle, Sliders, Loader2 } from 'lucide-react';
import { MeetingSessionPublic } from '../../types/session';

interface HostControlsProps {
  session: MeetingSessionPublic;
  readyParticipantCount: number;
  isCalculating: boolean;
  hasCalculated: boolean;
  onOptimize: () => void;
  onOpenSettings: () => void;
  onCloseSession: () => void;
}

export const HostControls: React.FC<HostControlsProps> = ({
  session,
  readyParticipantCount,
  isCalculating,
  hasCalculated,
  onOptimize,
  onOpenSettings,
  onCloseSession,
}) => {
  const canOptimize = readyParticipantCount >= 2 && !isCalculating;

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-wider text-amber-400">
          Host Controls
        </h3>
        <span className="text-[11px] font-mono text-slate-400">
          Mode: {session.network_type} • {session.optimization_objective}
        </span>
      </div>

      {/* Main Calculate / Recalculate Button */}
      <button
        onClick={onOptimize}
        disabled={!canOptimize}
        className={`w-full py-3 px-4 rounded-xl font-bold text-sm shadow-lg transition flex items-center justify-center gap-2 ${
          canOptimize
            ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-600/30'
            : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/50'
        }`}
      >
        {isCalculating ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin text-white" />
            <span>Calculating Optimal Meeting Point...</span>
          </>
        ) : hasCalculated ? (
          <>
            <RotateCcw className="w-4 h-4" />
            <span>Recalculate Meeting Point</span>
          </>
        ) : (
          <>
            <Calculator className="w-4 h-4" />
            <span>Calculate Optimal Meeting Point</span>
          </>
        )}
      </button>

      {/* Helper notice if not enough participants */}
      {readyParticipantCount < 2 && (
        <p className="text-[11px] text-slate-400 text-center">
          Requires at least 2 participants with submitted coordinates ({readyParticipantCount}/2 ready)
        </p>
      )}

      {/* Auxiliary Host Actions */}
      <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-800">
        <button
          onClick={onOpenSettings}
          className="py-2 px-3 rounded-xl text-xs font-semibold bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition flex items-center justify-center gap-1.5"
        >
          <Sliders className="w-3.5 h-3.5 text-blue-400" />
          <span>Settings</span>
        </button>

        <button
          onClick={() => {
            if (confirm('Are you sure you want to close this session? All participants will be disconnected.')) {
              onCloseSession();
            }
          }}
          className="py-2 px-3 rounded-xl text-xs font-semibold bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition flex items-center justify-center gap-1.5"
        >
          <XCircle className="w-3.5 h-3.5" />
          <span>Close Room</span>
        </button>
      </div>
    </div>
  );
};
