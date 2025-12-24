/**
 * REST API client for Management/Franchise endpoints
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export interface FranchiseSession {
  franchise_id: string;
  message: string;
}

export interface CreateFranchiseRequest {
  team_id: string;
  team_name: string;
  season_year?: number;
  start_phase?: string;
}

export interface ActiveSession {
  id: string;
  team_abbr?: string;
}

export interface FranchiseState {
  id: string;
  league_id: string;
  player_team_id: string;
  calendar: unknown;
  events: unknown;
  clipboard: unknown;
  ticker: unknown;
}

// Scouting/Draft types
export interface CombineMeasurables {
  forty_yard_dash: number | null;
  forty_percentile: number | null;
  bench_press_reps: number | null;
  bench_percentile: number | null;
  vertical_jump: number | null;
  vertical_percentile: number | null;
  broad_jump: number | null;
  broad_percentile: number | null;
}

export interface ScoutEstimate {
  name: string;
  projected_value: number;
  accuracy: 'low' | 'medium' | 'high';
  min_estimate: number;
  max_estimate: number;
  grade: string;
}

export interface ProspectData {
  player_id: string;
  name: string;
  position: string;
  college: string;
  age: number;
  height: string;
  weight: number;
  scouted_percentage: number;
  interviewed: boolean;
  private_workout: boolean;
  combine: CombineMeasurables;
  scout_estimates: ScoutEstimate[];
  overall_projection: number;
  projected_round: number | null;
}

export interface DraftProspectsResponse {
  count: number;
  prospects: ProspectData[];
}

// Portrait generation status
export interface PortraitBatchStatus {
  league_id: string;
  total: number;
  completed: number;
  failed: number;
  pending: number;
  status: 'pending' | 'processing' | 'complete' | 'failed';
}

// Drawer types
export type DrawerItemType = 'player' | 'prospect' | 'news' | 'game';

export interface DrawerItem {
  id: string;
  type: DrawerItemType;
  ref_id: string;
  note: string | null;
  archived_at: string;
  title: string;
  subtitle: string | null;
}

export interface DrawerResponse {
  items: DrawerItem[];
  count: number;
}

export interface AddDrawerItemRequest {
  type: DrawerItemType;
  ref_id: string;
  note?: string;
}

// Draft Board types
export interface BoardEntry {
  prospect_id: string;
  rank: number;
  tier: number;  // 1=Elite, 2=Great, 3=Good, 4=Solid, 5=Flier
  notes: string;
  name: string;
  position: string;
  college: string | null;
  overall: number;
}

export interface DraftBoardResponse {
  entries: BoardEntry[];
  count: number;
}

export interface AddToBoardRequest {
  prospect_id: string;
  tier?: number;
}

export interface UpdateBoardEntryRequest {
  tier?: number;
  notes?: string;
}

// Day advance response
export interface CalendarState {
  season_year: number;
  current_date: string;
  phase: string;
  current_week: number;
  speed: string;
  is_paused: boolean;
  day_name: string;
  time_display: string;
  date_display: string;
  week_display: string;
}

export interface ManagementEventData {
  id: string;
  event_type: string;
  category: string;
  priority: string;
  title: string;
  description: string;
  icon: string;
  display_mode: string;
  created_at: string;
  scheduled_for: string | null;
  deadline: string | null;
  scheduled_week: number | null;
  scheduled_day: number | null;
  arc_id: string | null;
  status: string;
  auto_pause: boolean;
  requires_attention: boolean;
  can_dismiss: boolean;
  can_delegate: boolean;
  team_id: string | null;
  player_ids: string[];
  payload: Record<string, unknown>;
  is_urgent: boolean;
}

export interface DayAdvanceResponse {
  calendar: CalendarState;
  day_events: ManagementEventData[];
  event_count: number;
}

// Week Journal types
export type JournalCategory = 'practice' | 'conversation' | 'intel' | 'injury' | 'transaction';

export interface WeekJournalEntry {
  id: string;
  day: number;
  category: JournalCategory;
  title: string;
  effect: string;
  detail?: string;
  player?: {
    name: string;
    position: string;
    number: number;
  };
}

export interface WeekJournalResponse {
  week: number;
  entries: WeekJournalEntry[];
}

export interface AddJournalEntryRequest {
  category: JournalCategory;
  title: string;
  effect: string;
  detail?: string;
  player?: {
    name: string;
    position: string;
    number: number;
  };
}

// Playbook Mastery types
export type MasteryStatus = 'unlearned' | 'learned' | 'mastered';

export interface PlayMasteryEntry {
  play_id: string;
  play_name: string;
  status: MasteryStatus;
  progress: number;
  reps: number;
}

export interface PlayerPlaybook {
  player_id: string;
  name: string;
  position: string;
  depth?: number;
  plays: PlayMasteryEntry[];
  learned_count: number;
  mastered_count: number;
  total_plays: number;
}

export interface PlaybookMasteryResponse {
  team_abbr: string;
  players: PlayerPlaybook[];
}

// Development/Potentials types
export interface AttributePotential {
  name: string;
  current: number;
  potential: number;
  growth_room: number;
}

export interface PlayerDevelopment {
  player_id: string;
  name: string;
  position: string;
  overall: number;
  overall_potential: number;
  potentials: AttributePotential[];
}

export interface DevelopmentResponse {
  team_abbr: string;
  players: PlayerDevelopment[];
}

// Weekly Development (growth this week)
export interface PlayerWeeklyGain {
  player_id: string;
  name: string;
  position: string;
  gains: Record<string, number>;
}

export interface WeeklyDevelopmentResponse {
  week: number;
  players: PlayerWeeklyGain[];
}

// Practice execution types
export interface RunPracticeRequest {
  event_id: string;
  playbook: number;
  development: number;
  game_prep: number;
  intensity?: string;
}

export interface PlaybookPracticeStats {
  players_practiced: number;
  total_reps_given: number;
  tier_advancements: number;
  plays_practiced: number;
}

export interface DevelopmentPracticeStats {
  players_developed: number;
  total_points_gained: number;
  attributes_improved: Record<string, number>;
}

export interface GamePrepStats {
  opponent: string | null;
  prep_level: number;
  scheme_bonus: number;
  execution_bonus: number;
}

export interface PracticeResults {
  success: boolean;
  error?: string;
  duration_minutes: number;
  playbook_stats: PlaybookPracticeStats;
  development_stats: DevelopmentPracticeStats;
  game_prep_stats: GamePrepStats;
}

// Game Simulation types
export interface GameStats {
  passing_yards: number;
  rushing_yards: number;
  total_yards: number;
  turnovers: number;
  time_of_possession: string;
  third_down_pct: number;
  sacks: number;
}

export interface GameMVP {
  player_id: string | null;
  name: string;
  position: string;
  stat_line: string;
}

export interface GameResult {
  success: boolean;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  won: boolean;
  is_home: boolean;
  week: number;
  user_stats: GameStats;
  opponent_stats: GameStats;
  mvp: GameMVP | null;
}

export class ApiError extends Error {
  status: number;
  statusText: string;

  constructor(status: number, statusText: string, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, response.statusText, errorData.detail || 'Request failed');
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const managementApi = {
  // Franchise lifecycle
  createFranchise: (data: CreateFranchiseRequest): Promise<FranchiseSession> =>
    request('/management/franchise', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getFranchise: (id: string): Promise<FranchiseState> =>
    request(`/management/franchise/${id}`),

  deleteFranchise: (id: string): Promise<void> =>
    request(`/management/franchise/${id}`, { method: 'DELETE' }),

  listSessions: (): Promise<{ active_sessions: string[]; count: number }> =>
    request('/management/sessions'),

  // Time controls (REST fallback)
  pause: (franchiseId: string): Promise<void> =>
    request(`/management/franchise/${franchiseId}/pause`, { method: 'POST' }),

  play: (franchiseId: string, speed?: string): Promise<void> =>
    request(`/management/franchise/${franchiseId}/play`, {
      method: 'POST',
      body: JSON.stringify({ speed }),
    }),

  setSpeed: (franchiseId: string, speed: string): Promise<void> =>
    request(`/management/franchise/${franchiseId}/speed`, {
      method: 'POST',
      body: JSON.stringify({ speed }),
    }),

  // Calendar
  getCalendar: (franchiseId: string): Promise<unknown> =>
    request(`/management/franchise/${franchiseId}/calendar`),

  // Time advancement
  advanceDay: (franchiseId: string): Promise<DayAdvanceResponse> =>
    request(`/management/franchise/${franchiseId}/advance-day`, { method: 'POST' }),

  advanceToGame: (franchiseId: string): Promise<void> =>
    request(`/management/franchise/${franchiseId}/advance-to-game`, { method: 'POST' }),

  // Events
  getEvents: (franchiseId: string): Promise<unknown> =>
    request(`/management/franchise/${franchiseId}/events`),

  attendEvent: (franchiseId: string, eventId: string): Promise<void> =>
    request(`/management/franchise/${franchiseId}/events/attend`, {
      method: 'POST',
      body: JSON.stringify({ event_id: eventId }),
    }),

  dismissEvent: (franchiseId: string, eventId: string): Promise<void> =>
    request(`/management/franchise/${franchiseId}/events/dismiss`, {
      method: 'POST',
      body: JSON.stringify({ event_id: eventId }),
    }),

  // Ticker
  getTicker: (franchiseId: string): Promise<unknown> =>
    request(`/management/franchise/${franchiseId}/ticker`),

  // Draft
  getDraftProspects: (franchiseId: string): Promise<DraftProspectsResponse> =>
    request(`/management/franchise/${franchiseId}/draft-prospects`),

  getProspect: (franchiseId: string, prospectId: string): Promise<ProspectData> =>
    request(`/management/franchise/${franchiseId}/draft-prospects/${prospectId}`),

  // Portraits
  getPortraitBatchStatus: (leagueId: string): Promise<PortraitBatchStatus> =>
    request(`/portraits/batch/status/${leagueId}`),

  // Drawer
  getDrawer: (franchiseId: string): Promise<DrawerResponse> =>
    request(`/management/franchise/${franchiseId}/drawer`),

  addDrawerItem: (franchiseId: string, data: AddDrawerItemRequest): Promise<DrawerItem> =>
    request(`/management/franchise/${franchiseId}/drawer`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deleteDrawerItem: (franchiseId: string, itemId: string): Promise<void> =>
    request(`/management/franchise/${franchiseId}/drawer/${itemId}`, {
      method: 'DELETE',
    }),

  updateDrawerItemNote: (franchiseId: string, itemId: string, note: string | null): Promise<DrawerItem> =>
    request(`/management/franchise/${franchiseId}/drawer/${itemId}`, {
      method: 'PATCH',
      body: JSON.stringify({ note }),
    }),

  // Draft Board
  getDraftBoard: (franchiseId: string): Promise<DraftBoardResponse> =>
    request(`/management/franchise/${franchiseId}/draft-board`),

  addToBoard: (franchiseId: string, prospectId: string, tier?: number): Promise<BoardEntry> =>
    request(`/management/franchise/${franchiseId}/draft-board`, {
      method: 'POST',
      body: JSON.stringify({ prospect_id: prospectId, tier: tier ?? 3 }),
    }),

  removeFromBoard: (franchiseId: string, prospectId: string): Promise<void> =>
    request(`/management/franchise/${franchiseId}/draft-board/${prospectId}`, {
      method: 'DELETE',
    }),

  updateBoardEntry: (franchiseId: string, prospectId: string, data: UpdateBoardEntryRequest): Promise<BoardEntry> =>
    request(`/management/franchise/${franchiseId}/draft-board/${prospectId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  reorderBoardEntry: (franchiseId: string, prospectId: string, newRank: number): Promise<void> =>
    request(`/management/franchise/${franchiseId}/draft-board/${prospectId}/reorder`, {
      method: 'POST',
      body: JSON.stringify({ new_rank: newRank }),
    }),

  isOnBoard: (franchiseId: string, prospectId: string): Promise<{ prospect_id: string; on_board: boolean }> =>
    request(`/management/franchise/${franchiseId}/draft-board/${prospectId}/status`),

  // Week Journal
  getWeekJournal: (franchiseId: string): Promise<WeekJournalResponse> =>
    request(`/management/franchise/${franchiseId}/week-journal`),

  addJournalEntry: (franchiseId: string, data: AddJournalEntryRequest): Promise<WeekJournalEntry> =>
    request(`/management/franchise/${franchiseId}/week-journal`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Practice Execution
  runPractice: (franchiseId: string, data: RunPracticeRequest): Promise<PracticeResults> =>
    request(`/management/franchise/${franchiseId}/run-practice`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Playbook Mastery
  getPlaybookMastery: (franchiseId: string): Promise<PlaybookMasteryResponse> =>
    request(`/management/franchise/${franchiseId}/playbook-mastery`),

  // Development/Potentials
  getDevelopment: (franchiseId: string): Promise<DevelopmentResponse> =>
    request(`/management/franchise/${franchiseId}/development`),

  // Weekly Development (growth this week)
  getWeeklyDevelopment: (franchiseId: string): Promise<WeeklyDevelopmentResponse> =>
    request(`/management/franchise/${franchiseId}/weekly-development`),

  // Game Simulation
  simGame: (franchiseId: string, eventId: string): Promise<GameResult> =>
    request(`/management/franchise/${franchiseId}/sim-game`, {
      method: 'POST',
      body: JSON.stringify({ event_id: eventId }),
    }),
};
