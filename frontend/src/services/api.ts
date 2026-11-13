import { OptimizeMeetingRequest, OptimizeMeetingResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  details?: Record<string, unknown>;

  constructor(message: string, status: number, details?: Record<string, unknown>) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

/**
 * Call the meeting optimization API endpoint.
 */
export async function optimizeMeeting(
  request: OptimizeMeetingRequest
): Promise<OptimizeMeetingResponse> {
  const url = `${API_BASE_URL}/api/v1/meeting/optimize`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      let errorMessage = `Calculation request failed with status ${response.status}`;
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
            // Pydantic validation error list
            errorMessage = errorJson.detail
              .map((err: { loc?: string[]; msg?: string }) => err.msg || 'Validation error')
              .join(', ');
          }
        }
      } catch {
        // Response was not JSON
      }

      throw new ApiError(errorMessage, response.status, errorDetails);
    }

    const data: OptimizeMeetingResponse = await response.json();
    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Network or fetch connection failure
    throw new ApiError(
      'Unable to connect to the MeetPoint backend service. Please ensure the server is running.',
      0
    );
  }
}

/**
 * Check backend service health status.
 */
export async function checkBackendHealth(): Promise<{ status: string; version: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (response.ok) {
      return await response.json();
    }
    return { status: 'unhealthy', version: 'unknown' };
  } catch {
    return { status: 'offline', version: 'unknown' };
  }
}
