/**
 * BroadcastCanvas Types - Frame and player data structures
 *
 * These types match the backend frame data from coach_mode.py _collect_frame()
 */

export type PlayerType = 'qb' | 'receiver' | 'defender' | 'ol' | 'dl' | 'rb' | 'fb';
export type BallState = 'dead' | 'held' | 'in_flight' | 'loose';
export type ViewMode = 'field' | 'game';

export interface PlayerFrame {
  id: string;
  name: string;
  team: 'offense' | 'defense';
  position: string;
  player_type: PlayerType;
  x: number;  // Lateral position (0 = center)
  y: number;  // Depth from LOS (positive = downfield)
  vx: number;
  vy: number;
  speed: number;
  facing_x?: number;
  facing_y?: number;
  has_ball?: boolean;
  is_engaged?: boolean;

  // Route info (receivers)
  route_name?: string;
  route_phase?: string;
  current_waypoint?: number;
  total_waypoints?: number;
  target_x?: number;
  target_y?: number;

  // Coverage info (defenders)
  coverage_type?: 'man' | 'zone';
  coverage_phase?: string;
  man_target_id?: string;
  zone_type?: string;
  has_recognized_break?: boolean;
  has_triggered?: boolean;

  // Blocking
  engaged_with_id?: string;
  block_shed_progress?: number;

  // Ballcarrier
  is_ball_carrier?: boolean;
  in_tackle?: boolean;
  tackle_leverage?: number;

  // Pursuit
  pursuit_target_x?: number;
  pursuit_target_y?: number;
}

export interface WaypointFrame {
  x: number;
  y: number;
  is_break: boolean;
  phase: string;
}

export interface BallOrientation {
  x: number;  // Lateral axis component
  y: number;  // Downfield axis component
  z: number;  // Vertical axis component (tilt: positive = nose up)
}

export interface BallFrame {
  x: number;
  y: number;
  height: number;
  state: BallState;
  carrier_id: string | null;
  // Ball flight physics (Dzielski & Blackburn 2022)
  spin_rate?: number;        // RPM (500+ = tight spiral, below critical = wobbly)
  is_stable?: boolean;       // False = wobbly pass (below critical spin)
  orientation?: BallOrientation;  // Ball axis direction during flight
}

export interface PlayFrame {
  tick: number;
  time: number;
  phase: string;
  players: PlayerFrame[];
  ball: BallFrame;
  waypoints: Record<string, WaypointFrame[]>;
}

export interface TeamInfo {
  abbr: string;
  primaryColor: string;
  secondaryColor?: string;
  logo?: string;
}

export interface FieldPosition {
  /** Yard line where LOS is (0 = own goal line, 50 = midfield, 100 = opponent goal line) */
  yardLine: number;
  /** Yards needed for first down */
  yardsToGo: number;
  /** Down number (1-4) */
  down: number;
  /** Which team's territory (true = offense is in own territory, false = opponent's) */
  ownTerritory: boolean;
}

export interface BroadcastCanvasProps {
  frames: PlayFrame[];
  currentTick: number;
  isPlaying: boolean;

  // View mode
  viewMode: ViewMode;

  // Team info
  homeTeam: TeamInfo;
  awayTeam: TeamInfo;
  userControlsHome: boolean;
  possessionHome?: boolean;  // Which team has possession (true = home is offense)

  // Field position - for accurate yard markers
  fieldPosition?: FieldPosition;

  // Fog of war
  showOffenseRoutes: boolean;
  showDefenseCoverage: boolean;

  // Callbacks
  onTickChange: (tick: number) => void;
  onComplete?: () => void;

  // Canvas size overrides
  width?: number;
  height?: number;

  // Zoom level multiplier (1 = default, 2 = 2x zoom, etc.)
  zoomLevel?: number;
}

export interface Vec2 {
  x: number;
  y: number;
}
