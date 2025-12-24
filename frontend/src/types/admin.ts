/**
 * TypeScript types for Admin/League exploration API
 */

// === League Types ===

export interface LeagueSummary {
  id: string;
  name: string;
  current_season: number;
  current_week: number;
  team_count: number;
  total_players: number;
  free_agent_count: number;
  draft_class_size: number;
  is_offseason: boolean;
  is_playoffs: boolean;
}

export interface GenerateLeagueRequest {
  season?: number;
  name?: string;
  include_schedule?: boolean;
  parity_mode?: boolean;
  fantasy_draft?: boolean;  // If true, start with empty rosters and run fantasy draft
}

// === Team Types ===

export interface TeamSummary {
  id: string;
  abbreviation: string;
  name: string;
  city: string;
  full_name: string;
  roster_size: number;
  primary_color: string;
  secondary_color: string;
  division: string;
  conference: string;
  offense_rating: number;
  defense_rating: number;
}

export interface TeamDetail extends TeamSummary {
  qb_name: string | null;
  qb_overall: number | null;
  top_players: {
    id: string;
    name: string;
    position: string;
    overall: number;
    jersey: number;
  }[];
}

// === Player Types ===

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
  // Contract fields for roster display
  salary: number | null;
  contract_year_remaining: number | null;
}

// Personality types
export type ArchetypeType =
  | 'TEAM_FIRST'
  | 'FIERCE_COMPETITOR'
  | 'QUIET_PROFESSIONAL'
  | 'MENTOR'
  | 'MONEY_MOTIVATED'
  | 'DIVA'
  | 'HOT_HEAD'
  | 'FREE_SPIRIT'
  | 'FILM_JUNKIE'
  | 'EMOTIONAL_LEADER'
  | 'STEADY_VETERAN'
  | 'RISING_STAR';

export type PersonalityTrait =
  | 'DRIVEN' | 'COMPETITIVE' | 'AMBITIOUS'  // Motivation
  | 'LOYAL' | 'TEAM_PLAYER' | 'TRUSTING' | 'COOPERATIVE'  // Interpersonal
  | 'PATIENT' | 'AGGRESSIVE' | 'IMPULSIVE' | 'LEVEL_HEADED' | 'SENSITIVE'  // Temperament
  | 'STRUCTURED' | 'FLEXIBLE' | 'PERFECTIONIST'  // Work Style
  | 'CONSERVATIVE' | 'RECKLESS' | 'CALCULATING'  // Risk
  | 'EXPRESSIVE' | 'RESERVED' | 'DRAMATIC'  // Social
  | 'MATERIALISTIC' | 'VALUES_TRADITION' | 'THRIFTY';  // Values

export interface PersonalityProfile {
  archetype: ArchetypeType;
  traits: Record<PersonalityTrait, number>;  // 0.0 - 1.0
}

export interface PlayerApproval {
  player_id: string;
  approval: number;  // 0-100
  trend: number;  // Recent direction
  grievances: string[];  // Last 5 negative events
  last_updated: string | null;
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
  // Management fields (may be null if not tracked)
  personality?: PersonalityProfile | null;
  approval?: PlayerApproval | null;
  contract_years?: number | null;
  signing_bonus?: number | null;
}

// === Standings Types ===

export interface StandingEntry {
  rank: number;
  abbreviation: string;
  team_name: string;
  wins: number;
  losses: number;
  ties: number;
  record: string;
  win_pct: number;
  division_record: string;
  points_for: number;
  points_against: number;
  point_diff: number;
}

export interface DivisionStandings {
  division: string;
  conference: string;
  teams: StandingEntry[];
}

// === Schedule Types ===

export interface ScheduledGame {
  id: string;
  week: number;
  home_team: string;
  away_team: string;
  home_score: number | null;
  away_score: number | null;
  is_played: boolean;
  is_divisional: boolean;
  is_conference: boolean;
  winner: string | null;
}

// === Simulation Types ===

export interface SimulateWeekRequest {
  week?: number;
}

export interface SimulateToWeekRequest {
  target_week: number;
}

export interface GameResult {
  game_id: string;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  winner: string | null;
  is_overtime: boolean;
  is_tie: boolean;
}

