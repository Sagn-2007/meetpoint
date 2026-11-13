import React, { useState } from 'react';
import {
  Users,
  Compass,
  PlusCircle,
  LogIn,
  ShieldCheck,
  Footprints,
  Sparkles,
} from 'lucide-react';
import { CreateMeetingModal } from './CreateMeetingModal';
import { JoinMeetingModal } from './JoinMeetingModal';
import { CreateSessionResponse, JoinSessionResponse } from '../../types/session';

interface LandingPageProps {
  onSessionCreated: (session: CreateSessionResponse) => void;
  onSessionJoined: (joinData: JoinSessionResponse) => void;
  onLaunchSoloDemo: () => void;
  initialCode?: string;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onSessionCreated,
  onSessionJoined,
  onLaunchSoloDemo,
  initialCode,
}) => {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showJoinModal, setShowJoinModal] = useState(!!initialCode);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      {/* Top Bar */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Compass className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-white tracking-tight">MeetPoint</span>
              <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                v0.4.0 Collaborative
              </span>
            </div>
            <p className="text-xs text-slate-400">Network-Optimized Meeting Point Engine</p>
          </div>
        </div>

        <button
          onClick={onLaunchSoloDemo}
          className="text-xs font-medium text-slate-300 hover:text-white px-3 py-1.5 rounded-lg border border-slate-700 hover:bg-slate-800 transition"
        >
          Solo Demo Sandbox &rarr;
        </button>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-5xl mx-auto px-6 py-16 flex flex-col justify-center items-center text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-medium mb-6">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Phase 4: Real-Time Multi-User Collaboration</span>
        </div>

        <h1 className="text-4xl md:text-5xl font-extrabold text-white tracking-tight mb-4 max-w-3xl">
          Find the optimal meeting point for your group on real road networks.
        </h1>
        <p className="text-slate-400 text-base md:text-lg max-w-2xl mb-10 leading-relaxed">
          Create a collaborative room, share an invitation link, and let each participant
          independently submit their location. MeetPoint calculates the mathematically optimal
          meeting location using actual traversable pedestrian paths.
        </p>

        {/* Action Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-2xl mb-12">
          {/* Create Room Card */}
          <div className="bg-slate-800/80 border border-slate-700 hover:border-blue-500/50 rounded-2xl p-6 text-left shadow-xl transition-all flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center mb-4 border border-blue-500/20">
                <PlusCircle className="w-6 h-6" />
              </div>
              <h2 className="text-lg font-bold text-white mb-1">Create Meeting Session</h2>
              <p className="text-sm text-slate-400 mb-6">
                Host a new room, set optimization parameters, and receive a shareable invitation
                code with a secure host token.
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="w-full py-3 px-4 rounded-xl font-semibold bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/30 transition flex items-center justify-center gap-2"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Create New Meeting</span>
            </button>
          </div>

          {/* Join Room Card */}
          <div className="bg-slate-800/80 border border-slate-700 hover:border-emerald-500/50 rounded-2xl p-6 text-left shadow-xl transition-all flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center mb-4 border border-emerald-500/20">
                <LogIn className="w-6 h-6" />
              </div>
              <h2 className="text-lg font-bold text-white mb-1">Join with Invitation Code</h2>
              <p className="text-sm text-slate-400 mb-6">
                Have an 8-character invitation code? Enter the session room, submit your location,
                and view the calculated results.
              </p>
            </div>
            <button
              onClick={() => setShowJoinModal(true)}
              className="w-full py-3 px-4 rounded-xl font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/30 transition flex items-center justify-center gap-2"
            >
              <LogIn className="w-4 h-4" />
              <span>Join Meeting</span>
            </button>
          </div>
        </div>

        {/* Feature Highlights */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 w-full max-w-4xl text-left border-t border-slate-800 pt-10">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-slate-800 text-blue-400 border border-slate-700">
              <Footprints className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Pedestrian Road Networks</h3>
              <p className="text-xs text-slate-400 mt-1">
                Shortest traversable paths along OpenStreetMap walking routes with Dijkstra routing.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-slate-800 text-purple-400 border border-slate-700">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Real-Time Sync</h3>
              <p className="text-xs text-slate-400 mt-1">
                WebSockets broadcast presence, participant locations, and live meeting results instantly.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-slate-800 text-emerald-400 border border-slate-700">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Privacy First</h3>
              <p className="text-xs text-slate-400 mt-1">
                Explicit coordinate sharing only. No background GPS tracking, no accounts required.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Modals */}
      {showCreateModal && (
        <CreateMeetingModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={(session) => {
            setShowCreateModal(false);
            onSessionCreated(session);
          }}
        />
      )}

      {showJoinModal && (
        <JoinMeetingModal
          initialCode={initialCode}
          onClose={() => setShowJoinModal(false)}
          onSuccess={(joinData) => {
            setShowJoinModal(false);
            onSessionJoined(joinData);
          }}
        />
      )}
    </div>
  );
};
