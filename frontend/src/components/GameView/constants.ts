/**
 * GameView Constants
 *
 * Configuration values for the coach's game view.
 */

import type {
  Formation,
  PersonnelGroup,
  PlayCategory,
  CoverageScheme,
  BlitzPackage,
  LeagueScore,
  GameSituation,
  PlayOption,
} from './types';

// Development-only mock mode flag
// Set VITE_USE_MOCK_DATA=true in .env.local to enable mock fallbacks
export const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA === 'true';

// Mock initial situation for development
export const MOCK_SITUATION: GameSituation = {
  quarter: 2,
  timeRemaining: '5:42',
  down: 2,
  distance: 7,
  los: 65,
  yardLineDisplay: 'OPP 35',
  homeScore: 21,
  awayScore: 14,
  possessionHome: true,
  isRedZone: false,
  isGoalToGo: false,
  userOnOffense: true,
  homeTimeouts: 3,
  awayTimeouts: 2,
};

// Mock available plays for development
export const MOCK_PLAYS: PlayOption[] = [
  { code: 'INSIDE_ZONE', name: 'Inside Zone', category: 'run', isRecommended: true },
  { code: 'POWER', name: 'Power', category: 'run' },
  { code: 'COUNTER', name: 'Counter', category: 'run' },
  { code: 'DRAW', name: 'Draw', category: 'run' },
  { code: 'STRETCH', name: 'Stretch', category: 'run' },
  { code: 'SLANT', name: 'Slant', category: 'quick' },
  { code: 'HITCH', name: 'Hitch', category: 'quick' },
  { code: 'OUT', name: 'Out', category: 'quick' },
  { code: 'CURL', name: 'Curl', category: 'intermediate' },
  { code: 'DIG', name: 'Dig', category: 'intermediate' },
  { code: 'POST', name: 'Post', category: 'deep' },
  { code: 'GO_ROUTE', name: 'Go Route', category: 'deep' },
  { code: 'FADE', name: 'Fade', category: 'deep' },
  { code: 'SCREEN', name: 'Screen', category: 'screen' },
  { code: 'PA_BOOT', name: 'PA Boot', category: 'play_action' },
];

// Mock ticker events for game
export const MOCK_TICKER_EVENTS = [
  { type: 'play', text: 'DAL ball at own 25 after touchback' },
  { type: 'score', text: 'TOUCHDOWN - NYG leads 7-0' },
  { type: 'injury', text: 'DAL WR questionable to return (hamstring)' },
  { type: 'play', text: 'NYG: 8 plays, 75 yards, 4:32 TOP' },
  { type: 'league', text: 'PHI 14, WAS 10 - 3rd Quarter' },
];

// Formation configurations with visual data
export const FORMATIONS: Record<Formation, {
  name: string;
  personnel: PersonnelGroup[];
  description: string;
}> = {
  i_form: {
    name: 'I-Form',
    personnel: ['21', '22'],
    description: 'Power running, play action',
  },
  shotgun: {
    name: 'Shotgun',
    personnel: ['11', '10', '12'],
    description: 'Spread passing, read option',
  },
  singleback: {
    name: 'Singleback',
    personnel: ['11', '12', '21'],
    description: 'Balanced, versatile',
  },
  pistol: {
    name: 'Pistol',
    personnel: ['11', '12', '21'],
    description: 'Zone read, RPO',
  },
  empty: {
    name: 'Empty',
    personnel: ['10', '11'],
    description: 'Max protection issues, quick reads',
  },
  goal_line: {
    name: 'Goal Line',
    personnel: ['22', '23', '13'],
    description: 'Power, short yardage',
  },
  jumbo: {
    name: 'Jumbo',
    personnel: ['22', '23'],
    description: 'Heavy run, extra blockers',
  },
};

// Personnel group descriptions
export const PERSONNEL_GROUPS: Record<PersonnelGroup, {
  name: string;
  description: string;
  rbCount: number;
  teCount: number;
}> = {
  '10': { name: '10 Personnel', description: '1 RB, 0 TE, 4 WR', rbCount: 1, teCount: 0 },
  '11': { name: '11 Personnel', description: '1 RB, 1 TE, 3 WR', rbCount: 1, teCount: 1 },
  '12': { name: '12 Personnel', description: '1 RB, 2 TE, 2 WR', rbCount: 1, teCount: 2 },
  '13': { name: '13 Personnel', description: '1 RB, 3 TE, 1 WR', rbCount: 1, teCount: 3 },
  '21': { name: '21 Personnel', description: '2 RB, 1 TE, 2 WR', rbCount: 2, teCount: 1 },
  '22': { name: '22 Personnel', description: '2 RB, 2 TE, 1 WR', rbCount: 2, teCount: 2 },
  '23': { name: '23 Personnel', description: '2 RB, 3 TE, 0 WR', rbCount: 2, teCount: 3 },
};

