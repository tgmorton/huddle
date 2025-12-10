/**
 * Zustand store for game state management
 */

import { create } from 'zustand';
import type { GameState, PlayResult } from '../types/game';
import type { TeamSummary } from '../types/team';

interface PlayLogEntry {
  id: string;
  timestamp: number;
  description: string;
  isScoring: boolean;
  isTurnover: boolean;
  quarter: number;
  timeRemaining: string;
}

interface GameStore {
  // Connection state
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;

  // Game state
  gameId: string | null;
  gameState: GameState | null;
  homeTeam: TeamSummary | null;
  awayTeam: TeamSummary | null;

  // Play state
  lastPlayResult: PlayResult | null;
  playLog: PlayLogEntry[];
  awaitingPlayCall: boolean;
  availablePlays: string[];

  // Simulation state
  isPaused: boolean;
  pacing: 'instant' | 'fast' | 'normal' | 'slow';
  mode: 'auto' | 'manual' | 'step';

  // Actions
  setConnected: (connected: boolean) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  initGame: (gameId: string, gameState: GameState, homeTeam: TeamSummary, awayTeam: TeamSummary) => void;
  updateGameState: (gameState: GameState) => void;
  addPlayResult: (playResult: PlayResult, gameState: GameState) => void;
  addPlayFromWS: (payload: {
    result: PlayResult;
    quarter: number;
    time_remaining: string;
    home_score: number;
    away_score: number;
    down: number;
    yards_to_go: number;
    field_position: string;
    line_of_scrimmage: number;
    first_down_marker: number;
    offense_is_home: boolean;
  }) => void;
  setAwaitingPlayCall: (awaiting: boolean, availablePlays?: string[]) => void;

  setPaused: (paused: boolean) => void;
  setPacing: (pacing: 'instant' | 'fast' | 'normal' | 'slow') => void;
  setMode: (mode: 'auto' | 'manual' | 'step') => void;

  clearGame: () => void;
}

export const useGameStore = create<GameStore>((set, get) => ({
  // Initial state
  isConnected: false,
  isLoading: false,
  error: null,

  gameId: null,
  gameState: null,
  homeTeam: null,
  awayTeam: null,

  lastPlayResult: null,
  playLog: [],
  awaitingPlayCall: false,
  availablePlays: [],

  isPaused: false,
  pacing: 'normal',
  mode: 'auto',

  // Actions
  setConnected: (connected) => set({ isConnected: connected }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),

  initGame: (gameId, gameState, homeTeam, awayTeam) =>
    set({
      gameId,
      gameState,
      homeTeam,
      awayTeam,
      playLog: [],
      lastPlayResult: null,
      awaitingPlayCall: false,
      error: null,
    }),

  updateGameState: (gameState) => set({ gameState }),

  addPlayResult: (playResult, gameState) => {
    const { playLog } = get();
    const entry: PlayLogEntry = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      description: playResult.description,
      isScoring: playResult.is_scoring_play,
      isTurnover: playResult.is_turnover,
      quarter: gameState.clock.quarter,
      timeRemaining: gameState.clock.display,
    };
    set({
      gameState,
      lastPlayResult: playResult,
      playLog: [...playLog, entry],
    });
  },

  // Handle WebSocket play_completed payload (flat structure from backend)
  addPlayFromWS: (payload: {
    result: PlayResult;
    quarter: number;
    time_remaining: string;
    home_score: number;
    away_score: number;
    down: number;
    yards_to_go: number;
    field_position: string;
    line_of_scrimmage: number;
    first_down_marker: number;
    offense_is_home: boolean;
  }) => {
    const { playLog, gameState, homeTeam } = get();
    const entry: PlayLogEntry = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      description: payload.result.description,
      isScoring: payload.result.is_scoring_play,
      isTurnover: payload.result.is_turnover,
      quarter: payload.quarter,
      timeRemaining: payload.time_remaining,
    };

    // Determine which team has possession
    const teamWithBall = payload.offense_is_home && homeTeam ? homeTeam.id : (gameState?.possession?.team_with_ball || '');

    // Update game state with new values from the play
    const updatedGameState = gameState ? {
      ...gameState,
      clock: {
        ...gameState.clock,
        quarter: payload.quarter,
        display: payload.time_remaining,
      },
      score: {
        ...gameState.score,
        home_score: payload.home_score,
        away_score: payload.away_score,
      },
      down_state: {
        ...gameState.down_state,
        down: payload.down,
        yards_to_go: payload.yards_to_go,
        field_position_display: payload.field_position,
        line_of_scrimmage: payload.line_of_scrimmage,
        first_down_marker: payload.first_down_marker,
        display: `${payload.down}${payload.down === 1 ? 'st' : payload.down === 2 ? 'nd' : payload.down === 3 ? 'rd' : 'th'} & ${payload.yards_to_go}`,
      },
      possession: {
        ...gameState.possession,
        team_with_ball: teamWithBall,
      },
    } : null;

    set({
      gameState: updatedGameState,
      lastPlayResult: payload.result,
      playLog: [...playLog, entry],
    });
  },

  setAwaitingPlayCall: (awaiting, availablePlays = []) =>
    set({ awaitingPlayCall: awaiting, availablePlays }),

  setPaused: (paused) => set({ isPaused: paused }),
  setPacing: (pacing) => set({ pacing }),
  setMode: (mode) => set({ mode }),

  clearGame: () =>
    set({
      gameId: null,
      gameState: null,
      homeTeam: null,
      awayTeam: null,
      lastPlayResult: null,
      playLog: [],
      awaitingPlayCall: false,
      availablePlays: [],
      isPaused: false,
      error: null,
    }),
}));
