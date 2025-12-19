/**
 * TypeScript types for management/franchise mode
 */

// === Enums ===

export type SeasonPhase =
  | 'OFFSEASON_EARLY'
  | 'FREE_AGENCY_LEGAL_TAMPERING'
  | 'FREE_AGENCY'
  | 'PRE_DRAFT'
  | 'DRAFT'
  | 'POST_DRAFT'
  | 'OTA'
  | 'MINICAMP'
  | 'TRAINING_CAMP'
  | 'PRESEASON'
  | 'REGULAR_SEASON'
  | 'WILD_CARD'
  | 'DIVISIONAL'
  | 'CONFERENCE_CHAMPIONSHIP'
  | 'SUPER_BOWL';

export type TimeSpeed = 'PAUSED' | 'SLOW' | 'NORMAL' | 'FAST' | 'VERY_FAST' | 'INSTANT';

export type EventCategory =
  | 'FREE_AGENCY'
  | 'TRADE'
  | 'CONTRACT'
  | 'ROSTER'
  | 'PRACTICE'
  | 'MEETING'
  | 'GAME'
  | 'SCOUTING'
  | 'DRAFT'
  | 'STAFF'
  | 'DEADLINE'
  | 'SYSTEM';

export type EventPriority = 'CRITICAL' | 'HIGH' | 'NORMAL' | 'LOW' | 'BACKGROUND';

export type EventStatus =
  | 'SCHEDULED'
  | 'PENDING'
  | 'IN_PROGRESS'
  | 'ATTENDED'
  | 'EXPIRED'
  | 'DISMISSED'
  | 'AUTO_RESOLVED';

export type ClipboardTab =
  | 'EVENTS'
  | 'ROSTER'
  | 'DEPTH_CHART'
  | 'SCHEDULE'
  | 'FREE_AGENTS'
  | 'TRADE_BLOCK'
  | 'DRAFT_BOARD'
  | 'COACHING_STAFF'
  | 'FRONT_OFFICE'
  | 'PLAYBOOK'
  | 'GAMEPLAN'
  | 'FINANCES'
  | 'STANDINGS'
  | 'LEAGUE_LEADERS'
  | 'TRANSACTIONS';

export type TickerCategory =
  | 'SIGNING'
  | 'RELEASE'
  | 'TRADE'
  | 'WAIVER'
  | 'SCORE'
  | 'INJURY'
  | 'INJURY_REPORT'
  | 'SUSPENSION'
  | 'RETIREMENT'
  | 'HOLDOUT'
  | 'DRAFT_PICK'
  | 'DRAFT_TRADE'
  | 'DEADLINE'
  | 'RECORD'
  | 'AWARD'
  | 'RUMOR';

// === State Types ===

export interface CalendarState {
  season_year: number;
  current_date: string;
  phase: SeasonPhase;
  current_week: number;
  speed: TimeSpeed;
  is_paused: boolean;
  day_name: string;
  time_display: string;
  date_display: string;
  week_display: string;
}

export interface ManagementEvent {
  id: string;
  event_type: string;
  category: EventCategory;
  priority: EventPriority;
  title: string;
  description: string;
  icon: string;
  created_at: string;
  scheduled_for: string | null;
  deadline: string | null;
  status: EventStatus;
  auto_pause: boolean;
  requires_attention: boolean;
  can_dismiss: boolean;
  can_delegate: boolean;
  team_id: string | null;
  player_ids: string[];
  payload: Record<string, unknown>;
  is_urgent: boolean;
}

export interface EventQueue {
  pending: ManagementEvent[];
  urgent_count: number;
  total_count: number;
}

export interface PanelContext {
  panel_type: string;
  event_id: string | null;
  player_id: string | null;
  team_id: string | null;
  game_id: string | null;
  can_go_back: boolean;
}

export interface ClipboardState {
  active_tab: ClipboardTab;
  panel: PanelContext;
  available_tabs: ClipboardTab[];
  tab_badges: Record<string, number>;
}

export interface TickerItem {
  id: string;
  category: TickerCategory;
  headline: string;
  detail: string;
  timestamp: string;
  is_breaking: boolean;
  priority: number;
  is_read: boolean;
  is_clickable: boolean;
  link_event_id: string | null;
  age_display: string;
}

export interface TickerFeed {
  items: TickerItem[];
  unread_count: number;
  breaking_count: number;
}

export interface LeagueState {
  id: string;
  player_team_id: string | null;
  calendar: CalendarState;
  events: EventQueue;
  clipboard: ClipboardState;
  ticker: TickerFeed;
}

// === API Types ===

export interface CreateFranchiseRequest {
  team_id: string;
  team_name: string;
  season_year?: number;
  start_phase?: SeasonPhase;
}

export interface FranchiseCreatedResponse {
  franchise_id: string;
  message: string;
}

// === WebSocket Message Types ===

