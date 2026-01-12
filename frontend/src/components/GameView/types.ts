/**
 * GameView Types
 *
 * Type definitions for the coach's game view mode.
 */

// Game phases
export type GamePhase = 'pre_game' | 'pre_snap' | 'executing' | 'result' | 'special_teams' | 'game_over';
export type ViewMode = 'simulcast' | 'full_field';

// Coverage and blitz types
export type CoverageScheme = 'cover_0' | 'cover_1' | 'cover_2' | 'cover_3' | 'cover_4' | 'cover_6' | 'man';
export type BlitzPackage = 'none' | 'zone_blitz' | 'lb_blitz' | 'db_blitz' | 'all_out';

// Formation types
export type Formation =
  | 'i_form'
  | 'shotgun'
  | 'singleback'
  | 'pistol'
  | 'empty'
  | 'goal_line'
  | 'jumbo';

// Personnel groupings (# RBs, # TEs)
export type PersonnelGroup = '11' | '12' | '21' | '22' | '10' | '13' | '23';

// Play categories for offensive plays
export type PlayCategory = 'run' | 'quick' | 'intermediate' | 'deep' | 'screen' | 'play_action';

// Game situation from API
export interface GameSituation {
  quarter: number;
  timeRemaining: string;
  down: number;
  distance: number;
  los: number; // 0-100, where 0 = own goal line
  yardLineDisplay: string; // e.g., "OWN 35" or "OPP 25"
  homeScore: number;
  awayScore: number;
  possessionHome: boolean;
  isRedZone: boolean;
  isGoalToGo: boolean;
  userOnOffense: boolean;
  homeTimeouts: number;
  awayTimeouts: number;
}

// Play result from API
export interface PlayResult {
  outcome: 'complete' | 'incomplete' | 'sack' | 'run' | 'interception' | 'fumble' | 'touchdown' | 'penalty' | 'punt' | 'field_goal_good' | 'field_goal_missed';
  yardsGained: number;
  description: string;
  newDown: number;
  newDistance: number;
  newLos: number;
  firstDown: boolean;
  touchdown: boolean;
  turnover: boolean;
  isDriveOver: boolean;
  driveEndReason?: string;
  passerName?: string;
  receiverName?: string;
  tacklerName?: string;
}

// Drive play for history
export interface DrivePlay {
  playNumber: number;
  down: number;
  distance: number;
  los: number;
  playType: string;
  playName?: string;
  yardsGained: number;
  outcome: string;
  isFirstDown: boolean;
}

// Drive result summary
export interface DriveResult {
  plays: DrivePlay[];
  totalYards: number;
  timeOfPossession: string;
  result: 'touchdown' | 'field_goal' | 'punt' | 'turnover' | 'turnover_on_downs' | 'end_of_half' | 'safety';
  pointsScored: number;
  startingLos: number;
  endingLos: number;
}

// Available play option
export interface PlayOption {
  code: string;
  name: string;
  category: PlayCategory;
  description?: string;
  isRecommended?: boolean;
}

// Defensive play option
export interface DefenseOption {
  code: string;
  name: string;
  coverage: CoverageScheme;
  blitz: BlitzPackage;
  description?: string;
  riskLevel?: 'low' | 'medium' | 'high';
}

// Box score statistics
export interface BoxScore {
  home: TeamStats;
  away: TeamStats;
}

export interface TeamStats {
  totalYards: number;
  passingYards: number;
  rushingYards: number;
  firstDowns: number;
  turnovers: number;
  timeOfPossession: string;
  thirdDownConversions: string; // "5/12"
}

// Scouting intel (opponent tendencies)
export interface ScoutingIntel {
  coverageTendencies: { scheme: CoverageScheme; percentage: number }[];
  blitzRate: {
    overall: number;
    thirdDown: number;
    redZone: number;
  };
  weaknesses: string[];
}

// Key player performance
export interface KeyPlayerPerformance {
  playerId: string;
  name: string;
  position: string;
  status: 'hot' | 'cold' | 'neutral';
  statLine: string; // e.g., "5 rec, 87 yds, TD"
}

// Main game view state
export interface GameViewState {
  // Game identification
  gameId: string | null;

  // Current situation
  situation: GameSituation | null;
  phase: GamePhase;

  // User selections (offense)
  selectedFormation: Formation | null;
  selectedPersonnel: PersonnelGroup;
  selectedPlay: string | null;

  // User selections (defense)
  selectedCoverage: CoverageScheme | null;
  selectedBlitz: BlitzPackage;

  // Play result
  lastResult: PlayResult | null;

  // History
  currentDrive: DrivePlay[];
  allDrives: DriveResult[];
  boxScore: BoxScore | null;

  // UI state
  viewMode: ViewMode;
  activeSidePanel: string | null;
  soundEnabled: boolean;
}

// Props for intel panels
export interface IntelPanelProps {
  gameId: string;
  situation: GameSituation | null;
}

// League ticker mock item
export interface LeagueScore {
  homeTeam: string;
  awayTeam: string;
  homeScore: number;
  awayScore: number;
  quarter: number | 'FINAL';
  timeRemaining?: string;
}
