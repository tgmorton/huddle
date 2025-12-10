/**
 * REST API client for Huddle backend
 */

import type { CreateGameRequest, GameSettingsUpdate, GameState, PlayCall, PlayResult } from '../types/game';
import type { TeamSummary, Team } from '../types/team';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

interface GameResponse {
  game_state: GameState;
  home_team: TeamSummary;
  away_team: TeamSummary;
}

class ApiError extends Error {
  status: number;
  statusText: string;

  constructor(status: number, statusText: string, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, response.statusText, errorData.detail || 'Request failed');
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// Games API
export const gamesApi = {
  create: (data: CreateGameRequest = { generate_teams: true }): Promise<GameResponse> =>
    request('/games', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  get: (gameId: string): Promise<GameResponse> => request(`/games/${gameId}`),

  delete: (gameId: string): Promise<void> =>
    request(`/games/${gameId}`, {
      method: 'DELETE',
    }),

  executePlay: (gameId: string): Promise<PlayResult> =>
    request(`/games/${gameId}/play`, {
      method: 'POST',
    }),

  submitPlayCall: (gameId: string, playCall: PlayCall): Promise<PlayResult> =>
    request(`/games/${gameId}/play-call`, {
      method: 'POST',
      body: JSON.stringify(playCall),
    }),

  pause: (gameId: string): Promise<void> =>
    request(`/games/${gameId}/pause`, {
      method: 'POST',
    }),

  resume: (gameId: string): Promise<void> =>
    request(`/games/${gameId}/resume`, {
      method: 'POST',
    }),

  step: (gameId: string): Promise<PlayResult> =>
    request(`/games/${gameId}/step`, {
      method: 'POST',
    }),

  updateSettings: (gameId: string, settings: GameSettingsUpdate): Promise<GameState> =>
    request(`/games/${gameId}/settings`, {
      method: 'PATCH',
      body: JSON.stringify(settings),
    }),

  getTeamStats: (gameId: string): Promise<Record<string, unknown>> =>
    request(`/games/${gameId}/stats/team`),

  getPlayerStats: (gameId: string): Promise<Record<string, unknown>> =>
    request(`/games/${gameId}/stats/players`),

  getHistory: (gameId: string): Promise<string[]> => request(`/games/${gameId}/history`),
};

// Teams API
export const teamsApi = {
  create: (): Promise<Team> =>
    request('/teams', {
      method: 'POST',
    }),

  list: (): Promise<TeamSummary[]> => request('/teams'),

  get: (teamId: string): Promise<Team> => request(`/teams/${teamId}`),

  delete: (teamId: string): Promise<void> =>
    request(`/teams/${teamId}`, {
      method: 'DELETE',
    }),

  getStarters: (teamId: string): Promise<Record<string, unknown>> =>
    request(`/teams/${teamId}/starters`),
};

// Health check
export const healthApi = {
  check: (): Promise<{ status: string; active_games: number }> =>
    request('/health'.replace('/api/v1', '')),
};

export { ApiError };
