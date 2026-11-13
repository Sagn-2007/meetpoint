import React from 'react';
import { Navigation, Sparkles, RefreshCw, Users } from 'lucide-react';

interface NavbarProps {
  backendStatus: 'healthy' | 'unhealthy' | 'offline' | 'checking';
  onLoadSample: () => void;
  onReset: () => void;
  participantCount: number;
  onSwitchToCollaborative?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  backendStatus,
  onLoadSample,
  onReset,
  participantCount,
  onSwitchToCollaborative,
}) => {
  return (
    <header className="bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between shadow-sm z-30 flex-shrink-0">
      <div className="flex items-center space-x-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-indigo-100">
          <Navigation className="w-5 h-5 -rotate-45" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="font-bold text-lg tracking-tight text-slate-900">
              Meet<span className="text-indigo-600">Point</span>
            </h1>
            <span className="text-[10px] font-semibold bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full border border-indigo-100">
              Network Optimizer
            </span>
          </div>
          <p className="text-xs text-slate-500 hidden sm:block">
            True road & pedestrian network 1-Median & 1-Center meeting engine
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-2 sm:space-x-3">
        {/* Backend health status badge */}
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-50 border border-slate-200">
          <span
            className={`w-2 h-2 rounded-full ${
              backendStatus === 'healthy'
                ? 'bg-emerald-500 animate-pulse'
                : backendStatus === 'checking'
                ? 'bg-amber-400'
                : 'bg-rose-500'
            }`}
          />
          <span className="text-slate-600 capitalize text-[11px] hidden sm:inline">
            Engine: {backendStatus}
          </span>
        </div>

        {/* Switch to Collaborative Mode */}
        {onSwitchToCollaborative && (
          <button
            onClick={onSwitchToCollaborative}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors shadow-sm"
          >
            <Users className="w-3.5 h-3.5" />
            <span>Multi-User Rooms</span>
          </button>
        )}

        {/* Load Preset Demo Button */}
        <button
          onClick={onLoadSample}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors border border-slate-200"
          title="Load sample participant coordinates for quick demo"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
          <span className="hidden md:inline">Sample Demo</span>
        </button>

        {/* Reset Button */}
        {participantCount > 0 && (
          <button
            onClick={onReset}
            className="inline-flex items-center space-x-1 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors border border-transparent hover:border-rose-100"
            title="Clear all participants and results"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Reset</span>
          </button>
        )}
      </div>
    </header>
  );
};
