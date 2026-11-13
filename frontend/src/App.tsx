import React, { useState, useEffect, useCallback } from 'react';
import {
  CandidateRecommendation,
  NetworkType,
  OptimizationObjective,
  OptimizeMeetingRequest,
  OptimizeMeetingResponse,
  Participant,
} from './types';
import {
  CreateSessionResponse,
  JoinSessionResponse,
  MeetingSessionPublic,
  UserRole,
} from './types/session';
import { checkBackendHealth, optimizeMeeting, ApiError } from './services/api';
import { getParticipantColor } from './utils/colors';
import { Navbar } from './components/layout/Navbar';
import { MapView } from './components/map/MapView';
import { ParticipantList } from './components/participants/ParticipantList';
import { OptimizationControls } from './components/optimization/OptimizationControls';
import { ResultsPanel } from './components/results/ResultsPanel';
import { LandingPage } from './components/collaborative/LandingPage';
import { CollaborativeRoom } from './components/collaborative/CollaborativeRoom';
import { ErrorBoundary } from './components/ui/ErrorBoundary';

// Preset sample names
const SAMPLE_NAMES = ['Alice', 'Bob', 'Charlie', 'Diana', 'Evan', 'Fiona', 'George'];

// Preset sample demo coordinates (Central London / Covent Garden & Westminster)
const PRESET_PARTICIPANTS = [
  { name: 'Alice', latitude: 51.5075, longitude: -0.1275 },
  { name: 'Bob', latitude: 51.5085, longitude: -0.1265 },
  { name: 'Charlie', latitude: 51.5068, longitude: -0.1272 },
];

