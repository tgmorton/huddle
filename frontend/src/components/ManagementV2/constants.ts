// ManagementV2 Constants

import {
  Gamepad2,
  Box,
  Zap,
  Target,
  Circle,
  Route,
  GitBranch,
  ClipboardList,
  Settings,
  Eye,
} from 'lucide-react';
import type { ItemType, PaneSize } from './types';

// Size mapping for each item type when OPENED
// Collapsed items always use 'small' (2 cols)
// Small = 2 cols (collapsed), Medium = 4 cols (open), Large = 6 cols (open-wide)
export const TYPE_SIZE: Record<ItemType, PaneSize> = {
  practice: 'medium',
  game: 'medium',
  meeting: 'medium',
  deadline: 'medium',
  decision: 'medium',
  scout: 'large',
  player: 'medium',
  prospect: 'medium',
  contract: 'medium',
  negotiation: 'large',
  auction: 'large',
  news: 'medium',
  stats: 'large', // Full career stats pop-out
};

// Type config with text-based indicators
export const TYPE_CONFIG: Record<ItemType, { abbr: string; label: string }> = {
  practice: { abbr: 'PRC', label: 'Practice' },
  game: { abbr: 'GME', label: 'Game' },
  meeting: { abbr: 'MTG', label: 'Meeting' },
  deadline: { abbr: 'DUE', label: 'Deadline' },
  decision: { abbr: 'DEC', label: 'Decision' },
  scout: { abbr: 'SCT', label: 'Scouting' },
  player: { abbr: 'PLR', label: 'Player' },
  prospect: { abbr: 'PROS', label: 'Prospect' },
  contract: { abbr: 'CTR', label: 'Contract' },
  negotiation: { abbr: 'NGT', label: 'Negotiation' },
  auction: { abbr: 'AUC', label: 'Auction' },
  news: { abbr: 'NEWS', label: 'News' },
  stats: { abbr: 'STAT', label: 'Statistics' },
};

// Navigation groups for app switcher
export const NAV_GROUPS = [
  {
    label: 'Simulation',
    items: [
      { to: '/coach', label: 'Watch Game', icon: Eye },
      { to: '/', label: 'Game', icon: Gamepad2 },
      { to: '/sandbox', label: 'Sandbox', icon: Box },
      { to: '/integrated', label: 'Integrated', icon: Zap },
      { to: '/v2-sim', label: 'V2 Sim', icon: Target },
      { to: '/sim-analyzer', label: 'Analyzer', icon: Settings },
    ]
  },
  {
    label: 'Routes',
    items: [
      { to: '/pocket', label: 'Pocket', icon: Circle },
      { to: '/routes', label: 'Routes', icon: Route },
      { to: '/team-routes', label: 'Team Routes', icon: GitBranch },
    ]
  },
  {
    label: 'Management',
    items: [
      { to: '/manage', label: 'Manage V1', icon: ClipboardList },
      { to: '/admin', label: 'Admin', icon: Settings },
    ]
  }
];

// Panel widths for different views
export const PANEL_WIDTHS: Record<string, number> = {
  personnel: 420,
  transactions: 420,
  finances: 420,
  draft: 420,
  season: 360,
  team: 380,
  week: 320,
  league: 640, // Wider for stats tables
  settings: 300, // Compact settings panel
  history: 480, // Historical simulation browser
};

// === Player Stats Column Definitions ===
// Position-specific columns for stats tables
// Compact: fits in 420px sideview, Full: for 1440px pop-out

import type { StatColumnDef, StatPositionGroup } from '../../types/stats';

