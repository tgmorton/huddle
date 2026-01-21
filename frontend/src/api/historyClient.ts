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
  gm_archetype?: string;  // analytics, old_school, cap_wizard, win_now, balanced
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
  gm_archetype?: string;
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
  // AI reasoning fields
  position_value?: number;  // Research-backed draft value (0-1)
  need_score?: number;  // How badly team needed this position (0-1)
  gm_adjustment?: number;  // GM archetype modifier
  is_draft_priority?: boolean;  // Should draft vs sign in FA
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

// =============================================================================
// New AI Visibility Interfaces
// =============================================================================

export interface PositionAllocation {
  position: string;
  actual_pct: number;
  target_pct: number;
  gap: number;  // positive = under-invested
  player_count: number;
  total_cap: number;
}

export interface CapAllocationData {
  team_id: string;
  team_name: string;
  season: number;
  gm_archetype: string;
  total_cap: number;
  cap_used: number;
  cap_pct: number;
  offense_allocation: PositionAllocation[];
  defense_allocation: PositionAllocation[];
}

export interface FATarget {
  position: string;
  priority: number;
  budget_pct: number;
  reason: string;
}

export interface FASigning {
  player_id: string;
  player_name: string;
  position: string;
  overall: number;
  age: number;
  contract_years: number;
  contract_value: number;
  cap_hit: number;
  was_target: boolean;
  value_vs_market: number;
}

export interface FAStrategyData {
  team_id: string;
  team_name: string;
  season: number;
  gm_archetype: string;
  cap_space_before: number;
  target_positions: FATarget[];
  positions_to_avoid: string[];
  cap_space_after: number;
  signings: FASigning[];
  total_spent: number;
  plan_success_pct: number;
  positions_filled: string[];
  positions_missed: string[];
}

export interface TeamProfile {
  team_id: string;
  team_name: string;
  season: number;
  gm_archetype: string;
  gm_description: string;
  rookie_premium: number;
  position_preferences: Record<string, number>;
  team_identity?: string;
  offensive_philosophy?: string;
  defensive_philosophy?: string;
  status: string;
  status_since?: number;
  draft_philosophy: string;
  spending_style: string;
}

export interface GMComparisonEntry {
  archetype: string;
  team_count: number;
  avg_wins: number;
  avg_win_pct: number;
  playoffs_made: number;
  championships: number;
  avg_cap_efficiency: number;
  draft_hit_rate: number;
}

export interface GMComparisonData {
  season: number;
  archetypes: GMComparisonEntry[];
}

// =============================================================================
// Position-by-Position Roster Planning
// =============================================================================

export interface PositionOption {
  option_type: 'FA' | 'DRAFT' | 'KEEP' | 'TRADE';
  player_name: string;
  overall: number;
  age: number;
  probability: number;  // 0-100
  details: string;
  player_id?: string;
  projected_cost?: number;
  years?: number;
}

export interface PositionPlan {
  position: string;
  position_group: string;
  need_level: number;  // 0-1
  need_reason: string;
  current_starter?: string;
  current_overall?: number;
  current_age?: number;
  current_contract_years?: number;
  research_recommendation: 'Draft' | 'Sign in FA';
  rookie_premium: number;
  options: PositionOption[];
}

