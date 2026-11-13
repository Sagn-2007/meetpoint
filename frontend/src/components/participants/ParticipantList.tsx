import React, { useState } from 'react';
import { Participant } from '../../types';
import { UserPlus, Trash2, MapPin, Edit2, Check, X, MousePointerClick } from 'lucide-react';
import { formatCoordinate } from '../../utils/formatters';

interface ParticipantListProps {
  participants: Participant[];
  onAddParticipant: (name: string, lat: number, lon: number) => void;
  onUpdateParticipant: (id: string, name: string, lat: number, lon: number) => void;
  onRemoveParticipant: (id: string) => void;
  onClearAll: () => void;
  clickToAddEnabled: boolean;
  onToggleClickToAdd: () => void;
}

export const ParticipantList: React.FC<ParticipantListProps> = ({
  participants,
  onAddParticipant,
  onUpdateParticipant,
  onRemoveParticipant,
  onClearAll,
  clickToAddEnabled,
  onToggleClickToAdd,
}) => {
  const [isAddingManual, setIsAddingManual] = useState(false);
  const [manualName, setManualName] = useState('');
  const [manualLat, setManualLat] = useState('');
  const [manualLon, setManualLon] = useState('');
  const [manualError, setManualError] = useState<string | null>(null);

  // Editing state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editLat, setEditLat] = useState('');
  const [editLon, setEditLon] = useState('');

  const handleStartEdit = (p: Participant) => {
    setEditingId(p.id);
    setEditName(p.name);
    setEditLat(p.latitude.toString());
    setEditLon(p.longitude.toString());
  };

  const handleSaveEdit = (id: string) => {
    const lat = parseFloat(editLat);
    const lon = parseFloat(editLon);
    if (isNaN(lat) || lat < -90 || lat > 90) return;
    if (isNaN(lon) || lon < -180 || lon > 180) return;

    onUpdateParticipant(id, editName.trim() || 'Participant', lat, lon);
    setEditingId(null);
  };

  const handleManualAddSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setManualError(null);

    const lat = parseFloat(manualLat);
    const lon = parseFloat(manualLon);

    if (isNaN(lat) || lat < -90 || lat > 90) {
      setManualError('Latitude must be a valid number between -90 and 90');
      return;
    }
    if (isNaN(lon) || lon < -180 || lon > 180) {
      setManualError('Longitude must be a valid number between -180 and 180');
      return;
    }

    const name = manualName.trim() || `Participant ${participants.length + 1}`;
    onAddParticipant(name, lat, lon);

    // Reset form
    setManualName('');
    setManualLat('');
    setManualLon('');
    setIsAddingManual(false);
  };

  return (
    <div className="space-y-3">
      {/* Header and Add Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="font-semibold text-slate-900 text-sm">Participants</span>
          <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
            {participants.length}
          </span>
        </div>

        <div className="flex items-center space-x-1.5">
          {/* Click to add toggle button */}
          <button
            onClick={onToggleClickToAdd}
            className={`inline-flex items-center space-x-1 px-2.5 py-1 text-xs font-medium rounded-lg transition-colors border ${
              clickToAddEnabled
                ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                : 'bg-white text-slate-700 hover:bg-slate-50 border-slate-200'
            }`}
            title="Click on the map to place participant pins"
          >
            <MousePointerClick className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">
              {clickToAddEnabled ? 'Clicking Map...' : 'Click to Add'}
            </span>
          </button>

          {/* Manual Add toggle button */}
          <button
            onClick={() => setIsAddingManual(!isAddingManual)}
            className="inline-flex items-center space-x-1 px-2.5 py-1 text-xs font-medium bg-white text-slate-700 hover:bg-slate-50 rounded-lg transition-colors border border-slate-200"
            title="Enter coordinates manually"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Manual</span>
          </button>

          {participants.length > 0 && (
            <button
              onClick={onClearAll}
              className="text-slate-400 hover:text-rose-500 p-1 rounded transition-colors"
              title="Clear all participants"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Manual Input Form */}
      {isAddingManual && (
        <form
          onSubmit={handleManualAddSubmit}
          className="bg-indigo-50/50 p-3 rounded-xl border border-indigo-100 space-y-2 text-xs"
        >
          <div className="font-medium text-indigo-900 flex justify-between items-center">
            <span>Add Participant Coordinates</span>
            <button
              type="button"
              onClick={() => setIsAddingManual(false)}
              className="text-slate-400 hover:text-slate-600"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <input
              type="text"
              placeholder="Name (e.g. Alice)"
              value={manualName}
              onChange={(e) => setManualName(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            <input
              type="number"
              step="any"
              placeholder="Latitude (e.g. 51.5075)"
              value={manualLat}
              onChange={(e) => setManualLat(e.target.value)}
              required
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            <input
              type="number"
              step="any"
              placeholder="Longitude (e.g. -0.1275)"
              value={manualLon}
              onChange={(e) => setManualLon(e.target.value)}
              required
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {manualError && (
            <div className="text-[11px] text-rose-600 font-medium">{manualError}</div>
          )}

          <div className="flex justify-end space-x-2 pt-1">
            <button
              type="button"
              onClick={() => setIsAddingManual(false)}
              className="px-2.5 py-1 rounded text-slate-600 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-3 py-1 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 shadow-sm"
            >
              Add
            </button>
          </div>
        </form>
      )}

      {/* Participants Scroll List */}
      <div className="space-y-1.5 max-h-[220px] overflow-y-auto pr-0.5">
        {participants.length === 0 ? (
          <div className="text-center py-6 px-4 border-2 border-dashed border-slate-200 rounded-xl text-slate-400 text-xs">
            <MapPin className="w-6 h-6 mx-auto mb-1.5 text-slate-300" />
            <p className="font-medium text-slate-600">No participants added yet</p>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Click on the map or use "Manual" above to add at least 2 locations.
            </p>
          </div>
        ) : (
          participants.map((p) => {
            const isEditing = editingId === p.id;

            return (
              <div
                key={p.id}
                className="bg-white rounded-xl p-2.5 border border-slate-200 shadow-xs flex items-center justify-between text-xs hover:border-slate-300 transition-colors"
              >
                {isEditing ? (
                  <div className="flex-1 mr-2 space-y-1.5">
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="w-full px-2 py-1 rounded border border-slate-200 text-xs font-medium"
                    />
                    <div className="grid grid-cols-2 gap-1.5">
                      <input
                        type="number"
                        step="any"
                        value={editLat}
                        onChange={(e) => setEditLat(e.target.value)}
                        className="px-2 py-0.5 rounded border border-slate-200 text-[11px]"
                      />
                      <input
                        type="number"
                        step="any"
                        value={editLon}
                        onChange={(e) => setEditLon(e.target.value)}
                        className="px-2 py-0.5 rounded border border-slate-200 text-[11px]"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center space-x-2.5 overflow-hidden mr-2">
                    <span
                      className="w-6 h-6 rounded-full flex items-center justify-center text-white font-bold text-[11px] flex-shrink-0 shadow-xs"
                      style={{ backgroundColor: p.color }}
                    >
                      {p.name.charAt(0).toUpperCase()}
                    </span>
                    <div className="truncate">
                      <div className="font-semibold text-slate-800 truncate">{p.name}</div>
                      <div className="text-[11px] font-mono text-slate-400 truncate">
                        {formatCoordinate(p)}
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex items-center space-x-1 flex-shrink-0">
                  {isEditing ? (
                    <>
                      <button
                        onClick={() => handleSaveEdit(p.id)}
                        className="p-1 rounded text-emerald-600 hover:bg-emerald-50"
                        title="Save changes"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="p-1 rounded text-slate-400 hover:bg-slate-100"
                        title="Cancel"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => handleStartEdit(p)}
                        className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                        title="Edit participant"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => onRemoveParticipant(p.id)}
                        className="p-1 rounded text-slate-400 hover:text-rose-500 hover:bg-rose-50"
                        title="Remove participant"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
