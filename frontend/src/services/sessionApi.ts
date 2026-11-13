import {
  CreateSessionRequest,
  CreateSessionResponse,
  JoinSessionRequest,
  JoinSessionResponse,
  MeetingSessionPublic,
} from '../types/session';
import { OptimizeMeetingResponse } from '../types';
import { ApiError } from './api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = `Request failed with status ${response.status}`;
    let errorDetails: Record<string, unknown> | undefined;

    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        if (typeof errorJson.detail === 'string') {
          errorMessage = errorJson.detail;
        } else if (errorJson.detail.message) {
          errorMessage = errorJson.detail.message;
          errorDetails = errorJson.detail.details;
        } else if (Array.isArray(errorJson.detail)) {
          errorMessage = errorJson.detail
            .map((err: { msg?: string }) => err.msg || 'Validation error')
            .join(', ');
        }
      }
    } catch {
      // Body not JSON
    }

    throw new ApiError(errorMessage, response.status, errorDetails);
  }

  return response.json() as Promise<T>;
}

export async function createSession(data: CreateSessionRequest): Promise<CreateSessionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<CreateSessionResponse>(response);
}

export async function getSessionByCode(invitationCode: string): Promise<MeetingSessionPublic> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${invitationCode.toUpperCase().trim()}`);
  return handleResponse<MeetingSessionPublic>(response);
}

export async function joinSession(
  invitationCode: string,
  data: JoinSessionRequest
): Promise<JoinSessionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${invitationCode.toUpperCase().trim()}/join`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<JoinSessionResponse>(response);
}

export async function submitLocation(
  sessionId: string,
  token: string,
  latitude: number,
  longitude: number
): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/location`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Session-Token': token,
    },
    body: JSON.stringify({ latitude, longitude }),
  });
  return handleResponse<any>(response);
}

export async function withdrawLocation(sessionId: string, token: string): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/location`, {
    method: 'DELETE',
    headers: { 'X-Session-Token': token },
  });
  return handleResponse<any>(response);
}

export async function triggerOptimization(
  sessionId: string,
  hostToken: string
): Promise<OptimizeMeetingResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/optimize`, {
    method: 'POST',
    headers: { 'X-Session-Token': hostToken },
  });
  return handleResponse<OptimizeMeetingResponse>(response);
}

export async function getSessionResults(
  sessionId: string,
  token?: string
): Promise<{ has_result: boolean; result_is_stale: boolean; result: OptimizeMeetingResponse | null }> {
  const headers: Record<string, string> = {};
  if (token) {
    headers['X-Session-Token'] = token;
  }
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/results`, {
    headers,
  });
  return handleResponse<{ has_result: boolean; result_is_stale: boolean; result: OptimizeMeetingResponse | null }>(
    response
  );
}

export async function updateSessionSettings(
  sessionId: string,
  hostToken: string,
  settings: Partial<CreateSessionRequest>
): Promise<MeetingSessionPublic> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/settings`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'X-Session-Token': hostToken,
    },
    body: JSON.stringify(settings),
  });
  return handleResponse<MeetingSessionPublic>(response);
}

export async function removeParticipant(
  sessionId: string,
  hostToken: string,
  participantId: string
): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/participants/${participantId}`, {
    method: 'DELETE',
    headers: { 'X-Session-Token': hostToken },
  });
  return handleResponse<any>(response);
}

export async function leaveSession(sessionId: string, token: string): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/leave`, {
    method: 'POST',
    headers: { 'X-Session-Token': token },
  });
  return handleResponse<any>(response);
}

export async function closeSession(sessionId: string, hostToken: string): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/close`, {
    method: 'POST',
    headers: { 'X-Session-Token': hostToken },
  });
  return handleResponse<any>(response);
}
