import React, { useState, useCallback, useMemo } from 'react';
import {
  AlertTriangle,
  RotateCcw,
  MapPin,
} from 'lucide-react';
import {
  MeetingSessionPublic,
  SessionParticipantPublic,
  UserRole,
  WebSocketMessage,
} from '../../types/session';
import {
  OptimizeMeetingResponse,
  Participant,
} from '../../types';
import { useSessionWebSocket } from '../../hooks/useSessionWebSocket';
import {
  closeSession,
  leaveSession,
  removeParticipant,
  submitLocation,
  triggerOptimization,
  withdrawLocation,
} from '../../services/sessionApi';
import { SessionHeader } from './SessionHeader';
import { SessionParticipantList } from './SessionParticipantList';
import { HostControls } from './HostControls';
import { ParticipantControls } from './ParticipantControls';
import { SessionSettingsModal } from './SessionSettingsModal';
import { MapView } from '../map/MapView';
import { ResultsPanel } from '../results/ResultsPanel';
import { getParticipantColor } from '../../utils/colors';

interface CollaborativeRoomProps {
  initialSession: MeetingSessionPublic;
  userRole: UserRole;
  token: string;
  currentParticipantId?: string | null;
  onExit: () => void;
}

export const CollaborativeRoom: React.FC<CollaborativeRoomProps> = ({
  initialSession,
  userRole: initialRole,
  token,
  currentParticipantId: initialParticipantId,
  onExit,
}) => {
  // Session State
  const [session, setSession] = useState<MeetingSessionPublic>(initialSession);
  const [userRole, setUserRole] = useState<UserRole>(initialRole);
  const [currentParticipantId, setCurrentParticipantId] = useState<string | null>(
    initialParticipantId || null
  );
  const [participants, setParticipants] = useState<SessionParticipantPublic[]>([]);
  const [result, setResult] = useState<OptimizeMeetingResponse | null>(null);

  // UI & Interaction State
  const [isCalculating, setIsCalculating] = useState(false);
  const [isLocating, setIsLocating] = useState(false);
  const [isMapPicking, setIsMapPicking] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [staleReason, setStaleReason] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Result visualization state
  const [selectedCandidateNodeId, setSelectedCandidateNodeId] = useState<number | string | null>(
    null
  );
  const [visibleRouteIds, setVisibleRouteIds] = useState<Set<string>>(new Set());
  const [compareActiveView, setCompareActiveView] = useState<'median' | 'center'>('median');

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = useCallback(
    (msg: WebSocketMessage) => {
      switch (msg.type) {
        case 'session_snapshot': {
          const snapshot = msg.data;
          setSession(snapshot.session);
          setParticipants(snapshot.participants || []);
          if (snapshot.latest_result) {
            setResult(snapshot.latest_result);
            // Default all routes visible
            if (snapshot.latest_result.individual_distances) {
              const ids = new Set<string>(
                snapshot.latest_result.individual_distances.map(
                  (r: { participant_id: string }) => r.participant_id
                )
              );
              setVisibleRouteIds(ids);
            }
          }
          if (snapshot.user_role) setUserRole(snapshot.user_role);
          if (snapshot.current_participant_id) {
            setCurrentParticipantId(snapshot.current_participant_id);
          }
          break;
        }

        case 'participant_joined': {
          const newParticipant: SessionParticipantPublic = msg.data;
          setParticipants((prev) => {
            const exists = prev.some((p) => p.id === newParticipant.id);
            if (exists) {
              return prev.map((p) => (p.id === newParticipant.id ? newParticipant : p));
            }
            return [...prev, newParticipant];
          });
          break;
        }

        case 'participant_updated': {
          const updated: SessionParticipantPublic = msg.data;
          setParticipants((prev) =>
            prev.map((p) => (p.id === updated.id ? { ...p, ...updated } : p))
          );
          break;
        }

        case 'participant_left':
        case 'participant_removed': {
          const { participant_id } = msg.data;
          setParticipants((prev) => prev.filter((p) => p.id !== participant_id));
          if (participant_id === currentParticipantId) {
            alert('You have been removed from this meeting session.');
            onExit();
          }
          break;
        }

        case 'settings_updated': {
          setSession((prev) => ({
            ...prev,
            ...msg.data,
          }));
          break;
        }

        case 'optimization_started': {
          setIsCalculating(true);
          setErrorMessage(null);
          break;
        }

        case 'optimization_completed': {
          setIsCalculating(false);
          const optResult = msg.data.result;
          setResult(optResult);
          setSession((prev) => ({ ...prev, result_is_stale: false }));
          setStaleReason(null);

          // Reveal all routes
          if (optResult?.individual_distances) {
            const ids = new Set<string>(
              optResult.individual_distances.map(
                (r: { participant_id: string }) => r.participant_id
              )
            );
            setVisibleRouteIds(ids);
          }
          break;
        }

        case 'optimization_failed': {
          setIsCalculating(false);
          setErrorMessage(msg.data.error || 'Optimization calculation failed.');
          break;
        }

        case 'result_stale': {
          setSession((prev) => ({ ...prev, result_is_stale: true }));
          if (msg.data.reason) {
            setStaleReason(msg.data.reason);
          }
          break;
        }

        case 'session_closed': {
          alert('The host has closed this meeting session.');
          onExit();
          break;
        }

        default:
          break;
      }
    },
    [currentParticipantId, onExit]
  );

  // Hook into WebSocket
  const { status: wsStatus } = useSessionWebSocket({
    sessionId: session.session_id,
    token,
    onMessage: handleWebSocketMessage,
  });

  // Current participant object
  const currentParticipant = useMemo(
    () => participants.find((p) => p.id === currentParticipantId) || null,
    [participants, currentParticipantId]
  );

  // Transform participants with coordinates for MapView
  const mapParticipants = useMemo<Participant[]>(() => {
    return participants
      .filter((p) => p.location_submitted && p.latitude !== null && p.longitude !== null)
      .map((p, idx) => ({
        id: p.id,
        name: p.display_name,
        latitude: p.latitude as number,
        longitude: p.longitude as number,
        color: getParticipantColor(idx),
      }));
  }, [participants]);

  // Host Action: Trigger Optimization
  const handleOptimize = async () => {
    setIsCalculating(true);
    setErrorMessage(null);
    try {
      await triggerOptimization(session.session_id, token);
    } catch (err: any) {
      setIsCalculating(false);
      setErrorMessage(err?.message || 'Failed to trigger optimization.');
    }
  };

  // Host Action: Close Session
  const handleCloseSession = async () => {
    try {
      await closeSession(session.session_id, token);
      onExit();
    } catch (err: any) {
      alert(err?.message || 'Failed to close session.');
    }
  };

  // Host Action: Remove Participant
  const handleRemoveParticipant = async (participantId: string) => {
    try {
      await removeParticipant(session.session_id, token, participantId);
    } catch (err: any) {
      alert(err?.message || 'Failed to remove participant.');
    }
  };

  // Participant Action: Submit GPS
  const handleSubmitGps = () => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser.');
      return;
    }

    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const lat = Number(pos.coords.latitude.toFixed(6));
          const lon = Number(pos.coords.longitude.toFixed(6));
          await submitLocation(session.session_id, token, lat, lon);
        } catch (err: any) {
          alert(err?.message || 'Failed to submit GPS location.');
        } finally {
          setIsLocating(false);
        }
      },
      (err) => {
        setIsLocating(false);
        alert(`Could not get GPS position: ${err.message}`);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  // Participant Action: Pick on Map
  const handleMapClick = async (lat: number, lon: number) => {
    if (!isMapPicking) return;
    try {
      await submitLocation(
        session.session_id,
        token,
        Number(lat.toFixed(6)),
        Number(lon.toFixed(6))
      );
      setIsMapPicking(false);
    } catch (err: any) {
      alert(err?.message || 'Failed to update location on map.');
    }
  };

  // Participant Action: Withdraw Location
  const handleWithdrawLocation = async () => {
    try {
      await withdrawLocation(session.session_id, token);
    } catch (err: any) {
      alert(err?.message || 'Failed to withdraw location.');
    }
  };

  // Participant Action: Leave Session
  const handleLeaveSession = async () => {
    try {
      await leaveSession(session.session_id, token);
    } catch {
      // ignore
    } finally {
      onExit();
    }
  };

  // Route visibility toggling
  const handleToggleRoute = (participantId: string) => {
    setVisibleRouteIds((prev) => {
      const next = new Set(prev);
      if (next.has(participantId)) {
        next.delete(participantId);
      } else {
        next.add(participantId);
      }
      return next;
    });
  };

  const readyParticipantCount = participants.filter((p) => p.location_submitted).length;

  return (
    <div className="h-screen w-screen flex flex-col bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Top Session Header */}
      <SessionHeader
        session={session}
        userRole={userRole}
        currentParticipantName={currentParticipant?.display_name}
        wsStatus={wsStatus}
        onOpenSettings={() => setShowSettingsModal(true)}
        onLeave={userRole === 'HOST' ? onExit : handleLeaveSession}
      />

      {/* Main Collaborative Content Area */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Control & Presence Sidebar */}
        <aside className="w-96 min-w-[340px] max-w-[420px] bg-slate-900 border-r border-slate-800 flex flex-col h-full z-10 shadow-xl overflow-y-auto p-4 gap-4">
          {/* Stale Result Banner */}
          {session.result_is_stale && result && (
            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex flex-col gap-2">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold">Results are out of date</span>
                  <p className="text-[11px] text-amber-400/90 mt-0.5">
                    {staleReason || 'A participant updated or withdrew their coordinates.'}
                  </p>
                </div>
              </div>
              {userRole === 'HOST' && (
                <button
                  onClick={handleOptimize}
                  disabled={isCalculating || readyParticipantCount < 2}
                  className="w-full py-1.5 px-3 rounded-lg font-bold bg-amber-500 hover:bg-amber-400 text-slate-950 transition flex items-center justify-center gap-1.5 text-xs disabled:opacity-50"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Recalculate Meeting Point</span>
                </button>
              )}
            </div>
          )}

          {/* Error Message Banner */}
          {errorMessage && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
              {errorMessage}
            </div>
          )}

          {/* Role-Specific Actions */}
          {userRole === 'HOST' ? (
            <HostControls
              session={session}
              readyParticipantCount={readyParticipantCount}
              isCalculating={isCalculating}
              hasCalculated={!!result}
              onOptimize={handleOptimize}
              onOpenSettings={() => setShowSettingsModal(true)}
              onCloseSession={handleCloseSession}
            />
          ) : (
            <ParticipantControls
              currentParticipant={currentParticipant}
              isMapPicking={isMapPicking}
              onToggleMapPicking={() => setIsMapPicking(!isMapPicking)}
              onSubmitGps={handleSubmitGps}
              onWithdrawLocation={handleWithdrawLocation}
              onLeave={handleLeaveSession}
              isLocating={isLocating}
            />
          )}

          {/* Participant Presence & Status List */}
          <SessionParticipantList
            participants={participants}
            userRole={userRole}
            currentParticipantId={currentParticipantId}
            onRemoveParticipant={userRole === 'HOST' ? handleRemoveParticipant : undefined}
          />

          {/* Optimization Results Panel */}
          {result && (
            <div className="border-t border-slate-800 pt-4">
              <ResultsPanel
                result={result}
                participants={mapParticipants}
                selectedCandidateNodeId={selectedCandidateNodeId}
                onSelectCandidate={(c) => setSelectedCandidateNodeId(c.node_id)}
                visibleRouteIds={visibleRouteIds}
                onToggleRouteVisibility={handleToggleRoute}
                compareActiveView={compareActiveView}
                onSwitchCompareView={setCompareActiveView}
              />
            </div>
          )}
        </aside>

        {/* Right Map Canvas */}
        <main className="flex-1 h-full relative">
          <MapView
            participants={mapParticipants}
            onParticipantMove={() => {}}
            onParticipantDelete={() => {}}
            onMapClickAdd={handleMapClick}
            clickToAddEnabled={isMapPicking}
            result={result}
            selectedCandidateNodeId={selectedCandidateNodeId}
            onSelectCandidate={(c) => setSelectedCandidateNodeId(c.node_id)}
            visibleRouteIds={visibleRouteIds}
          />

          {/* Map Overlay Badge if picking coordinates */}
          {isMapPicking && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] bg-amber-500 text-slate-950 font-bold px-4 py-2 rounded-full shadow-2xl flex items-center gap-2 text-xs animate-bounce">
              <MapPin className="w-4 h-4" />
              <span>Click on the map to set your location coordinates</span>
            </div>
          )}
        </main>
      </div>

      {/* Settings Modal (Host Only) */}
      {showSettingsModal && (
        <SessionSettingsModal
          session={session}
          hostToken={token}
          onClose={() => setShowSettingsModal(false)}
          onSuccess={(updated) => {
            setSession(updated);
            setShowSettingsModal(false);
          }}
        />
      )}
    </div>
  );
};
