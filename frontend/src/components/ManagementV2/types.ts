// ManagementV2 Types

export type WeekPhase = 'recovery' | 'practice' | 'prep' | 'gameday';
export type ItemType = 'practice' | 'game' | 'meeting' | 'deadline' | 'decision' | 'scout' | 'player' | 'prospect' | 'news';
export type EventType = 'injury' | 'trade_offer' | 'media' | 'contract_demand' | 'morale';
export type PaneSize = 'small' | 'medium' | 'large';

export type LeftPanelView =
  | 'personnel'      // Roster, Depth Chart, Coaches
  | 'transactions'   // Free Agents, Trades, Waivers
  | 'finances'       // Cap, Contracts
  | 'draft'          // Board, Scouts, Prospects
  | 'season'         // Schedule, Standings, Playoffs
  | 'team'           // Strategy, Chemistry, Front Office
  | 'drawer'         // Archived workspace items
  | 'week'           // Weekly gameplay loop view
  | null;

export type WorkspaceItemStatus = 'active' | 'pinned' | 'archived';

export interface WorkspaceItem {
  id: string;
  type: ItemType;
  title: string;
  subtitle?: string;
  detail?: string;
  timeLeft?: string;
  isOpen: boolean;
  playerId?: string;
  eventId?: string;     // for event-type items (practice, game, etc.)
  eventPayload?: Record<string, unknown>;  // payload from the event for pane data
  status: WorkspaceItemStatus;
  archivedAt?: number;  // timestamp for archived items
  note?: string;        // user note for archived items
}

export interface AgendaItem {
  id: string;
  type: ItemType;
  title: string;
  subtitle?: string;
  detail?: string;
  timeLeft?: string;
  action?: string;
  actionSecondary?: string;
  completed?: boolean;
}

export interface NewsItem {
  id: string;
  text: string;
  isBreaking?: boolean;
}

export interface GameEvent {
  id: string;
  type: EventType;
  title: string;
  subtitle: string;
  description: string;
  severity: 'info' | 'warning' | 'critical';
  options: { label: string; variant: 'primary' | 'secondary' | 'danger' }[];
}

export interface Player {
  id: string;
  name: string;
  position: string;
  number: number;
  age: number;
  experience: string;
  overall: number;
  salary: string;
  contractYears: number;
  morale: 'high' | 'neutral' | 'low';
  traits: string[];
}

export type RosterView = { type: 'list' } | { type: 'player'; playerId: string };

export interface PlayerStats {
  id: string;
  name: string;
  pos: string;
  ovr: number;
  depth?: number; // 1 = starter, 2 = backup, etc.
  attrs: Record<string, number>; // position-relevant attributes
}