export interface WeekResult {
  week: number;
  games: GameResult[];
  total_games: number;
}

export interface PlayoffTeam {
  seed: number;
  abbreviation: string;
  team_name: string;
  record: string;
  win_pct: number;
  is_division_winner: boolean;
}

export interface PlayoffPicture {
  afc: PlayoffTeam[];
  nfc: PlayoffTeam[];
}

// === Stats Types ===

export interface PassingStats {
  attempts: number;
  completions: number;
  yards: number;
  touchdowns: number;
  interceptions: number;
  sacks: number;
  completion_pct: number;
  passer_rating: number;
}

export interface RushingStats {
  attempts: number;
  yards: number;
  touchdowns: number;
  fumbles_lost: number;
  yards_per_carry: number;
  longest: number;
}

export interface ReceivingStats {
  targets: number;
  receptions: number;
  yards: number;
  touchdowns: number;
  yards_per_reception: number;
  catch_pct: number;
}

export interface DefensiveStats {
  tackles: number;
  sacks: number;
  interceptions: number;
  passes_defended: number;
  forced_fumbles: number;
  fumble_recoveries: number;
}

export interface PlayerSeasonStats {
  player_id: string;
  player_name: string;
  team_abbr: string;
  position: string;
  games_played: number;
  passing?: PassingStats;
  rushing?: RushingStats;
  receiving?: ReceivingStats;
  defense?: DefensiveStats;
}

export interface TeamGameStats {
  team_abbr: string;
  total_yards: number;
  passing_yards: number;
  rushing_yards: number;
  first_downs: number;
  turnovers: number;
  penalties: number;
  penalty_yards: number;
  time_of_possession: string;
}

export interface ScoringPlay {
  play_number: number;
  quarter: number;
  time: string;
  description: string;
  points: number;
  home_score: number;
  away_score: number;
}

export interface GameDetail {
  game_id: string;
  week: number;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  is_overtime: boolean;
  is_playoff: boolean;
  home_stats: TeamGameStats;
  away_stats: TeamGameStats;
  scoring_plays: ScoringPlay[];
}

export interface Play {
  play_number: number;
  quarter: number;
  time: string;
  down: number;
  distance: number;
  yard_line: number;
  offense: string;
  play_type: string;
  yards: number;
  outcome: string;
  description: string;
  is_scoring: boolean;
}

export interface SeasonLeader {
  rank: number;
  player_id: string;
  player_name: string;
  team_abbr: string;
  position: string;
  games_played: number;
  value: number;
}

// === Depth Chart Types ===

export interface DepthChartEntry {
  slot: string;
  player_id: string | null;
  player_name: string | null;
  position: string | null;
  overall: number | null;
}

export interface DepthChart {
  team_abbr: string;
  offense: DepthChartEntry[];
  defense: DepthChartEntry[];
  special_teams: DepthChartEntry[];
}

// === Playoff Bracket Types ===

export interface PlayoffBracketGame {
  game_id: string | null;
  week: number;
  round_name: string;
  home_team: string | null;
  away_team: string | null;
  home_score: number | null;
  away_score: number | null;
  winner: string | null;
  is_played: boolean;
}

export interface PlayoffBracket {
  wild_card: PlayoffBracketGame[];
  divisional: PlayoffBracketGame[];
  conference: PlayoffBracketGame[];
  super_bowl: PlayoffBracketGame | null;
  champion: string | null;
}

export interface PlayoffResults {
  wild_card: GameResult[];
  divisional: GameResult[];
  conference: GameResult[];
  super_bowl: GameResult | null;
  champion: string | null;
}

// === Draft Types ===

export interface DraftPick {
  id: string;
  round: number;
  pick_number: number;
  round_pick: number;
  original_team: string;
  current_team: string;
  is_selected: boolean;
  was_traded: boolean;
  player_id: string | null;
  player_name: string | null;
  player_position: string | null;
}

