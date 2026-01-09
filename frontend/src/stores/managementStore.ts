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
import type { ScheduledGame } from '../types/admin';

// Extended type for next game with computed opponent info
export interface NextGameInfo {
  week: number;
  opponent: string;
  is_home: boolean;
  is_divisional: boolean;
  is_conference: boolean;
}

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

  // Journal version - incremented when journal entries are added
  journalVersion: number;

  // Schedule & standings
  teamAbbr: string | null;
  schedule: ScheduledGame[] | null;
  teamRecord: { wins: number; losses: number; ties: number } | null;
  nextGame: NextGameInfo | null;

  // Actions - Connection
  setConnected: (connected: boolean) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setFranchiseId: (id: string | null) => void;

  // Actions - State updates
  setFullState: (state: LeagueState) => void;
  updateCalendar: (calendar: CalendarState) => void;
  updateEvents: (events: EventQueue) => void;
  setEvents: (events: ManagementEvent[]) => void;
  mergeEvents: (newEvents: ManagementEvent[]) => void;
  updateClipboard: (clipboard: ClipboardState) => void;
  addTickerItem: (item: TickerItem) => void;
  addEvent: (event: ManagementEvent) => void;
  removeEvent: (eventId: string) => void;

  // Actions - UI
  showAutoPause: (reason: string, eventId: string | null) => void;
  dismissAutoPause: () => void;

  // Actions - Journal
  bumpJournalVersion: () => void;

  // Actions - Schedule
  setTeamAbbr: (abbr: string) => void;
  setSchedule: (schedule: ScheduledGame[]) => void;
  setTeamRecord: (record: { wins: number; losses: number; ties: number }) => void;
  setNextGame: (game: NextGameInfo | null) => void;

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

  journalVersion: 0,

  // Schedule & standings
  teamAbbr: null,
  schedule: null,
  teamRecord: null,
  nextGame: null,

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

  setEvents: (eventsList) => {
    const { state, events: existingEvents } = get();
    const newEvents: EventQueue = {
      pending: eventsList,
      upcoming: existingEvents?.upcoming || [],  // Preserve upcoming from previous state
      urgent_count: eventsList.filter(e => e.is_urgent).length,
      total_count: eventsList.length,
    };
    if (state) {
      set({
        events: newEvents,
        state: { ...state, events: newEvents },
      });
    } else {
      set({ events: newEvents });
    }
  },

  mergeEvents: (newEventsList) => {
    const { state, events: existingEvents } = get();
    // Get existing pending events
    const existingPending = existingEvents?.pending || [];
    // Create a set of existing IDs for fast lookup
    const existingIds = new Set(existingPending.map(e => e.id));
    // Filter out duplicates from new events and add to existing
    const uniqueNewEvents = newEventsList.filter(e => !existingIds.has(e.id));
    const mergedPending = [...uniqueNewEvents, ...existingPending];

    const mergedEvents: EventQueue = {
      pending: mergedPending,
      upcoming: existingEvents?.upcoming || [],
      urgent_count: mergedPending.filter(e => e.is_urgent).length,
      total_count: mergedPending.length,
    };
    if (state) {
      set({
        events: mergedEvents,
        state: { ...state, events: mergedEvents },
      });
    } else {
      set({ events: mergedEvents });
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

  removeEvent: (eventId) => {
    const { events, state } = get();
    if (events) {
      const eventToRemove = events.pending.find(e => e.id === eventId);
      const newPending = events.pending.filter(e => e.id !== eventId);
      const newEvents: EventQueue = {
        ...events,
        pending: newPending,
        urgent_count: eventToRemove?.is_urgent
          ? events.urgent_count - 1
          : events.urgent_count,
        total_count: Math.max(0, events.total_count - 1),
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

  // Actions - Journal
  bumpJournalVersion: () => {
    set((state) => ({ journalVersion: state.journalVersion + 1 }));
  },

  // Actions - Schedule
  setTeamAbbr: (abbr) => set({ teamAbbr: abbr }),
  setSchedule: (schedule) => set({ schedule }),
  setTeamRecord: (record) => set({ teamRecord: record }),
  setNextGame: (game) => set({ nextGame: game }),

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
      journalVersion: 0,
      teamAbbr: null,
      schedule: null,
      teamRecord: null,
      nextGame: null,
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

export const selectLeagueId = (state: ManagementStore) =>
  state.state?.league_id ?? null;

export const selectFranchiseId = (state: ManagementStore) =>
  state.franchiseId;

export const selectJournalVersion = (state: ManagementStore) =>
  state.journalVersion;

export const selectTeamAbbr = (state: ManagementStore) =>
  state.teamAbbr;

export const selectTeamRecord = (state: ManagementStore) =>
  state.teamRecord;

export const selectNextGame = (state: ManagementStore) =>
  state.nextGame;

export const selectSchedule = (state: ManagementStore) =>
  state.schedule;
