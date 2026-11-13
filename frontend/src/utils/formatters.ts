import { Coordinate } from '../types';

/**
 * Formats a distance in metres to human-readable string (m or km).
 */
export function formatDistance(metres: number | undefined | null): string {
  if (metres === undefined || metres === null || isNaN(metres)) {
    return '0 m';
  }
  if (metres < 1000) {
    return `${Math.round(metres)} m`;
  }
  return `${(metres / 1000).toFixed(2)} km`;
}

/**
 * Formats coordinates for display with fixed decimal places.
 */
export function formatCoordinate(coord: Coordinate | { latitude: number; longitude: number }): string {
  return `${coord.latitude.toFixed(5)}, ${coord.longitude.toFixed(5)}`;
}

/**
 * Formats millisecond duration for performance metrics.
 */
export function formatMs(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)} ms`;
  }
  return `${(ms / 1000).toFixed(2)} s`;
}

/**
 * Estimates nominal travel duration for user context (e.g., ~5 km/h walk, ~30 km/h city drive).
 */
export function estimateDuration(metres: number, networkType: string = 'walk'): string {
  if (!metres || metres <= 0) return '0 min';
  // 5 km/h for walking = ~83.3 m/min
  // 30 km/h for driving = ~500 m/min
  const speedMetersPerMin = networkType === 'walk' ? 83.3 : 500;
  const mins = Math.max(1, Math.round(metres / speedMetersPerMin));
  if (mins < 60) {
    return `~${mins} min`;
  }
  const hours = Math.floor(mins / 60);
  const remainingMins = mins % 60;
  return `~${hours}h ${remainingMins}m`;
}