// Compact view columns (6-7 columns, fits in sideview)
export const STAT_COLUMNS_COMPACT: Record<StatPositionGroup, StatColumnDef[]> = {
  QB: [
    { key: 'games_played', label: 'Games', abbr: 'G', width: 28, align: 'right' },
    { key: 'passing.completions', label: 'Completions', abbr: 'CMP', width: 40, align: 'right' },
    { key: 'passing.attempts', label: 'Attempts', abbr: 'ATT', width: 40, align: 'right' },
    { key: 'passing.yards', label: 'Yards', abbr: 'YDS', width: 48, align: 'right' },
    { key: 'passing.touchdowns', label: 'Touchdowns', abbr: 'TD', width: 32, align: 'right' },
    { key: 'passing.interceptions', label: 'Interceptions', abbr: 'INT', width: 32, align: 'right' },
    { key: 'passing.passer_rating', label: 'Rating', abbr: 'RTG', width: 44, align: 'right', format: 'decimal', decimals: 1 },
  ],
  RB: [
    { key: 'games_played', label: 'Games', abbr: 'G', width: 28, align: 'right' },
    { key: 'rushing.attempts', label: 'Attempts', abbr: 'ATT', width: 40, align: 'right' },
    { key: 'rushing.yards', label: 'Yards', abbr: 'YDS', width: 48, align: 'right' },
    { key: 'rushing.yards_per_carry', label: 'Average', abbr: 'AVG', width: 40, align: 'right', format: 'decimal', decimals: 1 },
    { key: 'rushing.touchdowns', label: 'Touchdowns', abbr: 'TD', width: 32, align: 'right' },
    { key: 'rushing.fumbles_lost', label: 'Fumbles', abbr: 'FUM', width: 32, align: 'right' },
  ],
  WR: [
    { key: 'games_played', label: 'Games', abbr: 'G', width: 28, align: 'right' },
    { key: 'receiving.receptions', label: 'Receptions', abbr: 'REC', width: 40, align: 'right' },
    { key: 'receiving.targets', label: 'Targets', abbr: 'TGT', width: 40, align: 'right' },
    { key: 'receiving.yards', label: 'Yards', abbr: 'YDS', width: 48, align: 'right' },
    { key: 'receiving.yards_per_reception', label: 'Average', abbr: 'AVG', width: 40, align: 'right', format: 'decimal', decimals: 1 },
    { key: 'receiving.touchdowns', label: 'Touchdowns', abbr: 'TD', width: 32, align: 'right' },
  ],
  TE: [
    { key: 'games_played', label: 'Games', abbr: 'G', width: 28, align: 'right' },
    { key: 'receiving.receptions', label: 'Receptions', abbr: 'REC', width: 40, align: 'right' },
    { key: 'receiving.yards', label: 'Yards', abbr: 'YDS', width: 48, align: 'right' },
    { key: 'receiving.touchdowns', label: 'Touchdowns', abbr: 'TD', width: 32, align: 'right' },
    { key: 'blocking.pass_block_grade', label: 'Pass Block', abbr: 'PBK', width: 36, align: 'right' },
  ],
  OL: [
    { key: 'games_started', label: 'Starts', abbr: 'GS', width: 28, align: 'right' },
    { key: 'blocking.snaps', label: 'Snaps', abbr: 'SNP', width: 48, align: 'right' },
    { key: 'blocking.sacks_allowed', label: 'Sacks', abbr: 'SK', width: 32, align: 'right' },
    { key: 'blocking.penalties', label: 'Penalties', abbr: 'PEN', width: 36, align: 'right' },
    { key: 'blocking.pass_block_grade', label: 'Pass Block', abbr: 'PBK', width: 36, align: 'right' },
    { key: 'blocking.run_block_grade', label: 'Run Block', abbr: 'RBK', width: 36, align: 'right' },
  ],
  DL: [
    { key: 'games_played', label: 'Games', abbr: 'G', width: 28, align: 'right' },
    { key: 'defense.tackles', label: 'Tackles', abbr: 'TKL', width: 40, align: 'right' },
    { key: 'defense.tackles_for_loss', label: 'TFL', abbr: 'TFL', width: 36, align: 'right' },
    { key: 'defense.sacks', label: 'Sacks', abbr: 'SCK', width: 36, align: 'right', format: 'decimal', decimals: 1 },
    { key: 'defense.qb_hits', label: 'QB Hits', abbr: 'QBH', width: 36, align: 'right' },
    { key: 'defense.forced_fumbles', label: 'FF', abbr: 'FF', width: 28, align: 'right' },
  ],
  LB: [
    { key: 'games_played', label: 'Games', abbr: 'G', width: 28, align: 'right' },
    { key: 'defense.tackles', label: 'Tackles', abbr: 'TKL', width: 40, align: 'right' },
    { key: 'defense.tackles_for_loss', label: 'TFL', abbr: 'TFL', width: 36, align: 'right' },
    { key: 'defense.sacks', label: 'Sacks', abbr: 'SCK', width: 36, align: 'right', format: 'decimal', decimals: 1 },
    { key: 'defense.interceptions', label: 'INT', abbr: 'INT', width: 32, align: 'right' },
    { key: 'defense.passes_defended', label: 'PD', abbr: 'PD', width: 32, align: 'right' },
  ],
  DB: [
    { key: 'games_played', label: 'Games', abbr: 'G', width: 28, align: 'right' },
    { key: 'defense.tackles', label: 'Tackles', abbr: 'TKL', width: 40, align: 'right' },
    { key: 'defense.interceptions', label: 'INT', abbr: 'INT', width: 32, align: 'right' },
    { key: 'defense.passes_defended', label: 'PD', abbr: 'PD', width: 36, align: 'right' },
    { key: 'defense.forced_fumbles', label: 'FF', abbr: 'FF', width: 28, align: 'right' },
  ],
  K: [
    { key: 'games_played', label: 'Games', abbr: 'G', width: 28, align: 'right' },
    { key: 'kicking.fg_made', label: 'FG Made', abbr: 'FGM', width: 40, align: 'right' },
    { key: 'kicking.fg_attempts', label: 'FG Att', abbr: 'FGA', width: 40, align: 'right' },
    { key: 'kicking.fg_pct', label: 'FG%', abbr: 'FG%', width: 44, align: 'right', format: 'pct' },
    { key: 'kicking.fg_long', label: 'Long', abbr: 'LNG', width: 36, align: 'right' },
  ],
  P: [
    { key: 'games_played', label: 'Games', abbr: 'G', width: 28, align: 'right' },
    { key: 'punting.punts', label: 'Punts', abbr: 'PNT', width: 40, align: 'right' },
    { key: 'punting.punt_yards', label: 'Yards', abbr: 'YDS', width: 48, align: 'right' },
    { key: 'punting.punt_avg', label: 'Average', abbr: 'AVG', width: 40, align: 'right', format: 'decimal', decimals: 1 },
    { key: 'punting.punts_inside_20', label: 'In20', abbr: 'I20', width: 36, align: 'right' },
  ],
};

