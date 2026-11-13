import React, { useState, useEffect, useCallback } from 'react';
import {
  CandidateRecommendation,
  NetworkType,
  OptimizationObjective,
  OptimizeMeetingRequest,
  OptimizeMeetingResponse,
  Participant,
} from './types';
import { checkBackendHealth, optimizeMeeting, ApiError } from './services/api';
import { getParticipantColor } from './utils/colors';
import { Navbar } from './components/layout/Navbar';
import { MapView } from './components/map/MapView';
import { ParticipantList } from './components/participants/ParticipantList';
import { OptimizationControls } from './components/optimization/OptimizationControls';
import { ResultsPanel } from './components/results/ResultsPanel';

// Preset sample names
const SAMPLE_NAMES = ['Alice', 'Bob', 'Charlie', 'Diana', 'Evan', 'Fiona', 'George'];

// Preset sample demo coordinates (Central London / Covent Garden & Westminster)
const PRESET_PARTICIPANTS = [
  { name: 'Alice', latitude: 51.5075, longitude: -0.1275 },
  { name: 'Bob', latitude: 51.5085, longitude: -0.1265 },
  { name: 'Charlie', latitude: 51.5068, longitude: -0.1272 },
];

export const App: React.FC = () => {
  // Application State
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [networkType, setNetworkType] = useState<NetworkType>('walk');
  const [objective, setObjective] = useState<OptimizationObjective>('median');
  const [topK, setTopK] = useState<number>(5);
  const [clickToAddEnabled, setClickToAddEnabled] = useState<boolean>(true);

  // Results & Calculation State
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

  // Check health on mount
  useEffect(() => {
    checkBackendHealth()
      .then((res) => {
        setBackendStatus(res.status === 'healthy' ? 'healthy' : 'unhealthy');
      })
      .catch(() => {
        setBackendStatus('offline');
      });
  }, []);

  // Add a participant from map click
  const handleMapClickAdd = useCallback(
    (lat: number, lon: number) => {
      const idx = participants.length;
      const autoName =
        idx < SAMPLE_NAMES.length ? SAMPLE_NAMES[idx] : `Participant ${idx + 1}`;
      const newParticipant: Participant = {
        id: `p_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
        name: autoName,
        latitude: lat,
        longitude: lon,
        color: getParticipantColor(idx),
      };

      setParticipants((prev) => [...prev, newParticipant]);
      setResult(null); // Reset stale result
      setErrorMessage(null);
    },
    [participants.length]
  );

  // Manual Add
  const handleAddParticipant = (name: string, lat: number, lon: number) => {
    const idx = participants.length;
    const newParticipant: Participant = {
      id: `p_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
      name: name || `Participant ${idx + 1}`,
      latitude: lat,
      longitude: lon,
      color: getParticipantColor(idx),
    };

    setParticipants((prev) => [...prev, newParticipant]);
    setResult(null);
    setErrorMessage(null);
  };

  // Move participant marker (drag & drop)
  const handleParticipantMove = (id: string, lat: number, lon: number) => {
    setParticipants((prev) =>
      prev.map((p) => (p.id === id ? { ...p, latitude: lat, longitude: lon } : p))
    );
    setResult(null);
    setErrorMessage(null);
  };

  // Update participant details
  const handleUpdateParticipant = (id: string, name: string, lat: number, lon: number) => {
    setParticipants((prev) =>
      prev.map((p) =>
        p.id === id ? { ...p, name, latitude: lat, longitude: lon } : p
      )
    );
    setResult(null);
  };

  // Remove participant
  const handleRemoveParticipant = (id: string) => {
    setParticipants((prev) => {
      const updated = prev.filter((p) => p.id !== id);
      return updated.map((p, idx) => ({ ...p, color: getParticipantColor(idx) }));
    });
    setResult(null);
  };

  // Clear all
  const handleClearAll = () => {
    setParticipants([]);
    setResult(null);
    setErrorMessage(null);
    setSelectedCandidateNodeId(null);
  };

  // Load sample demo participants
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

  // Toggle individual route visibility on map
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

  // Select alternative candidate
  const handleSelectCandidate = (candidate: CandidateRecommendation) => {
    setSelectedCandidateNodeId(candidate.node_id);
  };

  // Run calculation
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

      // Make all participant routes visible by default
      const allIds = new Set(response.individual_distances.map((d) => d.participant_id));
      setVisibleRouteIds(allIds);
      setClickToAddEnabled(false); // disable click-to-add so map clicking interacts with routes
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

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-100">
      {/* 1. Top Navbar */}
      <Navbar
        backendStatus={backendStatus}
        onLoadSample={handleLoadSample}
        onReset={handleClearAll}
        participantCount={participants.length}
      />

      {/* 2. Main Workspace */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden relative">
        {/* Left Control & Results Sidebar */}
        <div className="w-full md:w-[420px] lg:w-[460px] flex-shrink-0 bg-white border-r border-slate-200 shadow-sm flex flex-col z-20 h-1/2 md:h-full">
          <div className="p-4 overflow-y-auto space-y-4 flex-1">
            {/* Participants Management */}
            <ParticipantList
              participants={participants}
              onAddParticipant={handleAddParticipant}
              onUpdateParticipant={handleUpdateParticipant}
              onRemoveParticipant={handleRemoveParticipant}
              onClearAll={handleClearAll}
              clickToAddEnabled={clickToAddEnabled}
              onToggleClickToAdd={() => setClickToAddEnabled(!clickToAddEnabled)}
            />

            {/* Optimization Controls */}
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

            {/* Results Section */}
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

        {/* Right Interactive Map (65-70%) */}
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
  );
};
export default App;
