/**
 * Zustand store for SimExplorer state management.
 */

import { create } from 'zustand';
import type {
  SimulationSummary,
  FullSimulationData,
  TeamSnapshot,
  TeamRoster,
  StandingsData,
  DraftData,
  TransactionLog,
} from '../api/historyClient';
import {
  runSimulationWithProgress,
  listSimulations,
  getSimulation,
  getStandings,
  getDraft,
  getTransactions,
  getTeamRoster,
} from '../api/historyClient';

export type ViewMode = 'overview' | 'standings' | 'roster' | 'draft' | 'transactions';

interface SimExplorerState {
  // Simulation list
  simulations: SimulationSummary[];

  // Current simulation
  currentSimId: string | null;
  currentSimulation: FullSimulationData | null;

  // Navigation
  selectedSeason: number | null;
  selectedTeamId: string | null;
  viewMode: ViewMode;

  // View data
  standings: StandingsData | null;
  draft: DraftData | null;
  transactions: TransactionLog | null;
  selectedRoster: TeamRoster | null;

  // UI state
  isLoading: boolean;
  isGenerating: boolean;
  progressMessage: string | null;
  error: string | null;

  // Actions
  loadSimulations: () => Promise<void>;
  generateSimulation: (numTeams?: number, years?: number) => Promise<void>;
  selectSimulation: (simId: string) => Promise<void>;
  selectSeason: (season: number) => Promise<void>;
  selectTeam: (teamId: string) => Promise<void>;
  setViewMode: (mode: ViewMode) => void;
  loadStandings: () => Promise<void>;
  loadDraft: () => Promise<void>;
  loadTransactions: (options?: { team_id?: string; transaction_type?: string }) => Promise<void>;
  loadRoster: (teamId: string) => Promise<void>;
  clearError: () => void;
}

export const useSimExplorerStore = create<SimExplorerState>((set, get) => ({
  // Initial state
  simulations: [],
  currentSimId: null,
  currentSimulation: null,
  selectedSeason: null,
  selectedTeamId: null,
  viewMode: 'overview',
  standings: null,
  draft: null,
  transactions: null,
  selectedRoster: null,
  isLoading: false,
  isGenerating: false,
  progressMessage: null,
  error: null,

  // Load available simulations
  loadSimulations: async () => {
    set({ isLoading: true, error: null });
    try {
      const simulations = await listSimulations();
      set({ simulations, isLoading: false });
    } catch (err) {
      set({ error: `Failed to load simulations: ${err}`, isLoading: false });
    }
  },

  // Generate a new simulation with progress
  generateSimulation: async (numTeams = 32, years = 3) => {
    set({ isGenerating: true, progressMessage: 'Starting simulation...', error: null });
    try {
      const summary = await runSimulationWithProgress(
        {
          num_teams: numTeams,
          years_to_simulate: years,
          start_year: 2021,
        },
        (event) => {
          if (event.type === 'progress' && event.message) {
            set({ progressMessage: event.message });
          }
        }
      );

      // Reload simulations list
      const simulations = await listSimulations();

      set({
        simulations,
        isGenerating: false,
        progressMessage: null,
      });

      // Auto-select the new simulation
      await get().selectSimulation(summary.sim_id);
    } catch (err) {
      set({ error: `Failed to generate simulation: ${err}`, isGenerating: false, progressMessage: null });
    }
  },

  // Select a simulation
  selectSimulation: async (simId: string) => {
    set({ isLoading: true, error: null });
    try {
      const simulation = await getSimulation(simId);
      const firstSeason = simulation.config.start_year;

      set({
        currentSimId: simId,
        currentSimulation: simulation,
        selectedSeason: firstSeason,
        selectedTeamId: null,
        viewMode: 'overview',
        standings: null,
        draft: null,
        transactions: null,
        selectedRoster: null,
        isLoading: false,
      });
    } catch (err) {
      set({ error: `Failed to load simulation: ${err}`, isLoading: false });
    }
  },

  // Select a season
  selectSeason: async (season: number) => {
    set({ selectedSeason: season, standings: null, draft: null, selectedRoster: null });

    // Reload data for current view
    const { viewMode, selectedTeamId, loadStandings, loadDraft, loadTransactions, loadRoster } = get();
    if (viewMode === 'standings') await loadStandings();
    if (viewMode === 'draft') await loadDraft();
    if (viewMode === 'transactions') await loadTransactions();
    if (viewMode === 'roster' && selectedTeamId) await loadRoster(selectedTeamId);
  },

  // Select a team
  selectTeam: async (teamId: string) => {
    set({ selectedTeamId: teamId });
    await get().loadRoster(teamId);
  },

  // Set view mode
  setViewMode: (mode: ViewMode) => {
    set({ viewMode: mode });

    // Auto-load data for the view
    const { loadStandings, loadDraft, loadTransactions } = get();
    if (mode === 'standings') loadStandings();
    if (mode === 'draft') loadDraft();
    if (mode === 'transactions') loadTransactions();
  },

  // Load standings for current season
  loadStandings: async () => {
    const { currentSimId, selectedSeason } = get();
    if (!currentSimId || !selectedSeason) return;

    set({ isLoading: true });
    try {
      const standings = await getStandings(currentSimId, selectedSeason);
      set({ standings, isLoading: false });
    } catch (err) {
      set({ error: `Failed to load standings: ${err}`, isLoading: false });
    }
  },

  // Load draft for current season
  loadDraft: async () => {
    const { currentSimId, selectedSeason } = get();
    if (!currentSimId || !selectedSeason) return;

    set({ isLoading: true });
    try {
      const draft = await getDraft(currentSimId, selectedSeason);
      set({ draft, isLoading: false });
    } catch (err) {
      set({ error: `Failed to load draft: ${err}`, isLoading: false });
    }
  },

  // Load transactions
  loadTransactions: async (options) => {
    const { currentSimId, selectedSeason } = get();
    if (!currentSimId) return;

    set({ isLoading: true });
    try {
      const transactions = await getTransactions(currentSimId, {
        season: selectedSeason ?? undefined,
        ...options,
        limit: 200,
      });
      set({ transactions, isLoading: false });
    } catch (err) {
      set({ error: `Failed to load transactions: ${err}`, isLoading: false });
    }
  },

  // Load roster for a team
  loadRoster: async (teamId: string) => {
    const { currentSimId, selectedSeason } = get();
    if (!currentSimId || !selectedSeason) return;

    set({ isLoading: true });
    try {
      const roster = await getTeamRoster(currentSimId, teamId, selectedSeason);
      set({ selectedRoster: roster, isLoading: false });
    } catch (err) {
      set({ error: `Failed to load roster: ${err}`, isLoading: false });
    }
  },

  clearError: () => set({ error: null }),
}));
