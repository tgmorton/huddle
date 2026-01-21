/**
 * BroadcastCanvas Constants - AWS Next Gen Stats style configuration
 */

// Field dimensions
export const FIELD_WIDTH_YARDS = 53.33;  // NFL field width
export const FIELD_LENGTH_YARDS = 100;

// Canvas configuration
export const FIELD_VIEW_CONFIG = {
  // Scale is calculated dynamically to fit sideline-to-sideline
  showBall: false,    // Only show on passes
  showRoutes: false,  // Minimal routes
  tilt: false,
};

export const GAME_VIEW_CONFIG = {
  scale: 15,          // pixels per yard (zoomed in)
  showBall: true,
  showRoutes: true,
  tilt: true,         // Slight down-tilt
};

// Default canvas dimensions
export const DEFAULT_WIDTH = 900;
export const DEFAULT_HEIGHT = 500;

// Field padding (pixels on each side)
export const FIELD_PADDING = 20;

// Player chip dimensions
// Note: Real players are ~0.3 yards radius, but we scale up for visibility
// At field-view scale (~16 px/yard), CHIP_RADIUS=6 gives ~0.75 yard radius
export const CHIP_RADIUS = 6;
export const CHIP_BORDER_WIDTH = 1.5;
export const CHIP_FONT_SIZE = 9;

// Ball dimensions
export const BALL_WIDTH = 6;
export const BALL_HEIGHT = 4;

// Line widths
export const LOS_LINE_WIDTH = 4;
export const FIRST_DOWN_LINE_WIDTH = 4;
export const YARD_LINE_WIDTH = 2;
export const HASH_MARK_WIDTH = 1;
export const ROUTE_LINE_WIDTH = 3;

// AWS Next Gen Stats Color Palette
export const COLORS = {
  // Field
  fieldGreen: 0x1e7d32,
  fieldGreenDark: 0x166326,
  fieldLines: 0xffffff,
  endZone: 0x0d47a1,  // Deep blue for end zones

  // Marker lines
  lineOfScrimmage: 0x2196f3,  // Blue LOS
  firstDownLine: 0xffeb3b,    // Yellow first down marker

  // Player chips - Offense
  offenseChip: 0x1565c0,      // Blue chips for offense
  offenseChipAlt: 0x0d47a1,   // Darker blue alt

  // Player chips - Defense
  defenseChip: 0xb71c1c,      // Red chips for defense
  defenseChipAlt: 0x7f0000,   // Darker red alt

  // Special positions
  qbChip: 0xfdd835,           // Yellow/gold for QB
  ballCarrierRing: 0xffa726,  // Orange ring for ball carrier

  // Ball
  ball: 0x8b4513,             // Saddle brown
  ballLaces: 0xffffff,        // White laces
  ballInFlight: 0xffd54f,     // Bright for visibility in flight

  // Routes and coverage
  routeTrace: 0x64b5f6,       // Light blue route traces
  routeBreak: 0xff7043,       // Orange at break points
  coverageLine: 0xef5350,     // Light red for coverage

  // Text
  chipText: 0xffffff,
  yardNumber: 0xffffff,

  // UI elements
  hashMarks: 0xcccccc,
  sideline: 0xffffff,
};

// Hash mark positions (yards from center)
export const HASH_OFFSET_YARDS = 6.17;  // College hash width

// End zone configuration
export const END_ZONE_DEPTH = 10;  // yards

// Animation
export const TICKS_PER_SECOND = 20;
export const MS_PER_TICK = 1000 / TICKS_PER_SECOND;

// Trail configuration
export const MAX_TRAIL_LENGTH = 20;
export const TRAIL_OPACITY_START = 0.6;
export const TRAIL_OPACITY_END = 0.05;

// Tilt perspective for Game View
export const GAME_VIEW_PERSPECTIVE = 800;
export const GAME_VIEW_ROTATE_X = 15;  // degrees
