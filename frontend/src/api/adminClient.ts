/**
 * REST API client for Admin/League endpoints
 */

import type {
  LeagueSummary,
  GenerateLeagueRequest,
  TeamSummary,
  TeamDetail,
  PlayerSummary,
  PlayerDetail,
  DivisionStandings,
  ScheduledGame,
  WeekResult,
  PlayoffPicture,
  SimulateWeekRequest,
  SimulateToWeekRequest,
  GameDetail,
  Play,
  SeasonLeader,
  PlayerSeasonStats,
  DepthChart,
  PlayoffBracket,
  PlayoffResults,
  DraftState,
  CreateDraftRequest,
  DraftResult,
  DraftPick,
  TeamNeeds,
  TeamCapSummary,
  TeamCapPlayers,
} from '../types/admin';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

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

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// Saved league info
export interface SavedLeague {
  id: string;
  name: string;
  season: number;
  created_at: string;
}

// Admin API
export const adminApi = {
  // League
  generateLeague: (data: GenerateLeagueRequest = {}): Promise<LeagueSummary> =>
    request('/admin/league/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getLeague: (): Promise<LeagueSummary> =>
    request('/admin/league'),

  listLeagues: (): Promise<SavedLeague[]> =>
    request('/admin/leagues'),

  loadLeague: (leagueId: string): Promise<LeagueSummary> =>
    request(`/admin/league/load/${leagueId}`, { method: 'POST' }),

  // Teams
  listTeams: (conference?: string, division?: string): Promise<TeamSummary[]> => {
    const params = new URLSearchParams();
    if (conference) params.append('conference', conference);
    if (division) params.append('division', division);
    const query = params.toString();
    return request(`/admin/teams${query ? `?${query}` : ''}`);
  },

  getTeam: (abbreviation: string): Promise<TeamDetail> =>
    request(`/admin/teams/${abbreviation}`),

  getTeamRoster: (
    abbreviation: string,
    position?: string,
    sortBy: string = 'depth_chart'
  ): Promise<PlayerSummary[]> => {
    const params = new URLSearchParams({ sort_by: sortBy });
    if (position) params.append('position', position);
    return request(`/admin/teams/${abbreviation}/roster?${params}`);
  },

  // Players
  getPlayer: (playerId: string): Promise<PlayerDetail> =>
    request(`/admin/players/${playerId}`),

  searchPlayers: (options: {
    position?: string;
    minOverall?: number;
    maxOverall?: number;
    team?: string;
    limit?: number;
  } = {}): Promise<PlayerSummary[]> => {
    const params = new URLSearchParams();
    if (options.position) params.append('position', options.position);
    if (options.minOverall) params.append('min_overall', String(options.minOverall));
    if (options.maxOverall) params.append('max_overall', String(options.maxOverall));
    if (options.team) params.append('team', options.team);
    if (options.limit) params.append('limit', String(options.limit));
    return request(`/admin/players?${params}`);
  },

  // Free Agents
  getFreeAgents: (position?: string, minOverall?: number, limit?: number): Promise<PlayerSummary[]> => {
    const params = new URLSearchParams();
    if (position) params.append('position', position);
    if (minOverall) params.append('min_overall', String(minOverall));
    if (limit) params.append('limit', String(limit));
    return request(`/admin/free-agents?${params}`);
  },

  // Draft Class
  getDraftClass: (position?: string, limit?: number): Promise<PlayerSummary[]> => {
    const params = new URLSearchParams();
    if (position) params.append('position', position);
    if (limit) params.append('limit', String(limit));
    return request(`/admin/draft-class?${params}`);
  },

  // Standings
  getStandings: (conference?: string): Promise<DivisionStandings[]> => {
    const params = new URLSearchParams();
    if (conference) params.append('conference', conference);
    const query = params.toString();
    return request(`/admin/standings${query ? `?${query}` : ''}`);
  },

  // Schedule
  getSchedule: (week?: number, team?: string): Promise<ScheduledGame[]> => {
    const params = new URLSearchParams();
    if (week) params.append('week', String(week));
    if (team) params.append('team', team);
    const query = params.toString();
    return request(`/admin/schedule${query ? `?${query}` : ''}`);
  },

  // Simulation
  simulateWeek: (data: SimulateWeekRequest = {}): Promise<WeekResult> =>
    request('/admin/simulate/week', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  simulateToWeek: (data: SimulateToWeekRequest): Promise<WeekResult[]> =>
    request('/admin/simulate/to-week', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  simulateSeason: (): Promise<WeekResult[]> =>
    request('/admin/simulate/season', {
      method: 'POST',
    }),

  getPlayoffPicture: (): Promise<PlayoffPicture> =>
    request('/admin/playoff-picture'),

  // Game Details & Stats
  getGameDetail: (gameId: string): Promise<GameDetail> =>
    request(`/admin/games/${gameId}`),

  getGamePlays: (gameId: string, options: {
    quarter?: number;
    limit?: number;
    offset?: number;
  } = {}): Promise<Play[]> => {
    const params = new URLSearchParams();
    if (options.quarter) params.append('quarter', String(options.quarter));
    if (options.limit) params.append('limit', String(options.limit));
    if (options.offset) params.append('offset', String(options.offset));
    const query = params.toString();
    return request(`/admin/games/${gameId}/plays${query ? `?${query}` : ''}`);
  },

  getGamePlayerStats: (gameId: string): Promise<Record<string, unknown>[]> =>
    request(`/admin/games/${gameId}/stats`),

  getSeasonLeaders: (category: string, stat: string, limit: number = 10): Promise<SeasonLeader[]> =>
    request(`/admin/stats/leaders?category=${category}&stat=${stat}&limit=${limit}`),

  getPlayerSeasonStats: (playerId: string): Promise<PlayerSeasonStats> =>
    request(`/admin/stats/player/${playerId}`),

  // Depth Charts
  getTeamDepthChart: (abbreviation: string): Promise<DepthChart> =>
    request(`/admin/teams/${abbreviation}/depth-chart`),

  // Team Stats
  getTeamStats: (abbreviation: string): Promise<{
    passing: PlayerSeasonStats[];
    rushing: PlayerSeasonStats[];
    receiving: PlayerSeasonStats[];
    defense: PlayerSeasonStats[];
  }> =>
    request(`/admin/teams/${abbreviation}/stats`),

  // Playoffs
  simulatePlayoffs: (): Promise<PlayoffResults> =>
    request('/admin/simulate/playoffs', { method: 'POST' }),

  getPlayoffBracket: (): Promise<PlayoffBracket> =>
    request('/admin/playoff-bracket'),

  // Draft
  createDraft: (data: CreateDraftRequest): Promise<DraftState> =>
    request('/admin/draft/create', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getDraftState: (): Promise<DraftState> =>
    request('/admin/draft/state'),

  startDraft: (): Promise<DraftState> =>
    request('/admin/draft/start', { method: 'POST' }),

  makePick: (playerId: string): Promise<DraftResult> =>
    request('/admin/draft/pick', {
      method: 'POST',
      body: JSON.stringify({ player_id: playerId }),
    }),

  simulateToUserPick: (): Promise<DraftResult> =>
    request('/admin/draft/simulate-to-user', { method: 'POST' }),

  simulateFullDraft: (): Promise<DraftResult> =>
    request('/admin/draft/simulate-full', { method: 'POST' }),

  getDraftPicks: (team?: string, round?: number): Promise<DraftPick[]> => {
    const params = new URLSearchParams();
    if (team) params.append('team', team);
    if (round) params.append('round', String(round));
    const query = params.toString();
    return request(`/admin/draft/picks${query ? `?${query}` : ''}`);
  },

  getAvailablePlayers: (position?: string, limit: number = 50): Promise<PlayerSummary[]> => {
    const params = new URLSearchParams();
    if (position) params.append('position', position);
    params.append('limit', String(limit));
    return request(`/admin/draft/available?${params}`);
  },

  getTeamNeeds: (abbreviation: string): Promise<TeamNeeds> =>
    request(`/admin/draft/team/${abbreviation}/needs`),

  // Salary Cap
  getTeamCapSummary: (abbreviation: string): Promise<TeamCapSummary> =>
    request(`/admin/teams/${abbreviation}/cap-summary`),

  getTeamCapPlayers: (abbreviation: string): Promise<TeamCapPlayers> =>
    request(`/admin/teams/${abbreviation}/cap-players`),
};

export { ApiError };