// Play categories with colors and descriptions
export const PLAY_CATEGORIES: Record<PlayCategory, {
  name: string;
  description: string;
  color: string;
}> = {
  run: {
    name: 'Run',
    description: 'Ground game plays',
    color: 'var(--success)',
  },
  quick: {
    name: 'Quick',
    description: '3-step drops, fast timing',
    color: 'var(--accent)',
  },
  intermediate: {
    name: 'Intermediate',
    description: '5-step drops, rhythm throws',
    color: 'var(--text-primary)',
  },
  deep: {
    name: 'Deep',
    description: '7-step drops, big play potential',
    color: 'var(--danger)',
  },
  screen: {
    name: 'Screen',
    description: 'Screen passes, misdirection',
    color: 'var(--warning)',
  },
  play_action: {
    name: 'Play Action',
    description: 'Fake run, deep shots',
    color: 'var(--text-secondary)',
  },
};

// Coverage scheme configurations
export const COVERAGE_SCHEMES: Record<CoverageScheme, {
  name: string;
  description: string;
  strength: string;
  weakness: string;
}> = {
  cover_0: {
    name: 'Cover 0',
    description: 'No deep help, all-out pressure',
    strength: 'Maximum pressure',
    weakness: 'No safety help',
  },
  cover_1: {
    name: 'Cover 1',
    description: 'Man coverage, single high safety',
    strength: 'Tight coverage, some deep help',
    weakness: 'Vulnerable to crossers',
  },
  cover_2: {
    name: 'Cover 2',
    description: 'Two deep safeties, zone underneath',
    strength: 'Stops deep balls',
    weakness: 'Soft in middle',
  },
  cover_3: {
    name: 'Cover 3',
    description: 'Three deep defenders, four underneath',
    strength: 'Balanced deep coverage',
    weakness: 'Soft flat zones',
  },
  cover_4: {
    name: 'Cover 4',
    description: 'Four deep quarters',
    strength: 'Excellent vs deep',
    weakness: 'Vulnerable to runs',
  },
  cover_6: {
    name: 'Cover 6',
    description: 'Quarters on one side, Cover 2 on other',
    strength: 'Flexible, disguised',
    weakness: 'Complex assignments',
  },
  man: {
    name: 'Man',
    description: 'Man-to-man coverage',
    strength: 'Tight coverage',
    weakness: 'Needs good corners',
  },
};

// Blitz package configurations
export const BLITZ_PACKAGES: Record<BlitzPackage, {
  name: string;
  description: string;
  rushers: number;
  riskLevel: 'low' | 'medium' | 'high';
}> = {
  none: {
    name: 'No Blitz',
    description: 'Standard rush, max coverage',
    rushers: 4,
    riskLevel: 'low',
  },
  zone_blitz: {
    name: 'Zone Blitz',
    description: 'Drop lineman, rush LB',
    rushers: 5,
    riskLevel: 'medium',
  },
  lb_blitz: {
    name: 'LB Blitz',
    description: 'Extra linebacker rush',
    rushers: 5,
    riskLevel: 'medium',
  },
  db_blitz: {
    name: 'DB Blitz',
    description: 'Corner or safety blitz',
    rushers: 5,
    riskLevel: 'high',
  },
  all_out: {
    name: 'All Out',
    description: 'Maximum pressure, cover 0',
    rushers: 6,
    riskLevel: 'high',
  },
};

// Situational tips based on down and distance
export const SITUATION_TIPS: Record<string, string> = {
  '1_long': 'First down - establish the run or take a shot',
  '2_short': 'Second and short - great run situation',
  '2_medium': 'Second and medium - balanced approach',
  '2_long': 'Second and long - passing down, watch for blitz',
  '3_short': 'Third and short - run or quick pass',
  '3_medium': 'Third and medium - must convert',
  '3_long': 'Third and long - expect coverage, find soft spots',
  '4_any': 'Fourth down - big decision time',
  'red_zone': 'Red zone - tightened windows, quick decisions',
  'goal_line': 'Goal line - power or misdirection',
  'two_minute': 'Two minute drill - manage the clock',
};

// Mock league scores for ticker
export const MOCK_LEAGUE_SCORES: LeagueScore[] = [
  { homeTeam: 'NYG', awayTeam: 'DAL', homeScore: 21, awayScore: 17, quarter: 3, timeRemaining: '8:42' },
  { homeTeam: 'KC', awayTeam: 'LV', homeScore: 35, awayScore: 28, quarter: 'FINAL' },
  { homeTeam: 'SF', awayTeam: 'SEA', homeScore: 14, awayScore: 14, quarter: 2, timeRemaining: '2:15' },
  { homeTeam: 'BUF', awayTeam: 'MIA', homeScore: 24, awayScore: 21, quarter: 4, timeRemaining: '5:30' },
  { homeTeam: 'PHI', awayTeam: 'WAS', homeScore: 10, awayScore: 7, quarter: 1, timeRemaining: '4:20' },
];

// Panel width configurations
export const PANEL_WIDTHS = {
  sidebar: 280,
  minSidebar: 240,
  maxSidebar: 360,
};

// Animation durations (ms)
export const ANIMATION_DURATIONS = {
  resultFadeIn: 300,
  resultFadeOut: 200,
  fieldTransition: 500,
  possessionChange: 800,
};

// Keyboard shortcuts
export const KEYBOARD_SHORTCUTS = {
  snap: 'Space',
  toggleView: 'v',
  timeout: 't',
  pause: 'p',
};
