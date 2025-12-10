/**
 * Zustand store for sandbox simulation state
 */

import { create } from 'zustand';
import type { Position2D, SandboxState, TickResult } from '../types/sandbox';

interface SandboxStore {
  // Connection state
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;

  // Session state
  sessionId: string | null;
  state: SandboxState | null;

  // Animation state (for interpolation)
  targetBlockerPos: Position2D;
  targetRusherPos: Position2D;
  currentBlockerPos: Position2D;
  currentRusherPos: Position2D;

  // Current tick info
  lastTick: TickResult | null;
  tickHistory: TickResult[];

  // Simulation controls
  isPaused: boolean;
  tickRateMs: number;

  // Actions
  setConnected: (connected: boolean) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setSessionId: (sessionId: string | null) => void;
  setState: (state: SandboxState) => void;
  updateFromTick: (tick: TickResult) => void;
  updatePositions: (blockerPos: Position2D, rusherPos: Position2D) => void;
  setTargetPositions: (blockerPos: Position2D, rusherPos: Position2D) => void;
  setPaused: (paused: boolean) => void;
  setTickRate: (rate: number) => void;
  clearSession: () => void;
}

export const useSandboxStore = create<SandboxStore>((set, get) => ({
  // Initial state
  isConnected: false,
  isLoading: false,
  error: null,

  sessionId: null,
  state: null,

  targetBlockerPos: { x: 0.5, y: 0 },
  targetRusherPos: { x: 0, y: 0 },
  currentBlockerPos: { x: 0.5, y: 0 },
  currentRusherPos: { x: 0, y: 0 },

  lastTick: null,
  tickHistory: [],

  isPaused: false,
  tickRateMs: 100,

  // Actions
  setConnected: (connected) => set({ isConnected: connected }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  setSessionId: (sessionId) => set({ sessionId }),

  setState: (state) => {
    set({
      state,
      sessionId: state.session_id,
      targetBlockerPos: state.blocker_position,
      targetRusherPos: state.rusher_position,
      currentBlockerPos: state.blocker_position,
      currentRusherPos: state.rusher_position,
      tickRateMs: state.tick_rate_ms,
    });
  },

  updateFromTick: (tick) => {
    const { tickHistory } = get();
    set({
      lastTick: tick,
      tickHistory: [...tickHistory, tick],
      targetBlockerPos: tick.blocker_position,
      targetRusherPos: tick.rusher_position,
    });
  },

  updatePositions: (blockerPos, rusherPos) => {
    set({
      currentBlockerPos: blockerPos,
      currentRusherPos: rusherPos,
    });
  },

  setTargetPositions: (blockerPos, rusherPos) => {
    set({
      targetBlockerPos: blockerPos,
      targetRusherPos: rusherPos,
    });
  },

  setPaused: (paused) => set({ isPaused: paused }),
  setTickRate: (rate) => set({ tickRateMs: rate }),

  clearSession: () =>
    set({
      sessionId: null,
      state: null,
      targetBlockerPos: { x: 0.5, y: 0 },
      targetRusherPos: { x: 0, y: 0 },
      currentBlockerPos: { x: 0.5, y: 0 },
      currentRusherPos: { x: 0, y: 0 },
      lastTick: null,
      tickHistory: [],
      isPaused: false,
      error: null,
    }),
}));
