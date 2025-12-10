/**
 * Zustand store for management/franchise mode state
 */

import { create } from 'zustand';
import type {
  LeagueState,
  CalendarState,
  EventQueue,
  ClipboardState,
  TickerFeed,
  ManagementEvent,
  TickerItem,
  ClipboardTab,
} from '../types/management';

interface ManagementStore {
  // Connection state
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;

  // Session state
  franchiseId: string | null;
  state: LeagueState | null;

  // Derived state (for easy access)
  calendar: CalendarState | null;
  events: EventQueue | null;
  clipboard: ClipboardState | null;
  ticker: TickerFeed | null;

  // UI state
  showAutoPauseModal: boolean;
  autoPauseReason: string | null;
  autoPauseEventId: string | null;

  // Actions - Connection
  setConnected: (connected: boolean) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setFranchiseId: (id: string | null) => void;

  // Actions - State updates
  setFullState: (state: LeagueState) => void;
  updateCalendar: (calendar: CalendarState) => void;
  updateEvents: (events: EventQueue) => void;
  updateClipboard: (clipboard: ClipboardState) => void;
  addTickerItem: (item: TickerItem) => void;
  addEvent: (event: ManagementEvent) => void;

  // Actions - UI
  showAutoPause: (reason: string, eventId: string | null) => void;
  dismissAutoPause: () => void;

  // Actions - Clear
  clearSession: () => void;
}

export const useManagementStore = create<ManagementStore>((set, get) => ({
  // Initial state
  isConnected: false,
  isLoading: false,
  error: null,

  franchiseId: null,
  state: null,

  calendar: null,
  events: null,
  clipboard: null,
  ticker: null,

  showAutoPauseModal: false,
  autoPauseReason: null,
  autoPauseEventId: null,

  // Actions - Connection
  setConnected: (connected) => set({ isConnected: connected }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  setFranchiseId: (franchiseId) => set({ franchiseId }),

  // Actions - State updates
  setFullState: (state) => {
    set({
      state,
      franchiseId: state.id,
      calendar: state.calendar,
      events: state.events,
      clipboard: state.clipboard,
      ticker: state.ticker,
    });
  },

  updateCalendar: (calendar) => {
    const { state } = get();
    if (state) {
      set({
        calendar,
        state: { ...state, calendar },
      });
    } else {
      set({ calendar });
    }
  },

  updateEvents: (events) => {
    const { state } = get();
    if (state) {
      set({
        events,
        state: { ...state, events },
      });
    } else {
      set({ events });
    }
  },

  updateClipboard: (clipboard) => {
    const { state } = get();
    if (state) {
      set({
        clipboard,
        state: { ...state, clipboard },
      });
    } else {
      set({ clipboard });
    }
  },

  addTickerItem: (item) => {
    const { ticker, state } = get();
    if (ticker) {
      const newTicker: TickerFeed = {
        ...ticker,
        items: [item, ...ticker.items].slice(0, 50), // Keep last 50
        unread_count: ticker.unread_count + 1,
        breaking_count: item.is_breaking
          ? ticker.breaking_count + 1
          : ticker.breaking_count,
      };
      if (state) {
        set({
          ticker: newTicker,
          state: { ...state, ticker: newTicker },
        });
      } else {
        set({ ticker: newTicker });
      }
    }
  },

  addEvent: (event) => {
    const { events, state } = get();
    if (events) {
      const newEvents: EventQueue = {
        ...events,
        pending: [event, ...events.pending],
        urgent_count: event.is_urgent
          ? events.urgent_count + 1
          : events.urgent_count,
        total_count: events.total_count + 1,
      };
      if (state) {
        set({
          events: newEvents,
          state: { ...state, events: newEvents },
        });
      } else {
        set({ events: newEvents });
      }
    }
  },

  // Actions - UI
  showAutoPause: (reason, eventId) => {
    set({
      showAutoPauseModal: true,
      autoPauseReason: reason,
      autoPauseEventId: eventId,
    });
  },

  dismissAutoPause: () => {
    set({
      showAutoPauseModal: false,
      autoPauseReason: null,
      autoPauseEventId: null,
    });
  },

  // Actions - Clear
  clearSession: () =>
    set({
      franchiseId: null,
      state: null,
      calendar: null,
      events: null,
      clipboard: null,
      ticker: null,
      isConnected: false,
      error: null,
      showAutoPauseModal: false,
      autoPauseReason: null,
      autoPauseEventId: null,
    }),
}));

// Empty arrays/objects to avoid creating new references
const EMPTY_EVENTS: ManagementEvent[] = [];
const EMPTY_TABS: ClipboardTab[] = ['EVENTS'];
const EMPTY_BADGES: Record<string, number> = {};
const EMPTY_TICKER: TickerItem[] = [];

// Selectors for common derived state - use stable references
export const selectIsPaused = (state: ManagementStore) =>
  state.calendar?.is_paused ?? true;

export const selectCurrentSpeed = (state: ManagementStore) =>
  state.calendar?.speed ?? 'PAUSED';

export const selectPendingEvents = (state: ManagementStore) =>
  state.events?.pending ?? EMPTY_EVENTS;

export const selectUrgentCount = (state: ManagementStore) =>
  state.events?.urgent_count ?? 0;

export const selectActiveTab = (state: ManagementStore) =>
  state.clipboard?.active_tab ?? 'EVENTS';

export const selectAvailableTabs = (state: ManagementStore) =>
  state.clipboard?.available_tabs ?? EMPTY_TABS;

export const selectTabBadges = (state: ManagementStore) =>
  state.clipboard?.tab_badges ?? EMPTY_BADGES;

export const selectTickerItems = (state: ManagementStore) =>
  state.ticker?.items ?? EMPTY_TICKER;
