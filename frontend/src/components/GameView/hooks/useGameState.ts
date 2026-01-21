/**
 * useGameState - Centralized state management hook for GameView
 *
 * Provides:
 * - Single source of truth for all game state
 * - Type-safe actions for state updates
 * - Derived values based on game mode
 * - localStorage persistence for UI preferences
 */

import { useReducer, useCallback, useEffect } from 'react';
import {
  gameStateReducer,
  initialGameState,
  type GameState,
  type GameAction,
  type GamePanelView,
} from './gameStateReducer';
import type {
  GamePhase,
  ViewMode,
  Formation,
  PersonnelGroup,
  CoverageScheme,
  BlitzPackage,
  PlayResult,
  DrivePlay,
  GameSituation,
} from '../types';
import type { GameMode } from '../components/GameStartFlow';

// Storage key for persisted UI preferences
const STORAGE_KEY = 'gameview-ui-prefs';

interface PersistedPrefs {
  sidebarExpanded: boolean;
}

// Load persisted preferences
function loadPersistedPrefs(): Partial<GameState> {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const prefs: PersistedPrefs = JSON.parse(stored);
      return { sidebarExpanded: prefs.sidebarExpanded };
    }
  } catch {
    // Ignore parse errors
  }
  return {};
}

// Save preferences to localStorage
function savePersistedPrefs(state: GameState): void {
  try {
    const prefs: PersistedPrefs = {
      sidebarExpanded: state.sidebarExpanded,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // Ignore storage errors
  }
}

export interface UseGameStateReturn {
  // Full state
  state: GameState;
  dispatch: React.Dispatch<GameAction>;

  // Commonly accessed values (convenience)
  gameMode: GameMode;
  gameStarted: boolean;
  phase: GamePhase;
  homeTeam: string;
  awayTeam: string;
  userIsHome: boolean;
  isSpectatorMode: boolean;

  // Offense selections
  selectedFormation: Formation | null;
  selectedPersonnel: PersonnelGroup;
  selectedPlayCode: string | null;
  selectedCategory: string;

  // Defense selections
  selectedCoverage: CoverageScheme | null;
  selectedBlitz: BlitzPackage;

  // UI state
  viewMode: ViewMode;
  sidebarExpanded: boolean;
  activePanel: GamePanelView;
  showSpecialTeamsModal: boolean;

  // Coach mode state
  coachLastResult: PlayResult | null;
  coachDrive: DrivePlay[];

  // Actions
  actions: {
    // Game flow
    startGame: (homeTeam: string, awayTeam: string, userIsHome: boolean, mode: GameMode) => void;
    resetGame: () => void;
    setPhase: (phase: GamePhase) => void;
    setGameStarted: (started: boolean) => void;

    // Offense
    setFormation: (formation: Formation | null) => void;
    setPersonnel: (personnel: PersonnelGroup) => void;
    setPlayCode: (playCode: string | null) => void;
    setCategory: (category: string) => void;

    // Defense
    setCoverage: (coverage: CoverageScheme | null) => void;
    setBlitz: (blitz: BlitzPackage) => void;

    // Results
    setCoachResult: (result: PlayResult | null) => void;
    addDrivePlay: (play: DrivePlay) => void;
    clearDrive: () => void;

    // UI
    setViewMode: (mode: ViewMode) => void;
    toggleViewMode: () => void;
    toggleSidebar: () => void;
    setSidebarExpanded: (expanded: boolean) => void;
    setActivePanel: (panel: GamePanelView) => void;
    togglePanel: (panel: GamePanelView) => void;
    setSpecialTeamsModal: (show: boolean) => void;
    setTickerPaused: (paused: boolean) => void;
    toggleTicker: () => void;
    setAppNavOpen: (open: boolean) => void;

    // Play execution
    executePlay: () => void;
    playComplete: (result: PlayResult) => void;
    dismissResult: () => void;
  };

  // Derived values
  getDerivedSituation: (
    spectatorSituation: GameSituation | null,
    coachSituation: GameSituation | null,
    mockSituation: GameSituation
  ) => GameSituation;

  getDerivedLastResult: (wsLastResult: PlayResult | null) => PlayResult | null;
  getDerivedDrive: (wsDrive: DrivePlay[]) => DrivePlay[];
}

export function useGameState(): UseGameStateReturn {
  // Initialize state with persisted preferences
  const [state, dispatch] = useReducer(
    gameStateReducer,
    { ...initialGameState, ...loadPersistedPrefs() }
  );

  // Persist UI preferences when they change
  useEffect(() => {
    savePersistedPrefs(state);
  }, [state.sidebarExpanded]);

  // Derived values
  const isSpectatorMode = state.gameMode === 'spectator';

  // Action creators
  const actions = {
    // Game flow
    startGame: useCallback((homeTeam: string, awayTeam: string, userIsHome: boolean, mode: GameMode) => {
      dispatch({ type: 'START_GAME', payload: { homeTeam, awayTeam, userIsHome, mode } });
    }, []),

    resetGame: useCallback(() => {
      dispatch({ type: 'RESET_GAME' });
    }, []),

    setPhase: useCallback((phase: GamePhase) => {
      dispatch({ type: 'SET_PHASE', payload: phase });
    }, []),

    setGameStarted: useCallback((started: boolean) => {
      dispatch({ type: 'SET_GAME_STARTED', payload: started });
    }, []),

    // Offense
    setFormation: useCallback((formation: Formation | null) => {
      dispatch({ type: 'SET_FORMATION', payload: formation });
    }, []),

    setPersonnel: useCallback((personnel: PersonnelGroup) => {
      dispatch({ type: 'SET_PERSONNEL', payload: personnel });
    }, []),

    setPlayCode: useCallback((playCode: string | null) => {
      dispatch({ type: 'SET_PLAY_CODE', payload: playCode });
    }, []),

    setCategory: useCallback((category: string) => {
      dispatch({ type: 'SET_CATEGORY', payload: category });
    }, []),

    // Defense
    setCoverage: useCallback((coverage: CoverageScheme | null) => {
      dispatch({ type: 'SET_COVERAGE', payload: coverage });
    }, []),

    setBlitz: useCallback((blitz: BlitzPackage) => {
      dispatch({ type: 'SET_BLITZ', payload: blitz });
    }, []),

    // Results
    setCoachResult: useCallback((result: PlayResult | null) => {
      dispatch({ type: 'SET_COACH_RESULT', payload: result });
    }, []),

    addDrivePlay: useCallback((play: DrivePlay) => {
      dispatch({ type: 'ADD_DRIVE_PLAY', payload: play });
    }, []),

    clearDrive: useCallback(() => {
      dispatch({ type: 'CLEAR_DRIVE' });
    }, []),

    // UI
    setViewMode: useCallback((mode: ViewMode) => {
      dispatch({ type: 'SET_VIEW_MODE', payload: mode });
    }, []),

    toggleViewMode: useCallback(() => {
      dispatch({ type: 'TOGGLE_VIEW_MODE' });
    }, []),

    toggleSidebar: useCallback(() => {
      dispatch({ type: 'TOGGLE_SIDEBAR' });
    }, []),

    setSidebarExpanded: useCallback((expanded: boolean) => {
      dispatch({ type: 'SET_SIDEBAR_EXPANDED', payload: expanded });
    }, []),

    setActivePanel: useCallback((panel: GamePanelView) => {
      dispatch({ type: 'SET_ACTIVE_PANEL', payload: panel });
    }, []),

    togglePanel: useCallback((panel: GamePanelView) => {
      dispatch({ type: 'TOGGLE_PANEL', payload: panel });
    }, []),

    setSpecialTeamsModal: useCallback((show: boolean) => {
      dispatch({ type: 'SET_SPECIAL_TEAMS_MODAL', payload: show });
    }, []),

    setTickerPaused: useCallback((paused: boolean) => {
      dispatch({ type: 'SET_TICKER_PAUSED', payload: paused });
    }, []),

    toggleTicker: useCallback(() => {
      dispatch({ type: 'TOGGLE_TICKER' });
    }, []),

    setAppNavOpen: useCallback((open: boolean) => {
      dispatch({ type: 'SET_APP_NAV_OPEN', payload: open });
    }, []),

    // Play execution
    executePlay: useCallback(() => {
      dispatch({ type: 'EXECUTE_PLAY' });
    }, []),

    playComplete: useCallback((result: PlayResult) => {
      dispatch({ type: 'PLAY_COMPLETE', payload: result });
    }, []),

    dismissResult: useCallback(() => {
      dispatch({ type: 'DISMISS_RESULT' });
    }, []),
  };

  // Derived value helpers that consider game mode
  const getDerivedSituation = useCallback((
    spectatorSituation: GameSituation | null,
    coachSituation: GameSituation | null,
    mockSituation: GameSituation
  ): GameSituation => {
    if (isSpectatorMode) {
      return spectatorSituation || mockSituation;
    }
    return coachSituation || mockSituation;
  }, [isSpectatorMode]);

  const getDerivedLastResult = useCallback((
    wsLastResult: PlayResult | null
  ): PlayResult | null => {
    return isSpectatorMode ? wsLastResult : state.coachLastResult;
  }, [isSpectatorMode, state.coachLastResult]);

  const getDerivedDrive = useCallback((
    wsDrive: DrivePlay[]
  ): DrivePlay[] => {
    return isSpectatorMode ? wsDrive : state.coachDrive;
  }, [isSpectatorMode, state.coachDrive]);

  return {
    // Full state
    state,
    dispatch,

    // Commonly accessed values
    gameMode: state.gameMode,
    gameStarted: state.gameStarted,
    phase: state.phase,
    homeTeam: state.homeTeam,
    awayTeam: state.awayTeam,
    userIsHome: state.userIsHome,
    isSpectatorMode,

    // Offense selections
    selectedFormation: state.selectedFormation,
    selectedPersonnel: state.selectedPersonnel,
    selectedPlayCode: state.selectedPlayCode,
    selectedCategory: state.selectedCategory,

    // Defense selections
    selectedCoverage: state.selectedCoverage,
    selectedBlitz: state.selectedBlitz,

    // UI state
    viewMode: state.viewMode,
    sidebarExpanded: state.sidebarExpanded,
    activePanel: state.activePanel,
    showSpecialTeamsModal: state.showSpecialTeamsModal,

    // Coach mode state
    coachLastResult: state.coachLastResult,
    coachDrive: state.coachDrive,

    // Actions
    actions,

    // Derived value helpers
    getDerivedSituation,
    getDerivedLastResult,
    getDerivedDrive,
  };
}

export default useGameState;
