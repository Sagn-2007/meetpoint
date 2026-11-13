import { OptimizationObjective, NetworkType, OptimizeMeetingResponse } from './index';

export type UserRole = 'HOST' | 'PARTICIPANT' | 'VIEWER';

export interface SessionParticipantPublic {
  id: string;
  display_name: string;
  latitude: number | null;
  longitude: number | null;
  location_submitted: boolean;
  is_online: boolean;
  joined_at: string;
}

export interface MeetingSessionPublic {
  session_id: string;
  invitation_code: string;
  title: string;
  description: string | null;
  status: 'active' | 'closed';
  network_type: NetworkType;
  optimization_objective: OptimizationObjective;
  top_k: number;
  result_is_stale: boolean;
  expires_at: string;
  created_at: string;
  participants_count: number;
  is_expired: boolean;
}

export interface SessionSnapshotData {
  session: MeetingSessionPublic;
  participants: SessionParticipantPublic[];
  latest_result: OptimizeMeetingResponse | null;
  user_role: UserRole;
  current_participant_id: string | null;
}

export interface CreateSessionRequest {
  title: string;
  description?: string;
  network_type: NetworkType;
  optimization_objective: OptimizationObjective;
  top_k: number;
}

export interface CreateSessionResponse {
  session_id: string;
  invitation_code: string;
  title: string;
  description: string | null;
  host_token: string;
  network_type: NetworkType;
  optimization_objective: OptimizationObjective;
  top_k: number;
  expires_at: string;
  created_at: string;
}

export interface JoinSessionRequest {
  display_name: string;
  latitude?: number;
  longitude?: number;
}

export interface JoinSessionResponse {
  session_id: string;
  participant_id: string;
  display_name: string;
  participant_token: string;
  location_submitted: boolean;
  latitude: number | null;
  longitude: number | null;
}

export interface WebSocketMessage {
  type: string;
  data: any;
}
