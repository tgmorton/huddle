/**
 * API client for Historical Simulation Explorer.
 */

const API_BASE = 'http://localhost:8000/api/v1/history';

export interface SimulationConfig {
  num_teams: number;
  years_to_simulate: number;
  start_year: number;
  draft_rounds: number;
  verbose: boolean;
}

export interface SimulationSummary {
  sim_id: string;
  num_teams: number;
  seasons_simulated: number;
  start_year: number;
  end_year: number;
  total_transactions: number;
  created_at: string;
}

export interface ContractSnapshot {
  player_id: string;
  team_id: string;
  total_value: number;
  years_remaining: number;
  cap_hit: number;
  guaranteed_remaining: number;
  contract_type: string;
}

export interface PlayerSnapshot {
  id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  position: string;
  overall: number;
  age: number;
  experience_years: number;
  contract?: ContractSnapshot;
}

export interface TeamSnapshot {
  team_id: string;
  team_name: string;
  season: number;
  wins: number;
  losses: number;
  win_pct: number;
  roster_size: number;
  cap_used: number;
  cap_pct: number;
  status: string;
}

export interface TeamRoster {
  team_id: string;
  team_name: string;
  season: number;
  players: PlayerSnapshot[];
  cap_used: number;
  cap_remaining: number;
}

export interface TeamStanding {
  rank: number;
  team_id: string;
  team_name: string;
  wins: number;
  losses: number;
  win_pct: number;
  status: string;
}

export interface StandingsData {
  season: number;
  teams: TeamStanding[];
}

export interface DraftPick {
  round: number;
  pick: number;
  overall: number;
  team_id: string;
  team_name: string;
  player_id: string;
  player_name: string;
  position: string;
  overall_rating: number;
}

export interface DraftData {
  season: number;
  picks: DraftPick[];
}

export interface TransactionData {
  id: string;
  transaction_type: string;
  season: number;
  date: string;
  team_id: string;
  team_name: string;
  player_name: string;
  player_position: string;
  details: Record<string, unknown>;
}

export interface TransactionLog {
  transactions: TransactionData[];
  total_count: number;
}

export interface SeasonSummary {
  season: number;
  champion_team_id?: string;
  champion_team_name?: string;
  total_transactions: number;
  draft_picks: number;
  avg_cap_usage: number;
}

export interface FullSimulationData {
  sim_id: string;
  config: SimulationConfig;
  summary: SimulationSummary;
  seasons: SeasonSummary[];
  teams: TeamSnapshot[];
}

// API Functions

export async function runSimulation(config: Partial<SimulationConfig>): Promise<SimulationSummary> {
  const response = await fetch(`${API_BASE}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      num_teams: config.num_teams ?? 32,
      years_to_simulate: config.years_to_simulate ?? 3,
      start_year: config.start_year ?? 2021,
      draft_rounds: config.draft_rounds ?? 7,
      verbose: config.verbose ?? false,
    }),
  });
  if (!response.ok) throw new Error(`Failed to run simulation: ${response.statusText}`);
  return response.json();
}

export interface ProgressEvent {
  type: 'progress' | 'complete' | 'error';
  message?: string;
  summary?: SimulationSummary;
}

export async function runSimulationWithProgress(
  config: Partial<SimulationConfig>,
  onProgress: (event: ProgressEvent) => void,
): Promise<SimulationSummary> {
  const params = new URLSearchParams({
    num_teams: (config.num_teams ?? 32).toString(),
    years_to_simulate: (config.years_to_simulate ?? 3).toString(),
    start_year: (config.start_year ?? 2021).toString(),
  });

  const response = await fetch(`${API_BASE}/simulate-stream?${params.toString()}`);
  if (!response.ok) throw new Error(`Failed to run simulation: ${response.statusText}`);

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let summary: SimulationSummary | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text = decoder.decode(value);
    const lines = text.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event = JSON.parse(line.slice(6)) as ProgressEvent;
          onProgress(event);
          if (event.type === 'complete' && event.summary) {
            summary = event.summary;
          }
          if (event.type === 'error') {
            throw new Error(event.message || 'Simulation failed');
          }
        } catch (e) {
          // Ignore parse errors for incomplete chunks
        }
      }
    }
  }

  if (!summary) throw new Error('Simulation did not complete');
  return summary;
}

export async function listSimulations(): Promise<SimulationSummary[]> {
  const response = await fetch(`${API_BASE}/simulations`);
  if (!response.ok) throw new Error(`Failed to list simulations: ${response.statusText}`);
  return response.json();
}

export async function getSimulation(simId: string): Promise<FullSimulationData> {
  const response = await fetch(`${API_BASE}/simulations/${simId}`);
  if (!response.ok) throw new Error(`Failed to get simulation: ${response.statusText}`);
  return response.json();
}

export async function deleteSimulation(simId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/simulations/${simId}`, { method: 'DELETE' });
  if (!response.ok) throw new Error(`Failed to delete simulation: ${response.statusText}`);
}

export async function getTeamsInSeason(simId: string, season: number): Promise<TeamSnapshot[]> {
  const response = await fetch(`${API_BASE}/simulations/${simId}/seasons/${season}/teams`);
  if (!response.ok) throw new Error(`Failed to get teams: ${response.statusText}`);
  return response.json();
}

export async function getStandings(simId: string, season: number): Promise<StandingsData> {
  const response = await fetch(`${API_BASE}/simulations/${simId}/seasons/${season}/standings`);
  if (!response.ok) throw new Error(`Failed to get standings: ${response.statusText}`);
  return response.json();
}

export async function getDraft(simId: string, season: number): Promise<DraftData> {
  const response = await fetch(`${API_BASE}/simulations/${simId}/seasons/${season}/draft`);
  if (!response.ok) throw new Error(`Failed to get draft: ${response.statusText}`);
  return response.json();
}

export async function getTransactions(
  simId: string,
  options?: {
    season?: number;
    team_id?: string;
    transaction_type?: string;
    limit?: number;
    offset?: number;
  }
): Promise<TransactionLog> {
  const params = new URLSearchParams();
  if (options?.season !== undefined) params.append('season', options.season.toString());
  if (options?.team_id) params.append('team_id', options.team_id);
  if (options?.transaction_type) params.append('transaction_type', options.transaction_type);
  if (options?.limit) params.append('limit', options.limit.toString());
  if (options?.offset) params.append('offset', options.offset.toString());

  const url = `${API_BASE}/simulations/${simId}/transactions?${params.toString()}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Failed to get transactions: ${response.statusText}`);
  return response.json();
}

export async function getTeamRoster(simId: string, teamId: string, season: number): Promise<TeamRoster> {
  const response = await fetch(`${API_BASE}/simulations/${simId}/teams/${teamId}/roster?season=${season}`);
  if (!response.ok) throw new Error(`Failed to get roster: ${response.statusText}`);
  return response.json();
}
