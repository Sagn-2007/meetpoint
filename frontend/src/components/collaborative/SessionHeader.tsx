import React, { useState } from 'react';
import {
  Compass,
  Copy,
  Check,
  Crown,
  User,
  LogOut,
  Sliders,
  Share2,
} from 'lucide-react';
import { MeetingSessionPublic, UserRole } from '../../types/session';
import { ConnectionStatus } from '../../hooks/useSessionWebSocket';

interface SessionHeaderProps {
  session: MeetingSessionPublic;
  userRole: UserRole;
  currentParticipantName?: string;
  wsStatus: ConnectionStatus;
  onOpenSettings?: () => void;
  onLeave: () => void;
}

export const SessionHeader: React.FC<SessionHeaderProps> = ({
  session,
  userRole,
  currentParticipantName,
  wsStatus,
  onOpenSettings,
  onLeave,
}) => {
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);

  const invitationUrl = `${window.location.origin}${window.location.pathname}#/join/${session.invitation_code}`;

  const copyLink = () => {
    navigator.clipboard.writeText(invitationUrl);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  const copyCode = () => {
    navigator.clipboard.writeText(session.invitation_code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  return (
    <header className="bg-slate-900 border-b border-slate-800 px-6 py-3.5 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-20">
      {/* Left: Brand & Meeting Info */}
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20 shrink-0">
          <Compass className="w-6 h-6 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-bold text-base text-white tracking-tight leading-tight">
              {session.title}
            </h1>
            {userRole === 'HOST' ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <Crown className="w-3 h-3" />
                Host
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                <User className="w-3 h-3" />
                {currentParticipantName || 'Participant'}
              </span>
            )}
          </div>
          {session.description && (
            <p className="text-xs text-slate-400 line-clamp-1 max-w-md">{session.description}</p>
          )}
        </div>
      </div>

      {/* Center: Share Code & Link */}
      <div className="flex items-center gap-2 bg-slate-800/80 border border-slate-700/80 rounded-xl px-3 py-1.5">
        <div className="flex items-center gap-1.5 mr-2">
          <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400">
            Room Code:
          </span>
          <span className="font-mono font-bold text-sm text-emerald-400 tracking-wider">
            {session.invitation_code}
          </span>
        </div>

        <button
          onClick={copyCode}
          title="Copy room code"
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700 transition"
        >
          {copiedCode ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
        </button>

        <button
          onClick={copyLink}
          title="Copy invite URL"
          className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-700 transition"
        >
          {copiedLink ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400">Copied!</span>
            </>
          ) : (
            <>
              <Share2 className="w-3.5 h-3.5 text-blue-400" />
              <span>Copy Link</span>
            </>
          )}
        </button>
      </div>

      {/* Right: Status & Actions */}
      <div className="flex items-center gap-3">
        {/* WS Connection Status */}
        <div className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700">
          <span
            className={`w-2 h-2 rounded-full ${
              wsStatus === 'connected'
                ? 'bg-emerald-400 animate-pulse'
                : wsStatus === 'reconnecting' || wsStatus === 'connecting'
                ? 'bg-amber-400 animate-ping'
                : 'bg-rose-400'
            }`}
          />
          <span className="text-slate-300 capitalize text-[11px] font-mono">
            {wsStatus === 'connected' ? 'Live' : wsStatus}
          </span>
        </div>

        {/* Host Settings */}
        {userRole === 'HOST' && onOpenSettings && (
          <button
            onClick={onOpenSettings}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-700 transition"
            title="Session settings"
          >
            <Sliders className="w-4 h-4" />
          </button>
        )}

        {/* Leave Room Button */}
        <button
          onClick={onLeave}
          className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl border border-rose-500/30 text-rose-400 hover:bg-rose-500/10 transition"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Exit Room</span>
        </button>
      </div>
    </header>
  );
};
