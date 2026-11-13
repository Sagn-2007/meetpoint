import React, { useState } from 'react';
import { X, Sparkles, Footprints, Car, AlertCircle, Loader2 } from 'lucide-react';
import { NetworkType, OptimizationObjective } from '../../types';
import { CreateSessionResponse } from '../../types/session';
import { createSession } from '../../services/sessionApi';

interface CreateMeetingModalProps {
  onClose: () => void;
  onSuccess: (session: CreateSessionResponse) => void;
}

export const CreateMeetingModal: React.FC<CreateMeetingModalProps> = ({ onClose, onSuccess }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [networkType, setNetworkType] = useState<NetworkType>('walk');
  const [objective, setObjective] = useState<OptimizationObjective>('median');
  const [topK, setTopK] = useState<number>(5);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Please provide a meeting title.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await createSession({
        title: title.trim(),
        description: description.trim() || undefined,
        network_type: networkType,
        optimization_objective: objective,
        top_k: topK,
      });
      onSuccess(response);
    } catch (err: any) {
      setError(err?.message || 'Failed to create meeting session.');
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
            <div className="p-1.5 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-bold text-white">Create Meeting Session</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5 overflow-y-auto flex-1">
          {error && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-start gap-2">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Title */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Meeting Title *
            </label>
            <input
              type="text"
              required
              placeholder="e.g., Team Coffee Sync, Project Retrospective"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Description (Optional)
            </label>
            <textarea
              rows={2}
              placeholder="Add details, agenda, or notes for participants..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Network Type */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
              Traversable Road Network
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setNetworkType('walk')}
                className={`flex items-center gap-2.5 p-3 rounded-xl border text-left transition ${
                  networkType === 'walk'
                    ? 'bg-blue-600/10 border-blue-500 text-blue-400'
                    : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:border-slate-600'
                }`}
              >
                <Footprints className="w-5 h-5 shrink-0" />
                <div>
                  <div className="text-sm font-semibold text-white">Pedestrian (Walk)</div>
                  <div className="text-xs text-slate-400">Default OSM walking network</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setNetworkType('drive')}
                className={`flex items-center gap-2.5 p-3 rounded-xl border text-left transition ${
                  networkType === 'drive'
                    ? 'bg-blue-600/10 border-blue-500 text-blue-400'
                    : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:border-slate-600'
                }`}
              >
                <Car className="w-5 h-5 shrink-0" />
                <div>
                  <div className="text-sm font-semibold text-white">Vehicular (Drive)</div>
                  <div className="text-xs text-slate-400">Drivable roads & one-ways</div>
                </div>
              </button>
            </div>
          </div>

          {/* Optimization Objective */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
              Optimization Objective
            </label>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setObjective('median')}
                className={`p-2.5 rounded-xl border text-center transition ${
                  objective === 'median'
                    ? 'bg-blue-600/10 border-blue-500 text-blue-400'
                    : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:border-slate-600'
                }`}
              >
                <div className="text-xs font-bold text-white">1-Median</div>
                <div className="text-[10px] text-slate-400 mt-0.5">Min total walk</div>
              </button>

              <button
                type="button"
                onClick={() => setObjective('center')}
                className={`p-2.5 rounded-xl border text-center transition ${
                  objective === 'center'
                    ? 'bg-blue-600/10 border-blue-500 text-blue-400'
                    : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:border-slate-600'
                }`}
              >
                <div className="text-xs font-bold text-white">1-Center</div>
                <div className="text-[10px] text-slate-400 mt-0.5">Min max walk</div>
              </button>

              <button
                type="button"
                onClick={() => setObjective('compare')}
                className={`p-2.5 rounded-xl border text-center transition ${
                  objective === 'compare'
                    ? 'bg-blue-600/10 border-blue-500 text-blue-400'
                    : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:border-slate-600'
                }`}
              >
                <div className="text-xs font-bold text-white">Compare</div>
                <div className="text-[10px] text-slate-400 mt-0.5">Both side-by-side</div>
              </button>
            </div>
          </div>

          {/* Top K */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Alternative Recommendations (Top K)
              </label>
              <span className="text-xs font-mono font-bold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">
                {topK}
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={15}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
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
              disabled={isSubmitting}
              className="px-5 py-2.5 rounded-xl text-sm font-semibold bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/30 transition flex items-center gap-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Creating Session...</span>
                </>
              ) : (
                <span>Create & Enter Room</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
