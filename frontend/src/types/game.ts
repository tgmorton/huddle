/**
 * Game state types matching the backend Pydantic schemas
 */

export type GamePhase =
  | 'COIN_TOSS'
  | 'KICKOFF'
  | 'FIRST_QUARTER'
  | 'SECOND_QUARTER'
  | 'HALFTIME'
  | 'THIRD_QUARTER'
  | 'FOURTH_QUARTER'
  | 'OVERTIME'
  | 'GAME_OVER';

export type PlayType = 'RUN' | 'PASS' | 'PUNT' | 'FIELD_GOAL' | 'EXTRA_POINT' | 'TWO_POINT' | 'KICKOFF';

export type RunType = 'INSIDE' | 'OUTSIDE' | 'DRAW' | 'COUNTER' | 'SWEEP' | 'POWER' | 'DIVE';

export type PassType = 'SHORT' | 'MEDIUM' | 'DEEP' | 'SCREEN' | 'SLANT' | 'HITCH' | 'POST' | 'CORNER';

export type Formation =
  | 'SINGLEBACK'
  | 'I_FORMATION'
  | 'SHOTGUN'
  | 'PISTOL'
  | 'EMPTY'
  | 'GOAL_LINE'
  | 'WILDCAT';

export type PersonnelPackage = 'PERSONNEL_11' | 'PERSONNEL_12' | 'PERSONNEL_21' | 'PERSONNEL_22' | 'PERSONNEL_10';

export type PlayOutcome =
  | 'GAIN'
  | 'NO_GAIN'
  | 'LOSS'
  | 'FIRST_DOWN'
  | 'TOUCHDOWN'
  | 'FUMBLE'
  | 'INTERCEPTION'
  | 'INCOMPLETE'
  | 'SACK'
  | 'PENALTY'
  | 'SAFETY'
  | 'FIELD_GOAL_MADE'
  | 'FIELD_GOAL_MISSED'
  | 'EXTRA_POINT_MADE'
  | 'EXTRA_POINT_MISSED'
  | 'TWO_POINT_MADE'
  | 'TWO_POINT_FAILED'
  | 'PUNT'
  | 'TOUCHBACK'
  | 'TURNOVER_ON_DOWNS';

export interface ClockState {
  quarter: number;
  time_remaining_seconds: number;
  play_clock: number;
  quarter_length_seconds: number;
  minutes: number;
  seconds: number;
  display: string;
  is_two_minute_warning: boolean;
}

export interface ScoreState {
  home_score: number;
  away_score: number;
  home_by_quarter: number[];
  away_by_quarter: number[];
  margin: number;
  is_tied: boolean;
}

export interface DownState {
  down: number;
  yards_to_go: number;
  line_of_scrimmage: number;
  display: string;
  field_position_display: string;
  is_goal_to_go: boolean;
  is_fourth_down: boolean;
  first_down_marker: number;
}

export interface PossessionState {
  team_with_ball: string;
  receiving_second_half: string;
  home_timeouts: number;
  away_timeouts: number;
}

export interface GameState {
  id: string;
  home_team_id: string;
  away_team_id: string;
  clock: ClockState;
  phase: GamePhase;
  score: ScoreState;
  down_state: DownState;
  possession: PossessionState;
  is_game_over: boolean;
  current_quarter: number;
}

export interface PlayResult {
  play_type: PlayType;
  outcome: PlayOutcome;
  yards_gained: number;
  description: string;
  is_touchdown: boolean;
  is_turnover: boolean;
  is_scoring_play: boolean;
  is_first_down: boolean;
  passer?: string;
  receiver?: string;
  rusher?: string;
  tackler?: string;
  penalty_type?: string;
  penalty_yards?: number;
  penalty_on_offense?: boolean;
}

export interface PlayCall {
  play_type: PlayType;
  run_type?: RunType;
  pass_type?: PassType;
  formation?: Formation;
  personnel?: PersonnelPackage;
}

export interface CreateGameRequest {
  home_team_id?: string;
  away_team_id?: string;
  generate_teams?: boolean;
}

export interface GameSettingsUpdate {
  pacing?: 'instant' | 'fast' | 'normal' | 'slow';
  mode?: 'auto' | 'manual' | 'step';
}
