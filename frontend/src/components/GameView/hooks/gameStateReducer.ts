/**
 * gameStateReducer - Centralized state management for GameView
 *
 * Consolidates the 20+ state variables from GameView into a single
 * reducer-based state management system.
 */

import type {
  GamePhase,
  ViewMode,
  Formation,
  PersonnelGroup,
  CoverageScheme,
  BlitzPackage,
  PlayResult,
  DrivePlay,
} from '../types';
import type { GameMode } from '../components/GameStartFlow';

// Panel views for left sidebar
export type GamePanelView = 'drive' | 'scout' | 'stats' | 'settings' | null;

// State shape
export interface GameState {
  // Game mode and status
  gameMode: GameMode;
  gameStarted: boolean;
  phase: GamePhase;

  // Teams
  homeTeam: string;
  awayTeam: string;
  userIsHome: boolean;

  // Offense selections
  selectedFormation: Formation | null;
  selectedPersonnel: PersonnelGroup;
  selectedPlayCode: string | null;
  selectedCategory: string;

  // Defense selections
  selectedCoverage: CoverageScheme | null;
  selectedBlitz: BlitzPackage;

  // Results and history (coach mode only)
  coachLastResult: PlayResult | null;
  coachDrive: DrivePlay[];

  // UI state
  viewMode: ViewMode;
  sidebarExpanded: boolean;
  activePanel: GamePanelView;
  showSpecialTeamsModal: boolean;
  tickerPaused: boolean;
  appNavOpen: boolean;
}

// Initial state
export const initialGameState: GameState = {
  // Game mode and status
  gameMode: 'coach',
  gameStarted: false,
  phase: 'pre_snap',

  // Teams
  homeTeam: 'NYG',
  awayTeam: 'DAL',
  userIsHome: true,

  // Offense selections
  selectedFormation: 'shotgun',
  selectedPersonnel: '11',
  selectedPlayCode: null,
  selectedCategory: 'run',

  // Defense selections
  selectedCoverage: 'cover_3',
  selectedBlitz: 'none',

  // Results and history
  coachLastResult: null,
  coachDrive: [],

  // UI state
  viewMode: 'simulcast',
  sidebarExpanded: false,
  activePanel: 'drive',
  showSpecialTeamsModal: false,
  tickerPaused: false,
  appNavOpen: false,
};

// Action types
export type GameAction =
  // Game flow
  | { type: 'SET_GAME_MODE'; payload: GameMode }
  | { type: 'SET_GAME_STARTED'; payload: boolean }
  | { type: 'SET_PHASE'; payload: GamePhase }
  | { type: 'START_GAME'; payload: { homeTeam: string; awayTeam: string; userIsHome: boolean; mode: GameMode } }
  | { type: 'RESET_GAME' }

  // Teams
  | { type: 'SET_HOME_TEAM'; payload: string }
  | { type: 'SET_AWAY_TEAM'; payload: string }
  | { type: 'SET_USER_IS_HOME'; payload: boolean }

  // Offense selections
  | { type: 'SET_FORMATION'; payload: Formation | null }
  | { type: 'SET_PERSONNEL'; payload: PersonnelGroup }
  | { type: 'SET_PLAY_CODE'; payload: string | null }
  | { type: 'SET_CATEGORY'; payload: string }

  // Defense selections
  | { type: 'SET_COVERAGE'; payload: CoverageScheme | null }
  | { type: 'SET_BLITZ'; payload: BlitzPackage }

  // Results and history
  | { type: 'SET_COACH_RESULT'; payload: PlayResult | null }
  | { type: 'ADD_DRIVE_PLAY'; payload: DrivePlay }
  | { type: 'CLEAR_DRIVE' }

  // UI state
  | { type: 'SET_VIEW_MODE'; payload: ViewMode }
  | { type: 'TOGGLE_VIEW_MODE' }
  | { type: 'SET_SIDEBAR_EXPANDED'; payload: boolean }
  | { type: 'TOGGLE_SIDEBAR' }
  | { type: 'SET_ACTIVE_PANEL'; payload: GamePanelView }
  | { type: 'TOGGLE_PANEL'; payload: GamePanelView }
  | { type: 'SET_SPECIAL_TEAMS_MODAL'; payload: boolean }
  | { type: 'SET_TICKER_PAUSED'; payload: boolean }
  | { type: 'TOGGLE_TICKER' }
  | { type: 'SET_APP_NAV_OPEN'; payload: boolean }

  // Play execution
  | { type: 'EXECUTE_PLAY' }
  | { type: 'PLAY_COMPLETE'; payload: PlayResult }
  | { type: 'DISMISS_RESULT' };