// Full view columns (extended for 1440px pop-out)
export const STAT_COLUMNS_FULL: Record<StatPositionGroup, StatColumnDef[]> = {
  QB: [
    { key: 'season', label: 'Year', abbr: 'YR', width: 48, align: 'left' },
    { key: 'team_abbr', label: 'Team', abbr: 'TM', width: 48, align: 'left' },
    { key: 'games_played', label: 'G', abbr: 'G', width: 28, align: 'right' },
    { key: 'games_started', label: 'GS', abbr: 'GS', width: 28, align: 'right' },
    { key: 'passing.completions', label: 'CMP', abbr: 'CMP', width: 44, align: 'right' },
    { key: 'passing.attempts', label: 'ATT', abbr: 'ATT', width: 44, align: 'right' },
    { key: 'passing.completion_pct', label: 'CMP%', abbr: 'CMP%', width: 52, align: 'right', format: 'pct' },
    { key: 'passing.yards', label: 'YDS', abbr: 'YDS', width: 52, align: 'right' },
    { key: 'passing.yards_per_attempt', label: 'Y/A', abbr: 'Y/A', width: 44, align: 'right', format: 'decimal', decimals: 1 },
    { key: 'passing.touchdowns', label: 'TD', abbr: 'TD', width: 36, align: 'right' },
    { key: 'passing.interceptions', label: 'INT', abbr: 'INT', width: 36, align: 'right' },
    { key: 'passing.sacks', label: 'SK', abbr: 'SK', width: 36, align: 'right' },
    { key: 'passing.longest', label: 'LNG', abbr: 'LNG', width: 40, align: 'right' },
    { key: 'passing.passer_rating', label: 'RTG', abbr: 'RTG', width: 52, align: 'right', format: 'decimal', decimals: 1 },
  ],
  RB: [
    { key: 'season', label: 'Year', abbr: 'YR', width: 48, align: 'left' },
    { key: 'team_abbr', label: 'Team', abbr: 'TM', width: 48, align: 'left' },
    { key: 'games_played', label: 'G', abbr: 'G', width: 28, align: 'right' },
    { key: 'games_started', label: 'GS', abbr: 'GS', width: 28, align: 'right' },
    { key: 'rushing.attempts', label: 'ATT', abbr: 'ATT', width: 44, align: 'right' },
    { key: 'rushing.yards', label: 'YDS', abbr: 'YDS', width: 52, align: 'right' },
    { key: 'rushing.yards_per_carry', label: 'AVG', abbr: 'AVG', width: 44, align: 'right', format: 'decimal', decimals: 1 },
    { key: 'rushing.touchdowns', label: 'TD', abbr: 'TD', width: 36, align: 'right' },
    { key: 'rushing.longest', label: 'LNG', abbr: 'LNG', width: 40, align: 'right' },
    { key: 'rushing.fumbles', label: 'FUM', abbr: 'FUM', width: 36, align: 'right' },
    { key: 'receiving.receptions', label: 'REC', abbr: 'REC', width: 40, align: 'right' },
    { key: 'receiving.yards', label: 'RYDS', abbr: 'RYDS', width: 48, align: 'right' },
    { key: 'receiving.touchdowns', label: 'RTD', abbr: 'RTD', width: 36, align: 'right' },
  ],
  WR: [
    { key: 'season', label: 'Year', abbr: 'YR', width: 48, align: 'left' },
    { key: 'team_abbr', label: 'Team', abbr: 'TM', width: 48, align: 'left' },
    { key: 'games_played', label: 'G', abbr: 'G', width: 28, align: 'right' },
    { key: 'games_started', label: 'GS', abbr: 'GS', width: 28, align: 'right' },
    { key: 'receiving.targets', label: 'TGT', abbr: 'TGT', width: 44, align: 'right' },
    { key: 'receiving.receptions', label: 'REC', abbr: 'REC', width: 44, align: 'right' },
    { key: 'receiving.catch_rate', label: 'CT%', abbr: 'CT%', width: 48, align: 'right', format: 'pct' },
    { key: 'receiving.yards', label: 'YDS', abbr: 'YDS', width: 52, align: 'right' },
    { key: 'receiving.yards_per_reception', label: 'AVG', abbr: 'AVG', width: 44, align: 'right', format: 'decimal', decimals: 1 },
    { key: 'receiving.touchdowns', label: 'TD', abbr: 'TD', width: 36, align: 'right' },
    { key: 'receiving.longest', label: 'LNG', abbr: 'LNG', width: 40, align: 'right' },
    { key: 'receiving.first_downs', label: '1D', abbr: '1D', width: 36, align: 'right' },
  ],
  TE: [
    { key: 'season', label: 'Year', abbr: 'YR', width: 48, align: 'left' },
    { key: 'team_abbr', label: 'Team', abbr: 'TM', width: 48, align: 'left' },
    { key: 'games_played', label: 'G', abbr: 'G', width: 28, align: 'right' },
    { key: 'receiving.targets', label: 'TGT', abbr: 'TGT', width: 44, align: 'right' },
    { key: 'receiving.receptions', label: 'REC', abbr: 'REC', width: 44, align: 'right' },
    { key: 'receiving.yards', label: 'YDS', abbr: 'YDS', width: 52, align: 'right' },
    { key: 'receiving.touchdowns', label: 'TD', abbr: 'TD', width: 36, align: 'right' },
    { key: 'blocking.pass_block_grade', label: 'PBK', abbr: 'PBK', width: 40, align: 'right' },
    { key: 'blocking.run_block_grade', label: 'RBK', abbr: 'RBK', width: 40, align: 'right' },
  ],
  OL: [
    { key: 'season', label: 'Year', abbr: 'YR', width: 48, align: 'left' },
    { key: 'team_abbr', label: 'Team', abbr: 'TM', width: 48, align: 'left' },
    { key: 'games_played', label: 'G', abbr: 'G', width: 28, align: 'right' },
    { key: 'games_started', label: 'GS', abbr: 'GS', width: 28, align: 'right' },
    { key: 'blocking.snaps', label: 'SNP', abbr: 'SNP', width: 52, align: 'right' },
    { key: 'blocking.sacks_allowed', label: 'SK', abbr: 'SK', width: 36, align: 'right' },
    { key: 'blocking.pressures_allowed', label: 'PRES', abbr: 'PRES', width: 44, align: 'right' },
    { key: 'blocking.penalties', label: 'PEN', abbr: 'PEN', width: 40, align: 'right' },
    { key: 'blocking.pancakes', label: 'PAN', abbr: 'PAN', width: 40, align: 'right' },
    { key: 'blocking.pass_block_grade', label: 'PBK', abbr: 'PBK', width: 40, align: 'right' },
    { key: 'blocking.run_block_grade', label: 'RBK', abbr: 'RBK', width: 40, align: 'right' },
  ],
  DL: [
    { key: 'season', label: 'Year', abbr: 'YR', width: 48, align: 'left' },
    { key: 'team_abbr', label: 'Team', abbr: 'TM', width: 48, align: 'left' },
    { key: 'games_played', label: 'G', abbr: 'G', width: 28, align: 'right' },
    { key: 'defense.tackles', label: 'TKL', abbr: 'TKL', width: 44, align: 'right' },
    { key: 'defense.tackles_solo', label: 'SOLO', abbr: 'SOLO', width: 44, align: 'right' },
    { key: 'defense.tackles_for_loss', label: 'TFL', abbr: 'TFL', width: 40, align: 'right' },
    { key: 'defense.sacks', label: 'SCK', abbr: 'SCK', width: 40, align: 'right', format: 'decimal', decimals: 1 },
    { key: 'defense.qb_hits', label: 'QBH', abbr: 'QBH', width: 40, align: 'right' },
    { key: 'defense.forced_fumbles', label: 'FF', abbr: 'FF', width: 32, align: 'right' },
    { key: 'defense.fumble_recoveries', label: 'FR', abbr: 'FR', width: 32, align: 'right' },
  ],
  LB: [
    { key: 'season', label: 'Year', abbr: 'YR', width: 48, align: 'left' },
    { key: 'team_abbr', label: 'Team', abbr: 'TM', width: 48, align: 'left' },
    { key: 'games_played', label: 'G', abbr: 'G', width: 28, align: 'right' },
    { key: 'defense.tackles', label: 'TKL', abbr: 'TKL', width: 44, align: 'right' },
    { key: 'defense.tackles_solo', label: 'SOLO', abbr: 'SOLO', width: 44, align: 'right' },
    { key: 'defense.tackles_for_loss', label: 'TFL', abbr: 'TFL', width: 40, align: 'right' },
    { key: 'defense.sacks', label: 'SCK', abbr: 'SCK', width: 40, align: 'right', format: 'decimal', decimals: 1 },
    { key: 'defense.interceptions', label: 'INT', abbr: 'INT', width: 36, align: 'right' },
    { key: 'defense.passes_defended', label: 'PD', abbr: 'PD', width: 36, align: 'right' },
    { key: 'defense.forced_fumbles', label: 'FF', abbr: 'FF', width: 32, align: 'right' },
  ],
  DB: [
    { key: 'season', label: 'Year', abbr: 'YR', width: 48, align: 'left' },
    { key: 'team_abbr', label: 'Team', abbr: 'TM', width: 48, align: 'left' },
    { key: 'games_played', label: 'G', abbr: 'G', width: 28, align: 'right' },
    { key: 'defense.tackles', label: 'TKL', abbr: 'TKL', width: 44, align: 'right' },
    { key: 'defense.interceptions', label: 'INT', abbr: 'INT', width: 36, align: 'right' },
    { key: 'defense.interception_yards', label: 'IYDS', abbr: 'IYDS', width: 48, align: 'right' },
    { key: 'defense.interception_tds', label: 'ITD', abbr: 'ITD', width: 36, align: 'right' },
    { key: 'defense.passes_defended', label: 'PD', abbr: 'PD', width: 36, align: 'right' },
    { key: 'defense.forced_fumbles', label: 'FF', abbr: 'FF', width: 32, align: 'right' },
  ],
  K: [
    { key: 'season', label: 'Year', abbr: 'YR', width: 48, align: 'left' },
    { key: 'team_abbr', label: 'Team', abbr: 'TM', width: 48, align: 'left' },
    { key: 'games_played', label: 'G', abbr: 'G', width: 28, align: 'right' },
    { key: 'kicking.fg_made', label: 'FGM', abbr: 'FGM', width: 44, align: 'right' },
    { key: 'kicking.fg_attempts', label: 'FGA', abbr: 'FGA', width: 44, align: 'right' },
    { key: 'kicking.fg_pct', label: 'FG%', abbr: 'FG%', width: 48, align: 'right', format: 'pct' },
    { key: 'kicking.fg_long', label: 'LNG', abbr: 'LNG', width: 40, align: 'right' },
    { key: 'kicking.xp_made', label: 'XPM', abbr: 'XPM', width: 44, align: 'right' },
    { key: 'kicking.xp_attempts', label: 'XPA', abbr: 'XPA', width: 44, align: 'right' },
    { key: 'kicking.points', label: 'PTS', abbr: 'PTS', width: 44, align: 'right' },
  ],
  P: [
    { key: 'season', label: 'Year', abbr: 'YR', width: 48, align: 'left' },
    { key: 'team_abbr', label: 'Team', abbr: 'TM', width: 48, align: 'left' },
    { key: 'games_played', label: 'G', abbr: 'G', width: 28, align: 'right' },
    { key: 'punting.punts', label: 'PNT', abbr: 'PNT', width: 44, align: 'right' },
    { key: 'punting.punt_yards', label: 'YDS', abbr: 'YDS', width: 52, align: 'right' },
    { key: 'punting.punt_avg', label: 'AVG', abbr: 'AVG', width: 44, align: 'right', format: 'decimal', decimals: 1 },
    { key: 'punting.punt_long', label: 'LNG', abbr: 'LNG', width: 40, align: 'right' },
    { key: 'punting.punts_inside_20', label: 'I20', abbr: 'I20', width: 40, align: 'right' },
    { key: 'punting.touchbacks', label: 'TB', abbr: 'TB', width: 36, align: 'right' },
  ],
};
