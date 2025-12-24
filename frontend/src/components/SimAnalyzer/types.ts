/**
 * SimAnalyzer Type Definitions
 *
 * Types for the simulation analysis visualization system.
 */

// View mode for the analyzer
export type ViewMode = 'analysis' | 'view';

// Player types from backend
export type PlayerType = 'qb' | 'receiver' | 'defender' | 'ol' | 'dl' | 'rb' | 'fb';

// Coverage types
export type CoverageType = 'man' | 'zone';

// Play phases
export type PlayPhase = 'PRE_SNAP' | 'SNAP' | 'DEVELOPMENT' | 'SCRAMBLE' | 'THROWN' | 'COMPLETE' | 'RUN_ACTIVE' | 'AFTER_CATCH';

// Gap types (between OL positions) - lowercase to match backend
export type GapType = 'a_left' | 'a_right' | 'b_left' | 'b_right' | 'c_left' | 'c_right' | 'd_left' | 'd_right';

// Run blocking assignments (from backend)
export type BlockingAssignment = 'zone_step' | 'pull_lead' | 'pull_wrap' | 'combo' | 'down' | 'cutoff' | 'reach' | 'base' | 'pass_set';

// Run play concepts
export type RunConcept = 'inside_zone' | 'outside_zone' | 'power' | 'counter' | 'dive' | 'draw' | 'toss';

// Play outcomes
export type PlayOutcome = 'in_progress' | 'complete' | 'incomplete' | 'interception' | 'tackled' | 'sack' | 'touchdown';

// Pressure levels (from QB brain)
export type PressureLevel = 'CLEAN' | 'LIGHT' | 'MODERATE' | 'HEAVY' | 'CRITICAL';

// Coverage shells (from QB brain)
export type CoverageShell = 'COVER_0' | 'COVER_1' | 'COVER_2' | 'COVER_3' | 'COVER_4' | 'COVER_6' | 'UNKNOWN';

// Blitz looks (from QB brain)
export type BlitzLook = 'NONE' | 'LIGHT' | 'HEAVY' | 'ZERO';

// Receiver status (from QB evaluation)
export type ReceiverStatus = 'OPEN' | 'WINDOW' | 'CONTESTED' | 'COVERED';

// Ball states
export type BallStateType = 'dead' | 'held' | 'in_flight' | 'loose';

// Throw types
export type ThrowType = 'bullet' | 'touch' | 'lob';

// Ballcarrier moves
export type MoveType = 'juke' | 'spin' | 'truck' | 'stiff_arm' | 'hurdle' | 'dead_leg' | 'cut' | 'speed_burst';

// ============================================================================
// Player State
// ============================================================================

export interface PlayerState {
  id: string;
  name: string;
  team: string;
  position: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  speed: number;
  facing_x?: number;
  facing_y?: number;
  player_type: PlayerType;
  has_ball?: boolean;
  goal_direction?: number;  // 1 = upfield, -1 = return

  // Receiver fields
  route_name?: string;
  route_phase?: string;
  current_waypoint?: number;
  total_waypoints?: number;
  target_x?: number;
  target_y?: number;
  read_order?: number;
  is_hot_route?: boolean;

  // Defender fields
  coverage_type?: CoverageType;
  coverage_phase?: string;
  man_target_id?: string;
  zone_type?: string;
  has_triggered?: boolean;
  has_reacted_to_break?: boolean;
  anticipated_x?: number;
  anticipated_y?: number;

  // DB recognition (cognitive delay)
  has_recognized_break?: boolean;
  recognition_timer?: number;
  recognition_delay?: number;

  // Pursuit (defenders chasing ballcarrier)
  pursuit_target_x?: number;
  pursuit_target_y?: number;

  // OL/DL blocking
  is_engaged?: boolean;
  engaged_with_id?: string;
  block_shed_progress?: number;
  blocking_assignment?: BlockingAssignment;
  is_pulling?: boolean;
  pull_target_x?: number;
  pull_target_y?: number;

  // RB run game
  target_gap?: GapType;
  designed_gap?: GapType;
  read_point_x?: number;
  read_point_y?: number;
  vision_target_x?: number;
  vision_target_y?: number;

  // Ballcarrier moves
  current_move?: MoveType;
  move_success?: boolean;

  // Tackle engagement (when ballcarrier is being tackled)
  in_tackle?: boolean;
  tackle_leverage?: number;  // -1 (tackler winning) to +1 (BC winning)
  tackle_ticks?: number;
  tackle_yards_gained?: number;
  primary_tackler_id?: string;

  // Common state
  at_max_speed?: boolean;
  cut_occurred?: boolean;
  cut_angle?: number;
  reasoning?: string;

  // QB evaluation of receiver (if applicable)
  qb_eval?: ReceiverEval;
}

// ============================================================================
// QB Analysis State
// ============================================================================

export interface ReceiverEval {
  separation: number;
  status: ReceiverStatus;
  route_phase: string;
  nearest_defender_id?: string;
  defender_closing_speed?: number;
  defender_trailing?: boolean;
  pre_break?: boolean;
  detection_quality: number;  // 1.0 = central vision, lower = peripheral
  read_order: number;
  is_hot?: boolean;
  anticipation_viable?: boolean;
}