export const App: React.FC = () => {
  // Navigation / View state: 'landing' | 'room' | 'sandbox'
  const [currentView, setCurrentView] = useState<'landing' | 'room' | 'sandbox'>('landing');

  // URL invitation code detection
  const [urlInvitationCode, setUrlInvitationCode] = useState<string | undefined>(undefined);

  // Active Collaborative Session state
  const [activeSession, setActiveSession] = useState<MeetingSessionPublic | null>(null);
  const [userRole, setUserRole] = useState<UserRole>('VIEWER');
  const [sessionToken, setSessionToken] = useState<string>('');
  const [currentParticipantId, setCurrentParticipantId] = useState<string | null>(null);

  // Single-User Sandbox State (Phase 3)
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [networkType, setNetworkType] = useState<NetworkType>('walk');
  const [objective, setObjective] = useState<OptimizationObjective>('median');
  const [topK, setTopK] = useState<number>(5);
  const [clickToAddEnabled, setClickToAddEnabled] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<OptimizeMeetingResponse | null>(null);
  const [selectedCandidateNodeId, setSelectedCandidateNodeId] = useState<number | string | null>(
    null
  );
  const [visibleRouteIds, setVisibleRouteIds] = useState<Set<string>>(new Set());
  const [compareActiveView, setCompareActiveView] = useState<'median' | 'center'>('median');

  // Backend Health State
  const [backendStatus, setBackendStatus] = useState<
    'healthy' | 'unhealthy' | 'offline' | 'checking'
  >('checking');

  // Check health and parse URL on mount
  useEffect(() => {
    checkBackendHealth()
      .then((res) => {
        setBackendStatus(res.status === 'healthy' ? 'healthy' : 'unhealthy');
      })
      .catch(() => {
        setBackendStatus('offline');
      });

    // Check for hash or query param: #/join/CODE, #join=CODE, ?code=CODE
    const hash = window.location.hash;
    const searchParams = new URLSearchParams(window.location.search);
    let detectedCode: string | null = null;

    if (hash.includes('/join/')) {
      const parts = hash.split('/join/');
      if (parts[1]) detectedCode = parts[1].replace(/[^a-zA-Z0-9]/g, '');
    } else if (hash.includes('join=')) {
      const parts = hash.split('join=');
      if (parts[1]) detectedCode = parts[1].replace(/[^a-zA-Z0-9]/g, '');
    } else if (searchParams.get('code')) {
      detectedCode = searchParams.get('code');
    }

    if (detectedCode && detectedCode.length === 8) {
      setUrlInvitationCode(detectedCode.toUpperCase());
      setCurrentView('landing');
    }
  }, []);

  // Collaborative Handlers
  const handleSessionCreated = (created: CreateSessionResponse) => {
    const sessionPublic: MeetingSessionPublic = {
      session_id: created.session_id,
      invitation_code: created.invitation_code,
      title: created.title,
      description: created.description,
      status: 'active',
      network_type: created.network_type,
      optimization_objective: created.optimization_objective,
      top_k: created.top_k,
      result_is_stale: false,
      expires_at: created.expires_at,
      created_at: created.created_at,
      participants_count: 0,
      is_expired: false,
    };
    setActiveSession(sessionPublic);
    setUserRole('HOST');
    setSessionToken(created.host_token);
    setCurrentParticipantId(null);
    setCurrentView('room');
  };

  const handleSessionJoined = (joinData: JoinSessionResponse) => {
    const sessionPublic: MeetingSessionPublic = {
      session_id: joinData.session_id,
      invitation_code: urlInvitationCode || '',
      title: 'Meeting Session',
      description: null,
      status: 'active',
      network_type: 'walk',
      optimization_objective: 'median',
      top_k: 5,
      result_is_stale: false,
      expires_at: new Date(Date.now() + 86400000).toISOString(),
      created_at: new Date().toISOString(),
      participants_count: 1,
      is_expired: false,
    };
    setActiveSession(sessionPublic);
    setUserRole('PARTICIPANT');
    setSessionToken(joinData.participant_token);
    setCurrentParticipantId(joinData.participant_id);
    setCurrentView('room');
  };

  const handleExitRoom = () => {
    setActiveSession(null);
    setUserRole('VIEWER');
    setSessionToken('');
    setCurrentParticipantId(null);
    setCurrentView('landing');
    window.location.hash = '';
  };

  // Sandbox Handlers (Phase 3)
  const handleAddParticipant = useCallback(
    (name: string, lat: number, lon: number) => {
      const newParticipant: Participant = {
        id: `p_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
        name: name.trim() || `Person ${participants.length + 1}`,
        latitude: lat,
        longitude: lon,
        color: getParticipantColor(participants.length),
      };
      setParticipants((prev) => [...prev, newParticipant]);
      setResult(null);
      setErrorMessage(null);
    },
    [participants.length]
  );

  const handleMapClickAdd = useCallback(
    (lat: number, lon: number) => {
      const defaultName = SAMPLE_NAMES[participants.length % SAMPLE_NAMES.length];
      handleAddParticipant(defaultName, Number(lat.toFixed(6)), Number(lon.toFixed(6)));
    },
    [handleAddParticipant, participants.length]
  );

  const handleParticipantMove = (id: string, lat: number, lon: number) => {
    setParticipants((prev) =>
      prev.map((p) => (p.id === id ? { ...p, latitude: lat, longitude: lon } : p))
    );
    setResult(null);
    setErrorMessage(null);
  };

  const handleUpdateParticipant = (id: string, name: string, lat: number, lon: number) => {
    setParticipants((prev) =>
      prev.map((p) => (p.id === id ? { ...p, name, latitude: lat, longitude: lon } : p))
    );
    setResult(null);
  };

  const handleRemoveParticipant = (id: string) => {
    setParticipants((prev) => {
      const updated = prev.filter((p) => p.id !== id);
      return updated.map((p, idx) => ({ ...p, color: getParticipantColor(idx) }));
    });
    setResult(null);
  };

  const handleClearAll = () => {
    setParticipants([]);
    setResult(null);
    setErrorMessage(null);
    setSelectedCandidateNodeId(null);
  };

  const handleLoadSample = () => {
    const sample = PRESET_PARTICIPANTS.map((preset, idx) => ({
      id: `sample_${idx + 1}`,
      name: preset.name,
      latitude: preset.latitude,
      longitude: preset.longitude,
      color: getParticipantColor(idx),
    }));
    setParticipants(sample);
    setResult(null);
    setErrorMessage(null);
  };

  const handleToggleRouteVisibility = (participantId: string) => {
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

  const handleSelectCandidate = (candidate: CandidateRecommendation) => {
    setSelectedCandidateNodeId(candidate.node_id);
  };

  const handleCalculate = async () => {
    if (participants.length < 2) return;

    setIsLoading(true);
    setErrorMessage(null);

    const payload: OptimizeMeetingRequest = {
      participants: participants.map((p) => ({
        id: p.id,
        latitude: p.latitude,
        longitude: p.longitude,
        label: p.name,
      })),
      network_type: networkType,
      objective: objective,
      top_k: topK,
    };

    try {
      const response = await optimizeMeeting(payload);
      setResult(response);
      setSelectedCandidateNodeId(response.optimal_node_id);

      const allIds = new Set(response.individual_distances.map((d) => d.participant_id));
      setVisibleRouteIds(allIds);
      setClickToAddEnabled(false);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('An unexpected error occurred while calculating the meeting point.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Render Views
  if (currentView === 'landing') {
    return (
      <ErrorBoundary fallbackTitle="MeetPoint Landing Error">
        <LandingPage
          initialCode={urlInvitationCode}
          onSessionCreated={handleSessionCreated}
          onSessionJoined={handleSessionJoined}
          onLaunchSoloDemo={() => setCurrentView('sandbox')}
        />
      </ErrorBoundary>
    );
  }

  if (currentView === 'room' && activeSession) {
    return (
      <ErrorBoundary fallbackTitle="Collaborative Room Error">
        <CollaborativeRoom
          initialSession={activeSession}
          userRole={userRole}
          token={sessionToken}
          currentParticipantId={currentParticipantId}
          onExit={handleExitRoom}
        />
      </ErrorBoundary>
    );
  }

  // Sandbox Mode (Phase 3)
  return (
    <ErrorBoundary fallbackTitle="Sandbox Workspace Error">
      <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-100">
        {/* 1. Top Navbar */}
        <Navbar
          backendStatus={backendStatus}
          onLoadSample={handleLoadSample}
          onReset={handleClearAll}
          participantCount={participants.length}
          onSwitchToCollaborative={() => setCurrentView('landing')}
        />

        {/* 2. Main Workspace */}
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden relative">
          {/* Left Control & Results Sidebar */}
          <div className="w-full md:w-[420px] lg:w-[460px] flex-shrink-0 bg-white border-r border-slate-200 shadow-sm flex flex-col z-20 h-1/2 md:h-full">
            <div className="p-4 overflow-y-auto space-y-4 flex-1">
              <ParticipantList
                participants={participants}
                onAddParticipant={handleAddParticipant}
                onUpdateParticipant={handleUpdateParticipant}
                onRemoveParticipant={handleRemoveParticipant}
                onClearAll={handleClearAll}
                clickToAddEnabled={clickToAddEnabled}
                onToggleClickToAdd={() => setClickToAddEnabled(!clickToAddEnabled)}
              />

              <OptimizationControls
                objective={objective}
                onObjectiveChange={setObjective}
                networkType={networkType}
                onNetworkTypeChange={setNetworkType}
                topK={topK}
                onTopKChange={setTopK}
                onCalculate={handleCalculate}
                isLoading={isLoading}
                participantCount={participants.length}
                errorMessage={errorMessage}
              />

              {result && (
                <ResultsPanel
                  result={result}
                  participants={participants}
                  selectedCandidateNodeId={selectedCandidateNodeId}
                  onSelectCandidate={handleSelectCandidate}
                  visibleRouteIds={visibleRouteIds}
                  onToggleRouteVisibility={handleToggleRouteVisibility}
                  compareActiveView={compareActiveView}
                  onSwitchCompareView={setCompareActiveView}
                />
              )}
            </div>
          </div>

          {/* Right Interactive Map */}
          <div className="flex-1 h-1/2 md:h-full relative overflow-hidden">
            <MapView
              participants={participants}
              onParticipantMove={handleParticipantMove}
              onParticipantDelete={handleRemoveParticipant}
              onMapClickAdd={handleMapClickAdd}
              clickToAddEnabled={clickToAddEnabled}
              result={result}
              selectedCandidateNodeId={selectedCandidateNodeId}
              onSelectCandidate={handleSelectCandidate}
              visibleRouteIds={visibleRouteIds}
            />
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
};

export default App;