// Reducer function
export function gameStateReducer(state: GameState, action: GameAction): GameState {
  switch (action.type) {
    // Game flow
    case 'SET_GAME_MODE':
      return { ...state, gameMode: action.payload };

    case 'SET_GAME_STARTED':
      return { ...state, gameStarted: action.payload };

    case 'SET_PHASE':
      return { ...state, phase: action.payload };

    case 'START_GAME':
      return {
        ...state,
        homeTeam: action.payload.homeTeam,
        awayTeam: action.payload.awayTeam,
        userIsHome: action.payload.userIsHome,
        gameMode: action.payload.mode,
        gameStarted: true,
        phase: 'pre_snap',
        coachDrive: [],
        coachLastResult: null,
      };

    case 'RESET_GAME':
      return {
        ...initialGameState,
        // Preserve UI preferences
        sidebarExpanded: state.sidebarExpanded,
        viewMode: state.viewMode,
      };

    // Teams
    case 'SET_HOME_TEAM':
      return { ...state, homeTeam: action.payload };

    case 'SET_AWAY_TEAM':
      return { ...state, awayTeam: action.payload };

    case 'SET_USER_IS_HOME':
      return { ...state, userIsHome: action.payload };

    // Offense selections
    case 'SET_FORMATION':
      return { ...state, selectedFormation: action.payload };

    case 'SET_PERSONNEL':
      return { ...state, selectedPersonnel: action.payload };

    case 'SET_PLAY_CODE':
      return { ...state, selectedPlayCode: action.payload };

    case 'SET_CATEGORY':
      return { ...state, selectedCategory: action.payload };

    // Defense selections
    case 'SET_COVERAGE':
      return { ...state, selectedCoverage: action.payload };

    case 'SET_BLITZ':
      return { ...state, selectedBlitz: action.payload };

    // Results and history
    case 'SET_COACH_RESULT':
      return { ...state, coachLastResult: action.payload };

    case 'ADD_DRIVE_PLAY':
      return { ...state, coachDrive: [...state.coachDrive, action.payload] };

    case 'CLEAR_DRIVE':
      return { ...state, coachDrive: [] };

    // UI state
    case 'SET_VIEW_MODE':
      return { ...state, viewMode: action.payload };

    case 'TOGGLE_VIEW_MODE':
      return {
        ...state,
        viewMode: state.viewMode === 'simulcast' ? 'full_field' : 'simulcast',
      };

    case 'SET_SIDEBAR_EXPANDED':
      return { ...state, sidebarExpanded: action.payload };

    case 'TOGGLE_SIDEBAR':
      return { ...state, sidebarExpanded: !state.sidebarExpanded };

    case 'SET_ACTIVE_PANEL':
      return { ...state, activePanel: action.payload };

    case 'TOGGLE_PANEL':
      return {
        ...state,
        activePanel: state.activePanel === action.payload ? null : action.payload,
      };

    case 'SET_SPECIAL_TEAMS_MODAL':
      return { ...state, showSpecialTeamsModal: action.payload };

    case 'SET_TICKER_PAUSED':
      return { ...state, tickerPaused: action.payload };

    case 'TOGGLE_TICKER':
      return { ...state, tickerPaused: !state.tickerPaused };

    case 'SET_APP_NAV_OPEN':
      return { ...state, appNavOpen: action.payload };

    // Play execution
    case 'EXECUTE_PLAY':
      return { ...state, phase: 'executing' };

    case 'PLAY_COMPLETE':
      return {
        ...state,
        phase: 'result',
        coachLastResult: action.payload,
      };

    case 'DISMISS_RESULT':
      return {
        ...state,
        phase: 'pre_snap',
        selectedPlayCode: null,
      };

    default:
      return state;
  }
}