export type ManagementWSMessageType =
  | 'state_sync'
  | 'calendar_update'
  | 'event_added'
  | 'event_updated'
  | 'event_removed'
  | 'ticker_item'
  | 'clipboard_update'
  | 'auto_paused'
  | 'error'
  | 'pause'
  | 'play'
  | 'set_speed'
  | 'select_tab'
  | 'attend_event'
  | 'dismiss_event'
  | 'go_back'
  | 'request_sync'
  | 'run_practice'
  | 'play_game'
  | 'sim_game';

export interface ManagementWSMessage {
  type: ManagementWSMessageType;
  payload?: Record<string, unknown>;
  error_message?: string;
  error_code?: string;
}

// === UI Helper Types ===

export interface TabInfo {
  id: ClipboardTab;
  name: string;
  icon: string;
  badge?: number;
}

export const TAB_DISPLAY_NAMES: Record<ClipboardTab, string> = {
  EVENTS: 'Events',
  ROSTER: 'Roster',
  DEPTH_CHART: 'Depth Chart',
  SCHEDULE: 'Schedule',
  FREE_AGENTS: 'Free Agents',
  TRADE_BLOCK: 'Trade Block',
  DRAFT_BOARD: 'Draft Board',
  COACHING_STAFF: 'Coaches',
  FRONT_OFFICE: 'Front Office',
  PLAYBOOK: 'Playbook',
  GAMEPLAN: 'Gameplan',
  FINANCES: 'Finances',
  STANDINGS: 'Standings',
  LEAGUE_LEADERS: 'Leaders',
  TRANSACTIONS: 'Transactions',
};

export const PRIORITY_COLORS: Record<EventPriority, string> = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  NORMAL: '#3b82f6',
  LOW: '#6b7280',
  BACKGROUND: '#9ca3af',
};

export const CATEGORY_ICONS: Record<EventCategory, string> = {
  FREE_AGENCY: 'user-plus',
  TRADE: 'exchange',
  CONTRACT: 'file-text',
  ROSTER: 'users',
  PRACTICE: 'dumbbell',
  MEETING: 'users',
  GAME: 'football',
  SCOUTING: 'search',
  DRAFT: 'graduation-cap',
  STAFF: 'briefcase',
  DEADLINE: 'clock',
  SYSTEM: 'info',
};

export const SPEED_LABELS: Record<TimeSpeed, string> = {
  PAUSED: 'Paused',
  SLOW: 'Slow',
  NORMAL: 'Normal',
  FAST: 'Fast',
  VERY_FAST: 'Very Fast',
  INSTANT: 'Instant',
};

// === Roster & Player Types ===

export interface PlayerSummary {
  id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  position: string;
  overall: number;
  potential: number;
  age: number;
  experience: number;
  jersey_number: number;
  team_abbr: string | null;
  morale?: number; // 0-100, optional
}

// Morale state for visual treatment
export type MoraleState = 'confident' | 'neutral' | 'struggling';

export function getMoraleState(morale: number | undefined): MoraleState {
  if (morale === undefined) return 'neutral';
  if (morale >= 70) return 'confident';
  if (morale <= 40) return 'struggling';
  return 'neutral';
}

export interface PlayerDetail extends PlayerSummary {
  height: string;
  weight: number;
  college: string | null;
  draft_year: number | null;
  draft_round: number | null;
  draft_pick: number | null;
  years_on_team: number;
  is_rookie: boolean;
  is_veteran: boolean;
  attributes: Record<string, number>;
}

export interface DepthChartEntry {
  slot: string;
  player_id: string | null;
  player_name: string | null;
  position: string | null;
  overall: number | null;
}

export interface DepthChartResponse {
  team_abbr: string;
  offense: DepthChartEntry[];
  defense: DepthChartEntry[];
  special_teams: DepthChartEntry[];
}

export interface ScheduledGame {
  game_id: string;
  week: number;
  home_team: string;
  away_team: string;
  home_score: number | null;
  away_score: number | null;
  is_played: boolean;
  is_home: boolean;
  opponent: string;
  result: string | null;
  day_of_week: string;
  time: string;
  is_primetime: boolean;
  is_division_game: boolean;
  is_conference_game: boolean;
}

// Position group for roster display
export type PositionGroup = 'QB' | 'RB' | 'WR' | 'TE' | 'OL' | 'DL' | 'LB' | 'DB' | 'ST';

export const POSITION_GROUPS: Record<PositionGroup, string[]> = {
  QB: ['QB'],
  RB: ['RB', 'FB'],
  WR: ['WR'],
  TE: ['TE'],
  OL: ['LT', 'LG', 'C', 'RG', 'RT', 'OT', 'OG'],
  DL: ['DE', 'DT', 'NT', 'EDGE'],
  LB: ['MLB', 'OLB', 'ILB', 'LB'],
  DB: ['CB', 'FS', 'SS', 'S'],
  ST: ['K', 'P', 'LS'],
};

export const POSITION_GROUP_NAMES: Record<PositionGroup, string> = {
  QB: 'Quarterbacks',
  RB: 'Running Backs',
  WR: 'Wide Receivers',
  TE: 'Tight Ends',
  OL: 'Offensive Line',
  DL: 'Defensive Line',
  LB: 'Linebackers',
  DB: 'Defensive Backs',
  ST: 'Special Teams',
};
