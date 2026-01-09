/**
 * Player Statistics Types
 *
 * Position-specific stat interfaces for game, season, and career statistics.
 * Following FOF9 patterns: compact view shows essential stats, full view shows all.
 */

// === Position-Specific Season Stats ===

export interface PassingSeasonStats {
  attempts: number;
  completions: number;
  yards: number;
  touchdowns: number;
  interceptions: number;
  sacks: number;
  sack_yards_lost: number;
  longest: number;
  // Derived
  completion_pct: number;
  yards_per_attempt: number;
  passer_rating: number;
}

export interface RushingSeasonStats {
  attempts: number;
  yards: number;
  touchdowns: number;
  fumbles: number;
  fumbles_lost: number;
  longest: number;
  first_downs: number;
  // Derived
  yards_per_carry: number;
}

export interface ReceivingSeasonStats {
  targets: number;
  receptions: number;
  yards: number;
  touchdowns: number;
  drops: number;
  longest: number;
  first_downs: number;
  // Derived
  yards_per_reception: number;
  catch_rate: number;
}

export interface BlockingSeasonStats {
  snaps: number;
  sacks_allowed: number;
  pressures_allowed: number;
  penalties: number;
  pancakes: number;
  // Grades (0-100)
  pass_block_grade: number;
  run_block_grade: number;
}

export interface DefensiveSeasonStats {
  tackles: number;
  tackles_solo: number;
  tackles_assisted: number;
  tackles_for_loss: number;
  sacks: number;
  qb_hits: number;
  interceptions: number;
  interception_yards: number;
  interception_tds: number;
  passes_defended: number;
  forced_fumbles: number;
  fumble_recoveries: number;
  safeties: number;
}

export interface KickingSeasonStats {
  // Field goals
  fg_attempts: number;
  fg_made: number;
  fg_long: number;
  fg_pct: number;
  // Extra points
  xp_attempts: number;
  xp_made: number;
  xp_pct: number;
  // Points
  points: number;
}

export interface PuntingSeasonStats {
  punts: number;
  punt_yards: number;
  punt_avg: number;
  punt_long: number;
  punts_inside_20: number;
  touchbacks: number;
}

// === Season Stats Row (one year) ===

export interface PlayerSeasonRow {
  season: number;
  team_abbr: string;
  games_played: number;
  games_started: number;

  // Position-specific (only populated for relevant positions)
  passing?: PassingSeasonStats;
  rushing?: RushingSeasonStats;
  receiving?: ReceivingSeasonStats;
  blocking?: BlockingSeasonStats;
  defense?: DefensiveSeasonStats;
  kicking?: KickingSeasonStats;
  punting?: PuntingSeasonStats;
}

// === Career Stats ===

export interface CareerHighs {
  // Game highs
  passing_yards_game?: number;
  passing_tds_game?: number;
  rushing_yards_game?: number;
  rushing_tds_game?: number;
  receiving_yards_game?: number;
  receptions_game?: number;
  receiving_tds_game?: number;
  tackles_game?: number;
  sacks_game?: number;

  // Season highs
  passing_yards_season?: number;
  passing_tds_season?: number;
  passer_rating_season?: number;
  rushing_yards_season?: number;
  rushing_tds_season?: number;
  receiving_yards_season?: number;
  receptions_season?: number;
  receiving_tds_season?: number;
  sacks_season?: number;
  interceptions_season?: number;
}

export interface PlayerCareerStats {
  player_id: string;
  player_name: string;
  position: string;
  seasons: PlayerSeasonRow[];
  career_totals: PlayerSeasonRow;
  career_highs: CareerHighs;
}

// === League Leaders ===

export interface LeagueLeader {
  rank: number;
  player_id: string;
  player_name: string;
  team_abbr: string;
  position: string;
  value: number;
  games_played: number;
}

export interface LeagueLeadersCategory {
  category: StatCategory;
  stat: string;
  stat_label: string;
  leaders: LeagueLeader[];
}

export type StatCategory = 'passing' | 'rushing' | 'receiving' | 'defense' | 'kicking';

// === Stat Column Definition ===

export interface StatColumnDef {
  key: string;           // Dot notation path, e.g., 'passing.yards'
  label: string;         // Full label for headers
  abbr: string;          // 3-4 char abbreviation for compact display
  width: number;         // Pixel width
  align: 'left' | 'right';
  format?: 'number' | 'pct' | 'decimal';
  decimals?: number;
}

// === Position Groups for Stats ===

export type StatPositionGroup =
  | 'QB'
  | 'RB'
  | 'WR'
  | 'TE'
  | 'OL'
  | 'DL'
  | 'LB'
  | 'DB'
  | 'K'
  | 'P';

// Map specific positions to stat groups
export const POSITION_TO_STAT_GROUP: Record<string, StatPositionGroup> = {
  QB: 'QB',
  RB: 'RB',
  FB: 'RB',
  WR: 'WR',
  TE: 'TE',
  LT: 'OL',
  LG: 'OL',
  C: 'OL',
  RG: 'OL',
  RT: 'OL',
  DE: 'DL',
  DT: 'DL',
  NT: 'DL',
  MLB: 'LB',
  ILB: 'LB',
  OLB: 'LB',
  CB: 'DB',
  FS: 'DB',
  SS: 'DB',
  K: 'K',
  P: 'P',
};

// === Team Stats ===

export interface TeamSeasonStats {
  team_abbr: string;
  team_name: string;

  // Offense
  points_per_game: number;
  total_yards_per_game: number;
  passing_yards_per_game: number;
  rushing_yards_per_game: number;
  turnovers: number;

  // Defense
  points_allowed_per_game: number;
  yards_allowed_per_game: number;
  passing_yards_allowed_per_game: number;
  rushing_yards_allowed_per_game: number;
  takeaways: number;
  sacks: number;

  // Rankings (1-32)
  offense_rank: number;
  defense_rank: number;
  points_rank: number;
  points_allowed_rank: number;
}