export interface QBState {
  current_read: number;
  pressure_level: PressureLevel;
  time_in_pocket: number;
  coverage_shell?: CoverageShell;
  blitz_look?: BlitzLook;
  dropback_complete?: boolean;
  receiver_evals?: Record<string, ReceiverEval>;
}

// ============================================================================
// Ball State
// ============================================================================

export interface BallState {
  state: BallStateType;
  x: number;
  y: number;
  height: number;
  carrier_id: string | null;
  flight_origin_x?: number;
  flight_origin_y?: number;
  flight_target_x?: number;
  flight_target_y?: number;
  flight_progress?: number;
  intended_receiver_id?: string;
  throw_type?: ThrowType;
  peak_height?: number;
}

// ============================================================================
// Route & Zone Data
// ============================================================================

export interface WaypointData {
  x: number;
  y: number;
  is_break: boolean;
  phase: string;
  look_for_ball: boolean;
}

export interface ZoneBoundary {
  min_x: number;
  max_x: number;
  min_y: number;
  max_y: number;
  anchor_x: number;
  anchor_y: number;
  is_deep: boolean;
}

// ============================================================================
// Events
// ============================================================================

export interface GameEvent {
  time: number;
  type: string;
  player_id: string | null;
  target_id?: string;
  description: string;
  data?: Record<string, unknown>;
}

// ============================================================================
// Trace System
// ============================================================================

export type TraceCategory = 'perception' | 'decision' | 'action';

export interface TraceLine {
  tick: number;
  time: number;
  category: TraceCategory;
  message: string;
}

// ============================================================================
// Player Configuration
// ============================================================================

export interface PlayerConfig {
  name: string;
  position: string;
  alignment_x: number;
  alignment_y?: number;
  // Route (for receivers)
  route_type?: string;
  read_order?: number;
  is_hot_route?: boolean;
  // Coverage (for DBs/LBs)
  coverage_type?: CoverageType;
  man_target?: string;
  zone_type?: string;
  // Attributes
  speed?: number;
  acceleration?: number;
  agility?: number;
  strength?: number;
  awareness?: number;
  throw_power?: number;
  throw_accuracy?: number;
  route_running?: number;
  catching?: number;
  elusiveness?: number;
  vision?: number;
  block_power?: number;
  block_finesse?: number;
  pass_rush?: number;
  man_coverage?: number;
  zone_coverage?: number;
  play_recognition?: number;
  press?: number;
  tackling?: number;
}

// ============================================================================
// Simulation State
// ============================================================================

export interface SimConfig {
  tick_rate_ms: number;
  max_time: number;
  offense: PlayerConfig[];
  defense: PlayerConfig[];
}

// Trace entry from backend trace system
export interface TraceEntry {
  tick: number;
  time: number;
  player_id: string;
  player_name: string;
  category: 'perception' | 'decision' | 'action';
  message: string;
}

export interface SimState {
  session_id: string;
  tick: number;
  time: number;
  phase?: PlayPhase;
  is_running: boolean;
  is_paused: boolean;
  is_complete: boolean;
  play_outcome?: PlayOutcome;
  ball_carrier_id?: string | null;
  tackle_position?: { x: number; y: number } | null;
  tackler_id?: string | null;
  players: PlayerState[];
  ball?: BallState;
  waypoints: Record<string, WaypointData[]>;
  zone_boundaries: Record<string, ZoneBoundary>;
  events: GameEvent[];
  config: SimConfig;
  // Analysis data
  qb_state?: QBState;
  qb_trace?: string[];
  // Per-player traces (new trace system)
  traces?: TraceEntry[];
  // Run game data
  is_run_play?: boolean;
  run_concept?: RunConcept;
  designed_gap?: GapType;
}

// ============================================================================
// Coverage Assignment (for Analysis Panel)
// ============================================================================

export interface CoverageAssignment {
  defender_id: string;
  defender_name: string;
  coverage_type: CoverageType;
  // Man coverage
  target_id?: string;
  target_name?: string;
  separation?: number;
  // Zone coverage
  zone_type?: string;
  is_triggered?: boolean;
  // State
  phase?: string;
  has_recognized_break?: boolean;
  recognition_progress?: number;  // 0-1
}

// ============================================================================
// WebSocket Messages
// ============================================================================

export interface WSMessage {
  type: 'state_sync' | 'tick' | 'complete' | 'error';
  payload?: SimState;
  message?: string;
}

export interface WSCommand {
  type: 'start' | 'pause' | 'resume' | 'reset' | 'step' | 'sync';
}

// ============================================================================
// Route/Scheme Options (for setup)
// ============================================================================

export interface RouteOption {
  type: string;
  name: string;
  break_depth: number;
  total_depth: number;
  route_side: string;
  is_quick: boolean;
}

export interface ZoneOption {
  type: string;
  is_deep: boolean;
}

export interface ConceptOption {
  name: string;
  display_name: string;
  description: string;
  formation: string;
  timing: string;
  coverage_beaters: string[];
  route_count: number;
  isRun?: boolean;  // True for run concepts
}

export interface SchemeOption {
  name: string;
  display_name: string;
  scheme_type: string;
  description: string;
  strengths: string[];
  weaknesses: string[];
}
