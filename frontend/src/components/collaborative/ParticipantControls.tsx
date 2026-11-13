import React from 'react';
import {
  Compass,
  MapPin,
  Trash2,
  LogOut,
  Loader2,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';
import { SessionParticipantPublic } from '../../types/session';

interface ParticipantControlsProps {
  currentParticipant: SessionParticipantPublic | null;
  isMapPicking: boolean;
  onToggleMapPicking: () => void;
  onSubmitGps: () => void;
  onWithdrawLocation: () => void;
  onLeave: () => void;
  isLocating: boolean;
}

export const ParticipantControls: React.FC<ParticipantControlsProps> = ({
  currentParticipant,
  isMapPicking,
  onToggleMapPicking,
  onSubmitGps,
  onWithdrawLocation,
  onLeave,
  isLocating,
}) => {
  const hasLocation = currentParticipant?.location_submitted;

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-wider text-blue-400">
          Your Location & Actions
        </h3>
        {hasLocation ? (
          <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" />
            Location Shared
          </span>
        ) : (
          <span className="text-[11px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
            Not Shared
          </span>
        )}
      </div>

      {/* Coordinate status */}
      {hasLocation && (
        <div className="text-xs bg-slate-800/80 p-2.5 rounded-xl border border-slate-700 font-mono text-slate-300 flex items-center justify-between">
          <span>
            {currentParticipant?.latitude?.toFixed(5)}, {currentParticipant?.longitude?.toFixed(5)}
          </span>
          <button
            onClick={onWithdrawLocation}
            title="Withdraw location"
            className="text-rose-400 hover:text-rose-300 text-xs flex items-center gap-1 hover:underline ml-2"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Withdraw</span>
          </button>
        </div>
      )}

      {/* Sharing Buttons */}
      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={onSubmitGps}
          disabled={isLocating}
          className="py-2.5 px-3 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white shadow transition flex items-center justify-center gap-1.5 disabled:opacity-50"
        >
          {isLocating ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Locating...</span>
            </>
          ) : (
            <>
              <Compass className="w-3.5 h-3.5" />
              <span>{hasLocation ? 'Update GPS' : 'Share GPS'}</span>
            </>
          )}
        </button>

        <button
          onClick={onToggleMapPicking}
          className={`py-2.5 px-3 rounded-xl text-xs font-semibold border transition flex items-center justify-center gap-1.5 ${
            isMapPicking
              ? 'bg-amber-500/20 border-amber-500 text-amber-300'
              : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
          }`}
        >
          <MapPin className="w-3.5 h-3.5 text-amber-400" />
          <span>{isMapPicking ? 'Click Map Now' : 'Pick on Map'}</span>
        </button>
      </div>

      {isMapPicking && (
        <p className="text-[11px] text-amber-400 bg-amber-500/10 p-2 rounded-lg border border-amber-500/20 text-center animate-pulse">
          Click anywhere on the map to set your location coordinates.
        </p>
      )}

      {/* Privacy Guarantee */}
      <div className="flex items-start gap-2 pt-1 border-t border-slate-800 text-[11px] text-slate-400">
        <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
        <span>
          Explicit sharing only. No background GPS tracking. You can withdraw your coordinates anytime.
        </span>
      </div>

      {/* Leave Session */}
      <button
        onClick={() => {
          if (confirm('Leave this meeting session?')) {
            onLeave();
          }
        }}
        className="w-full py-2 px-3 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 border border-slate-700 hover:border-rose-500/30 transition flex items-center justify-center gap-1.5"
      >
        <LogOut className="w-3.5 h-3.5" />
        <span>Leave Session</span>
      </button>
    </div>
  );
};
