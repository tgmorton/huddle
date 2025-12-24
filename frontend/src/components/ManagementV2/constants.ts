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
  news: 'medium',
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
  news: { abbr: 'NEWS', label: 'News' },
};

// Navigation groups for app switcher
export const NAV_GROUPS = [
  {
    label: 'Simulation',
    items: [
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
};