export interface DraftState {
  id: string;
  draft_type: 'nfl' | 'fantasy';
  phase: 'not_started' | 'in_progress' | 'completed' | 'paused';
  season: number;
  num_rounds: number;
  num_teams: number;
  current_pick_index: number;
  current_round: number;
  picks_made: number;
  picks_remaining: number;
  is_user_pick: boolean;
  user_team: string | null;
  current_pick: DraftPick | null;
}

export interface CreateDraftRequest {
  draft_type: 'nfl' | 'fantasy';
  num_rounds?: number;
  user_team?: string;
}

export interface DraftResult {
  picks_made: DraftPick[];
  draft_complete: boolean;
}

export interface TeamNeeds {
  team: string;
  needs: Record<string, number>;
}

// === UI State ===

export type AdminView =
  | 'dashboard'
  | 'teams'
  | 'team-detail'
  | 'players'
  | 'player-detail'
  | 'standings'
  | 'schedule'
  | 'game-detail'
  | 'free-agents'
  | 'draft-class'
  | 'draft'
  | 'simulate'
  | 'stats'
  | 'depth-chart'
  | 'playoffs';

export interface AdminState {
  league: LeagueSummary | null;
  teams: TeamSummary[];
  selectedTeam: TeamDetail | null;
  selectedPlayer: PlayerDetail | null;
  standings: DivisionStandings[];
  schedule: ScheduledGame[];
  freeAgents: PlayerSummary[];
  draftClass: PlayerSummary[];
  currentView: AdminView;
  isLoading: boolean;
  error: string | null;
}

// === Position Constants ===

export const POSITIONS = [
  'QB', 'RB', 'FB', 'WR', 'TE',
  'LT', 'LG', 'C', 'RG', 'RT',
  'DE', 'DT', 'NT', 'MLB', 'ILB', 'OLB',
  'CB', 'FS', 'SS',
  'K', 'P', 'LS'
] as const;

export type Position = typeof POSITIONS[number];

export const POSITION_GROUPS: Record<string, Position[]> = {
  'Offense': ['QB', 'RB', 'FB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT'],
  'Defense': ['DE', 'DT', 'NT', 'MLB', 'ILB', 'OLB', 'CB', 'FS', 'SS'],
  'Special Teams': ['K', 'P', 'LS'],
};

export const CONFERENCES = ['AFC', 'NFC'] as const;

export const DIVISIONS = [
  'AFC East', 'AFC North', 'AFC South', 'AFC West',
  'NFC East', 'NFC North', 'NFC South', 'NFC West',
] as const;

// === Salary Cap Types ===

export interface CapProjection {
  year: number;
  committed: number;
  projected_cap: number;
  cap_space: number;
}

export interface TeamCapSummary {
  team_abbr: string;
  season: number;
  salary_cap: number;           // League cap for this year
  cap_committed: number;        // Total salary committed
  cap_space: number;            // Remaining space
  dead_money: number;           // Cap hits from cuts/trades
  projections: CapProjection[]; // 6-year projection
}

export interface ContractYear {
  year: number;
  base_salary: number;
  signing_bonus: number;
  cap_hit: number;
}

export interface PlayerCapData {
  player_id: string;
  full_name: string;
  position: string;
  overall: number;
  age: number;
  cap_hit: number;              // This year's cap hit
  years_remaining: number;
  dead_money: number;           // If cut today
  cut_savings: number;          // cap_hit - dead_money
  contract_years: ContractYear[];
}

export interface TeamCapPlayers {
  team_abbr: string;
  top_earners: PlayerCapData[];
  expiring: PlayerCapData[];
  cuttable: PlayerCapData[];
}

// === Helper Functions ===

export function getOverallColor(overall: number): string {
  if (overall >= 90) return '#22c55e'; // Green - Elite
  if (overall >= 80) return '#84cc16'; // Lime - Star
  if (overall >= 70) return '#eab308'; // Yellow - Starter
  if (overall >= 60) return '#f97316'; // Orange - Backup
  return '#ef4444'; // Red - Developmental
}

export function getOverallLabel(overall: number): string {
  if (overall >= 90) return 'Elite';
  if (overall >= 80) return 'Star';
  if (overall >= 70) return 'Starter';
  if (overall >= 60) return 'Backup';
  return 'Developmental';
}
