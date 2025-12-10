/**
 * WebSocket message types matching the backend event schemas
 */

import type { DownState, GameState, PlayResult } from './game';
import type { TeamSummary } from './team';

export type WSMessageType =
  | 'play_completed'
  | 'scoring'
  | 'turnover'
  | 'quarter_end'
  | 'game_end'
  | 'awaiting_play_call'
  | 'state_sync'
  | 'error'
  | 'pause'
  | 'resume'
  | 'set_pacing'
  | 'play_call'
  | 'request_sync';

// Server -> Client messages

export interface PlayCompletedPayload {
  timestamp: string;
  game_id: string;
  quarter: number;
  time_remaining: string;
  home_score: number;
  away_score: number;
  result: PlayResult;
  down: number;
  yards_to_go: number;
  field_position: string;
  line_of_scrimmage: number;
  first_down_marker: number;
  offense_is_home: boolean;
}

export interface PlayCompletedMessage {
  type: 'play_completed';
  payload: PlayCompletedPayload;
}

export interface ScoringMessage {
  type: 'scoring';
  payload: {
    scoring_type: 'touchdown' | 'field_goal' | 'safety' | 'extra_point' | 'two_point';
    points: number;
    team_id: string;
    player_name?: string;
    description: string;
    new_score: {
      home: number;
      away: number;
    };
  };
}

export interface TurnoverMessage {
  type: 'turnover';
  payload: {
    turnover_type: 'interception' | 'fumble' | 'turnover_on_downs';
    description: string;
    losing_team_id: string;
    gaining_team_id: string;
  };
}

export interface QuarterEndMessage {
  type: 'quarter_end';
  payload: {
    quarter: number;
    home_score: number;
    away_score: number;
  };
}

export interface GameEndMessage {
  type: 'game_end';
  payload: {
    home_score: number;
    away_score: number;
    winner_id: string | null;
    is_tie: boolean;
  };
}

export interface AwaitingPlayCallMessage {
  type: 'awaiting_play_call';
  payload: {
    down_state: DownState;
    available_plays: string[];
  };
}

export interface StateSyncMessage {
  type: 'state_sync';
  payload: {
    game_state: GameState;
    home_team: TeamSummary;
    away_team: TeamSummary;
  };
}

export interface ErrorMessage {
  type: 'error';
  payload: {
    message: string;
    code: string;
  };
}

// Client -> Server messages

export interface PauseMessage {
  type: 'pause';
}

export interface ResumeMessage {
  type: 'resume';
}

export interface SetPacingMessage {
  type: 'set_pacing';
  payload: {
    pacing: 'instant' | 'fast' | 'normal' | 'slow';
  };
}

export interface PlayCallMessage {
  type: 'play_call';
  payload: {
    play_type: string;
    run_type?: string;
    pass_type?: string;
  };
}

export interface RequestSyncMessage {
  type: 'request_sync';
}

// Union types
export type ServerMessage =
  | PlayCompletedMessage
  | ScoringMessage
  | TurnoverMessage
  | QuarterEndMessage
  | GameEndMessage
  | AwaitingPlayCallMessage
  | StateSyncMessage
  | ErrorMessage;

export type ClientMessage =
  | PauseMessage
  | ResumeMessage
  | SetPacingMessage
  | PlayCallMessage
  | RequestSyncMessage;
