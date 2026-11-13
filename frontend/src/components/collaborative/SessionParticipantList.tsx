import React from 'react';
import { Users, UserX, CheckCircle2, Clock } from 'lucide-react';
import { SessionParticipantPublic, UserRole } from '../../types/session';
import { getParticipantColor } from '../../utils/colors';

interface SessionParticipantListProps {
  participants: SessionParticipantPublic[];
  userRole: UserRole;
  currentParticipantId?: string | null;
  onRemoveParticipant?: (participantId: string) => void;
}

export const SessionParticipantList: React.FC<SessionParticipantListProps> = ({
  participants,
  userRole,
  currentParticipantId,
  onRemoveParticipant,
}) => {
  const readyCount = participants.filter((p) => p.location_submitted).length;

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-blue-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Participants ({participants.length})
          </h3>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
          {readyCount} ready
        </span>
      </div>

      {/* Participant List */}
      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
        {participants.length === 0 ? (
          <div className="text-center py-6 text-xs text-slate-500">
            No participants have joined yet. Share the invite code to invite others!
          </div>
        ) : (
          participants.map((p, idx) => {
            const color = getParticipantColor(idx);
            const isSelf = currentParticipantId === p.id;

            return (
              <div
                key={p.id}
                className="flex items-center justify-between p-2.5 rounded-xl bg-slate-800/60 border border-slate-700/60 transition hover:border-slate-600"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  {/* Colored Avatar */}
                  <div
                    className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0 shadow"
                    style={{ backgroundColor: color }}
                  >
                    {p.display_name.charAt(0).toUpperCase()}
                  </div>

                  {/* Name and Online Status */}
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-semibold text-white truncate max-w-[120px]">
                        {p.display_name}
                      </span>
                      {isSelf && (
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-500/20 text-blue-400 font-medium">
                          You
                        </span>
                      )}
                      <span
                        className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                          p.is_online ? 'bg-emerald-400' : 'bg-slate-500'
                        }`}
                        title={p.is_online ? 'Online' : 'Offline'}
                      />
                    </div>

                    {/* Location Badge */}
                    <div className="flex items-center gap-1 text-[11px] text-slate-400 mt-0.5">
                      {p.location_submitted ? (
                        <span className="inline-flex items-center gap-1 text-emerald-400 font-mono">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>
                            {p.latitude?.toFixed(4)}, {p.longitude?.toFixed(4)}
                          </span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-amber-400">
                          <Clock className="w-3 h-3" />
                          <span>Waiting for location</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Host Action: Remove Participant */}
                {userRole === 'HOST' && onRemoveParticipant && (
                  <button
                    onClick={() => {
                      if (confirm(`Remove ${p.display_name} from this meeting?`)) {
                        onRemoveParticipant(p.id);
                      }
                    }}
                    title="Remove participant"
                    className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition"
                  >
                    <UserX className="w-4 h-4" />
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
