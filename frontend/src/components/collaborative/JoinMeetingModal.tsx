import React, { useState, useEffect } from 'react';
import {
  X,
  LogIn,
  Compass,
  AlertCircle,
  Loader2,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';
import { MeetingSessionPublic, JoinSessionResponse } from '../../types/session';
import { getSessionByCode, joinSession } from '../../services/sessionApi';

interface JoinMeetingModalProps {
  initialCode?: string;
  onClose: () => void;
  onSuccess: (joinData: JoinSessionResponse) => void;
}

export const JoinMeetingModal: React.FC<JoinMeetingModalProps> = ({
  initialCode = '',
  onClose,
  onSuccess,
}) => {
  const [code, setCode] = useState(initialCode.toUpperCase());
  const [displayName, setDisplayName] = useState('');
  const [sessionInfo, setSessionInfo] = useState<MeetingSessionPublic | null>(null);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Explicit location state
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [locationStatus, setLocationStatus] = useState<string | null>(null);

  // Auto-fetch session details when code is 8 chars
  useEffect(() => {
    const cleanCode = code.trim().toUpperCase();
    if (cleanCode.length === 8) {
      setIsLoadingSession(true);
      setError(null);
      getSessionByCode(cleanCode)
        .then((info) => {
          setSessionInfo(info);
          if (info.status === 'closed') {
            setError('This meeting session is closed.');
          } else if (info.is_expired) {
            setError('This meeting session has expired.');
          }
        })
        .catch((err) => {
          setSessionInfo(null);
          setError(err?.message || 'Meeting session not found.');
        })
        .finally(() => {
          setIsLoadingSession(false);
        });
    } else {
      setSessionInfo(null);
    }
  }, [code]);

  // Request browser GPS explicitly
  const handleRequestGps = () => {
    if (!navigator.geolocation) {
      setLocationStatus('Geolocation is not supported by your browser.');
      return;
    }

    setIsLocating(true);
    setLocationStatus('Requesting current GPS position...');

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCoords({
          lat: Number(position.coords.latitude.toFixed(6)),
          lon: Number(position.coords.longitude.toFixed(6)),
        });
        setIsLocating(false);
        setLocationStatus('GPS coordinates captured.');
      },
      (err) => {
        setIsLocating(false);
        setLocationStatus(`Could not access GPS (${err.message}). You can still join and pick your location manually.`);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!displayName.trim()) {
      setError('Please enter your name.');
      return;
    }
    if (!code.trim() || code.trim().length !== 8) {
      setError('Please enter a valid 8-character invitation code.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await joinSession(code.trim(), {
        display_name: displayName.trim(),
        latitude: coords ? coords.lat : undefined,
        longitude: coords ? coords.lon : undefined,
      });
      onSuccess(response);
    } catch (err: any) {
      setError(err?.message || 'Failed to join meeting session.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <LogIn className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-bold text-white">Join Meeting Session</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleJoin} className="p-6 space-y-5 overflow-y-auto flex-1">
          {error && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-start gap-2">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Invitation Code */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Invitation Code *
            </label>
            <input
              type="text"
              required
              maxLength={8}
              placeholder="e.g., ABC123XY"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-3.5 py-2.5 text-base font-mono tracking-widest text-white uppercase placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          {/* Session Preview Card */}
          {isLoadingSession && (
            <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700 flex items-center justify-center gap-2 text-sm text-slate-400">
              <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
              <span>Verifying session code...</span>
            </div>
          )}

          {sessionInfo && (
            <div className="p-4 rounded-xl bg-slate-800/60 border border-emerald-500/30 text-left space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Active Session
                </span>
                <span className="text-xs text-slate-400">
                  {sessionInfo.participants_count} joined
                </span>
              </div>
              <h3 className="font-bold text-base text-white">{sessionInfo.title}</h3>
              {sessionInfo.description && (
                <p className="text-xs text-slate-300 line-clamp-2">{sessionInfo.description}</p>
              )}
              <div className="flex items-center gap-3 pt-1 text-[11px] text-slate-400 font-mono">
                <span>Mode: {sessionInfo.network_type}</span>
                <span>•</span>
                <span>Objective: {sessionInfo.optimization_objective}</span>
              </div>
            </div>
          )}

          {/* Display Name */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Your Display Name *
            </label>
            <input
              type="text"
              required
              placeholder="e.g., Alex, Jordan, Sarah"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          {/* Privacy & Location Sharing Card */}
          <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700 space-y-3">
            <div className="flex items-start gap-2.5">
              <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                  Location Privacy Notice
                </h4>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  MeetPoint only reads your GPS coordinates upon explicit action. We do not run
                  background tracking or monitor your movements. You can update or withdraw your
                  location at any time inside the room.
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-700/60 flex flex-col gap-2">
              <button
                type="button"
                onClick={handleRequestGps}
                disabled={isLocating}
                className="w-full py-2.5 px-3 rounded-lg text-xs font-semibold bg-slate-700 hover:bg-slate-600 text-slate-100 flex items-center justify-center gap-2 transition disabled:opacity-50"
              >
                {isLocating ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Accessing GPS...</span>
                  </>
                ) : coords ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>GPS Captured ({coords.lat}, {coords.lon})</span>
                  </>
                ) : (
                  <>
                    <Compass className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Share My Current GPS Location</span>
                  </>
                )}
              </button>

              <div className="text-center">
                <span className="text-[11px] text-slate-500">
                  Or join now and select your location on the map later
                </span>
              </div>

              {locationStatus && (
                <p className="text-[11px] text-emerald-400 font-mono text-center">
                  {locationStatus}
                </p>
              )}
            </div>
          </div>

          {/* Footer Action */}
          <div className="pt-2 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !sessionInfo || sessionInfo.status !== 'active'}
              className="px-5 py-2.5 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/30 transition flex items-center gap-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Joining...</span>
                </>
              ) : (
                <span>Enter Room</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
