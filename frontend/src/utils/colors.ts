import L from 'leaflet';

export const PARTICIPANT_PALETTE = [
  '#2563eb', // Blue
  '#059669', // Emerald
  '#d97706', // Amber
  '#7c3aed', // Violet
  '#e11d48', // Rose
  '#0891b2', // Cyan
  '#ea580c', // Orange
  '#c026d3', // Fuchsia
  '#4b5563', // Slate
];

export function getParticipantColor(index: number): string {
  return PARTICIPANT_PALETTE[index % PARTICIPANT_PALETTE.length];
}

/**
 * Creates a modern Leaflet DivIcon for participant markers.
 */
export function createParticipantIcon(color: string, label: string) {
  const initial = label ? label.charAt(0).toUpperCase() : 'P';
  return L.divIcon({
    className: 'custom-participant-marker',
    html: `
      <div style="
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        background-color: ${color};
        color: white;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 13px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.25), 0 0 0 2px white;
        cursor: grab;
        transition: transform 0.15s ease;
      ">
        ${initial}
        <div style="
          position: absolute;
          bottom: -5px;
          left: 50%;
          transform: translateX(-50%);
          width: 0;
          height: 0;
          border-left: 5px solid transparent;
          border-right: 5px solid transparent;
          border-top: 6px solid ${color};
        "></div>
      </div>
    `,
    iconSize: [32, 38],
    iconAnchor: [16, 38],
    popupAnchor: [0, -38],
  });
}

/**
 * Creates a beacon DivIcon for the recommended optimal meeting point.
 */
export function createMeetingPointIcon() {
  return L.divIcon({
    className: 'custom-meeting-marker',
    html: `
      <div style="
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, #4f46e5 0%, #312e81 100%);
        color: #fef08a;
        border-radius: 9999px;
        box-shadow: 0 6px 16px rgba(79, 70, 229, 0.45), 0 0 0 3px #ffffff, 0 0 0 5px rgba(79, 70, 229, 0.3);
        animation: pulse-ring 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        cursor: pointer;
      ">
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="currentColor" stroke="none">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
        </svg>
        <div style="
          position: absolute;
          bottom: -7px;
          left: 50%;
          transform: translateX(-50%);
          width: 0;
          height: 0;
          border-left: 6px solid transparent;
          border-right: 6px solid transparent;
          border-top: 8px solid #312e81;
        "></div>
      </div>
    `,
    iconSize: [40, 48],
    iconAnchor: [20, 48],
    popupAnchor: [0, -48],
  });
}

/**
 * Creates a badge DivIcon for alternative candidate locations (Rank 2..K).
 */
export function createCandidateIcon(rank: number, isSelected: boolean = false) {
  const bg = isSelected ? '#1e1b4b' : '#64748b';
  const border = isSelected ? '#a5b4fc' : '#ffffff';
  const size = isSelected ? 30 : 26;
  return L.divIcon({
    className: 'custom-candidate-marker',
    html: `
      <div style="
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        width: ${size}px;
        height: ${size}px;
        background-color: ${bg};
        color: white;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 11px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2), 0 0 0 2px ${border};
        cursor: pointer;
      ">
        #${rank}
      </div>
    `,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}
