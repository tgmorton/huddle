/**
 * Types for sandbox blocking simulation
 */

export interface SandboxPlayer {
  id: string;
  name: string;
  role: 'blocker' | 'rusher';
  strength: number;
  speed: number;
  agility: number;
  pass_block: number;
  awareness: number;
  block_shedding: number;
  power_moves: number;
  finesse_moves: number;
}

export interface Position2D {
  x: number;
  y: number;
}

export interface TickResult {
  tick_number: number;
  timestamp_ms: number;
  blocker_position: Position2D;
  rusher_position: Position2D;
  rusher_technique: string;
  blocker_technique: string;
  rusher_score: number;
  blocker_score: number;
  margin: number;
  movement: number;
  matchup_state: 'initial' | 'engaged' | 'rusher_winning' | 'blocker_winning' | 'shed' | 'pancake';
  outcome: 'in_progress' | 'rusher_win' | 'blocker_win' | 'pancake';
  rusher_depth: number;
  engagement_duration_ms: number;
}

export interface SandboxState {
  session_id: string;
  blocker: SandboxPlayer;
  rusher: SandboxPlayer;
  tick_rate_ms: number;
  max_ticks: number;
  qb_zone_depth: number;
  current_tick: number;
  is_running: boolean;
  is_complete: boolean;
  blocker_position: Position2D;
  rusher_position: Position2D;
  outcome: string;
  stats: {
    rusher_wins_contest: number;
    blocker_wins_contest: number;
    neutral_contests: number;
  };
}

// WebSocket message types

export type SandboxWSMessageType =
  | 'start_simulation'
  | 'pause_simulation'
  | 'resume_simulation'
  | 'reset_simulation'
  | 'update_player'
  | 'set_tick_rate'
  | 'request_sync'
  | 'tick_update'
  | 'simulation_complete'
  | 'state_sync'
  | 'error';

export interface SandboxTickUpdateMessage {
  type: 'tick_update';
  payload: TickResult;
}

export interface SandboxStateSyncMessage {
  type: 'state_sync';
  payload: SandboxState;
}

export interface SandboxSimulationCompleteMessage {
  type: 'simulation_complete';
  payload: SandboxState;
}

export interface SandboxErrorMessage {
  type: 'error';
  message: string;
  code: string;
}

export type SandboxServerMessage =
  | SandboxTickUpdateMessage
  | SandboxStateSyncMessage
  | SandboxSimulationCompleteMessage
  | SandboxErrorMessage;