export interface RosterPlan {
  team_id: string;
  team_name: string;
  season: number;
  gm_archetype: string;
  cap_space: number;
  draft_picks: string[];
  offense_plans: PositionPlan[];
  defense_plans: PositionPlan[];
  total_needs: number;
  fa_targets: number;
  draft_targets: number;
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

// =============================================================================
// New AI Visibility API Functions
// =============================================================================

export async function getTeamProfile(simId: string, teamId: string, season: number): Promise<TeamProfile> {
  const response = await fetch(`${API_BASE}/simulations/${simId}/teams/${teamId}/profile?season=${season}`);
  if (!response.ok) throw new Error(`Failed to get team profile: ${response.statusText}`);
  return response.json();
}

export async function getTeamAllocation(simId: string, teamId: string, season: number): Promise<CapAllocationData> {
  const response = await fetch(`${API_BASE}/simulations/${simId}/teams/${teamId}/allocation?season=${season}`);
  if (!response.ok) throw new Error(`Failed to get cap allocation: ${response.statusText}`);
  return response.json();
}

export async function getTeamFAStrategy(simId: string, teamId: string, season: number): Promise<FAStrategyData> {
  const response = await fetch(`${API_BASE}/simulations/${simId}/teams/${teamId}/fa-strategy?season=${season}`);
  if (!response.ok) throw new Error(`Failed to get FA strategy: ${response.statusText}`);
  return response.json();
}

export async function getGMComparison(simId: string, season: number): Promise<GMComparisonData> {
  const response = await fetch(`${API_BASE}/simulations/${simId}/seasons/${season}/gm-comparison`);
  if (!response.ok) throw new Error(`Failed to get GM comparison: ${response.statusText}`);
  return response.json();
}

export async function getRosterPlan(simId: string, teamId: string, season: number): Promise<RosterPlan> {
  const response = await fetch(`${API_BASE}/simulations/${simId}/teams/${teamId}/roster-plan?season=${season}`);
  if (!response.ok) throw new Error(`Failed to get roster plan: ${response.statusText}`);
  return response.json();
}

// =============================================================================
// Franchise Creation from Simulation
// =============================================================================

export interface StartFranchiseResponse {
  franchise_id: string;
  team_id: string;
  team_name: string;
  league_id: string;
  season: number;
  message: string;
}

export interface PlayerDevelopmentEntry {
  season: number;
  age: number;
  overall: number;
  change: number;
}

export interface PlayerDevelopmentResponse {
  player_id: string;
  player_name: string;
  position: string;
  career_arc: PlayerDevelopmentEntry[];
}

/**
 * Start a franchise from a historical simulation.
 *
 * Converts the simulation to a playable league and creates a franchise
 * for the specified team.
 */
export async function startFranchiseFromSimulation(
  simId: string,
  teamId: string
): Promise<StartFranchiseResponse> {
  const response = await fetch(
    `${API_BASE}/simulations/${simId}/start-franchise?team_id=${teamId}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }
  );
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `Failed to start franchise: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get player development history across simulated seasons.
 */
export async function getPlayerDevelopment(
  simId: string,
  playerId: string
): Promise<PlayerDevelopmentResponse> {
  const response = await fetch(
    `${API_BASE}/simulations/${simId}/players/${playerId}/development`
  );
  if (!response.ok) throw new Error(`Failed to get player development: ${response.statusText}`);
  return response.json();
}

// =============================================================================
// Save/Load API Functions
// =============================================================================

export interface SavedSimulationInfo {
  sim_id: string;
  start_year: number;
  end_year: number;
  seasons_simulated: number;
  num_teams: number;
  total_transactions: number;
  saved_at: string;
}

/**
 * Save a simulation to disk.
 *
 * Persists the simulation data so it can be loaded later.
 */
export async function saveSimulation(simId: string): Promise<{ status: string; sim_id: string }> {
  const response = await fetch(`${API_BASE}/simulations/${simId}/save`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(`Failed to save simulation: ${response.statusText}`);
  return response.json();
}

/**
 * Load a saved simulation from disk into memory.
 */
export async function loadSavedSimulation(simId: string): Promise<SimulationSummary> {
  const response = await fetch(`${API_BASE}/simulations/${simId}/load`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(`Failed to load simulation: ${response.statusText}`);
  return response.json();
}

/**
 * List all saved simulations on disk.
 */
export async function listSavedSimulations(): Promise<SavedSimulationInfo[]> {
  const response = await fetch(`${API_BASE}/saved-simulations`);
  if (!response.ok) throw new Error(`Failed to list saved simulations: ${response.statusText}`);
  return response.json();
}

/**
 * Delete a saved simulation from disk.
 */
export async function deleteSavedSimulation(simId: string): Promise<{ status: string; sim_id: string }> {
  const response = await fetch(`${API_BASE}/saved-simulations/${simId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error(`Failed to delete saved simulation: ${response.statusText}`);
  return response.json();
}
