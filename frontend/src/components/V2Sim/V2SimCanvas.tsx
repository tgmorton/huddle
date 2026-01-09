/**
 * PixiJS Canvas for V2 simulation visualization
 *
 * Shows:
 * - Receivers (blue) with routes and waypoints
 * - Defenders (red) with coverage info
 * - Velocity vectors and movement trails
 * - Zone boundaries for zone coverage
 * - Separation indicators
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { Application, Graphics, Text, TextStyle, Container } from 'pixi.js';

// Catch effect type for visual feedback
interface CatchEffect {
  id: string;
  x: number;  // yard coords
  y: number;
  startTime: number;
  airYards: number;
  playerName: string;
}

// Types
interface PlayerState {
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
  player_type: 'receiver' | 'defender' | 'qb' | 'ol' | 'dl' | 'rb' | 'fb';
  has_ball?: boolean;
  // Receiver fields
  route_name?: string;
  route_phase?: string;
  current_waypoint?: number;
  total_waypoints?: number;
  target_x?: number;
  target_y?: number;
  // Defender fields
  coverage_type?: string;
  coverage_phase?: string;
  man_target_id?: string;
  zone_type?: string;
  has_triggered?: boolean;
  has_reacted_to_break?: boolean;
  anticipated_x?: number;
  anticipated_y?: number;
  // Common
  at_max_speed?: boolean;
  cut_occurred?: boolean;
  cut_angle?: number;
  reasoning?: string;

  // OL/DL Blocking fields
  is_engaged?: boolean;
  engaged_with_id?: string;
  block_shed_progress?: number;  // 0.0 to 1.0 (DL only)

  // Ballcarrier move fields
  current_move?: string;  // 'juke' | 'spin' | 'truck' | null
  move_success?: boolean;

  // Pursuit fields (defenders)
  pursuit_target_x?: number;
  pursuit_target_y?: number;

  // DB recognition state
  has_recognized_break?: boolean;
  recognition_timer?: number;
  recognition_delay?: number;

  // Ballcarrier direction
  goal_direction?: number;  // 1 or -1

  // Tackle engagement fields (for ballcarrier)
  in_tackle?: boolean;
  tackle_leverage?: number;  // -1 (tackler winning) to +1 (BC winning)
  tackle_ticks?: number;
  tackle_yards_gained?: number;
  primary_tackler_id?: string;
}

interface WaypointData {
  x: number;
  y: number;
  is_break: boolean;
  phase: string;
  look_for_ball: boolean;
}

interface ZoneBoundary {
  min_x: number;
  max_x: number;
  min_y: number;
  max_y: number;
  anchor_x: number;
  anchor_y: number;
  is_deep: boolean;
}

interface BallState {
  state: 'dead' | 'held' | 'in_flight' | 'loose';
  x: number;
  y: number;
  height: number;  // Height in yards (for 2.5D visualization)
  carrier_id: string | null;
  flight_origin_x?: number;
  flight_origin_y?: number;
  flight_target_x?: number;
  flight_target_y?: number;
  flight_progress?: number;
  intended_receiver_id?: string;
  throw_type?: 'bullet' | 'touch' | 'lob';
  peak_height?: number;
}

interface SimState {
  session_id: string;
  tick: number;
  time: number;
  is_running: boolean;
  is_paused: boolean;
  is_complete: boolean;
  players: PlayerState[];
  ball?: BallState;
  waypoints: Record<string, WaypointData[]>;
  zone_boundaries: Record<string, ZoneBoundary>;
  events: unknown[];
  config: unknown;
}

// Canvas config - full sideline-to-sideline view
// NFL field is 53.33 yards wide (160 feet), 26.67 yards from center to each sideline
const FIELD_WIDTH_YARDS = 53.33;
const PIXELS_PER_YARD = 18;  // Slightly smaller to fit better
const FIELD_PADDING = 40;    // Padding outside sidelines for labels

const CANVAS_WIDTH = Math.ceil(FIELD_WIDTH_YARDS * PIXELS_PER_YARD) + FIELD_PADDING * 2;  // ~1040px
const CANVAS_HEIGHT = 750;

// Field centered at x=0 (center of field), showing full sideline-to-sideline
// y=0 is LOS, showing -5 to 35 yards depth
const FIELD_CENTER_X = CANVAS_WIDTH / 2;
const LOS_Y = CANVAS_HEIGHT - 120; // LOS near bottom

const COLORS = {
  field: 0x228B22,
  fieldLines: 0xffffff,
  los: 0xffff00,
  hashMarks: 0xcccccc,

  // Offense (receivers)
  offense: 0x4169E1,
  offenseLight: 0x87AFFF,
  offenseTrail: 0x6495ED,

  // Defense (defenders)
  defense: 0xDC143C,
  defenseLight: 0xFF6B6B,
  defenseTrail: 0xCD5C5C,

  // QB
  qb: 0x00CED1,  // Dark cyan

  // OL (Offensive Line) - Green
  ol: 0x22c55e,
  olLight: 0x4ade80,
  olTrail: 0x16a34a,

  // DL (Defensive Line) - Orange
  dl: 0xf97316,
  dlLight: 0xfb923c,
  dlTrail: 0xea580c,

  // Ball
  ball: 0x8B4513,  // Saddle brown (football color)
  ballInFlight: 0xFFD700,  // Gold when in flight
  ballTarget: 0xFF4500,  // Orange red for target indicator

  // Waypoints
  waypoint: 0xFFA500,
  waypointDone: 0x666666,
  waypointCurrent: 0xFFD700,
  waypointBreak: 0xFF4500,

  // Zone visualization
  zoneDeep: 0x4B0082,
  zoneUnder: 0x800080,

  velocity: 0x00FF7F,
  cutIndicator: 0xFF00FF,
  anticipation: 0xFFD700,
  separation: 0xFF6347,

  // Blocking engagement
  blockNeutral: 0xFFFF00,  // Yellow - neutral engagement
  blockDLWinning: 0xFF4500,  // Orange-red - DL gaining advantage
  shedProgress: 0xFF6347,  // Tomato - shed progress bar

  // Ballcarrier moves
  moveSuccess: 0x22c55e,  // Green - move succeeded
  moveFailed: 0xef4444,   // Red - move failed

  // Pursuit
  pursuitLine: 0xFF69B4,  // Hot pink - pursuit angle line

  // Recognition state
  recognizing: 0xFFFF00,  // Yellow - still reading
  recognized: 0xFF0000,   // Red - recognized the break

  // Catch effects
  catchFlash: 0xFFD700,   // Gold - catch ring
  catchFlashInner: 0xFFFFFF,  // White - inner burst
  yardsPopup: 0x22c55e,   // Green - yards gained

  // Tackle engagement
  tackleOrange: 0xf97316,  // Orange - tackle line and label
  tackleBCWinning: 0x22c55e,  // Green - BC has leverage
  tackleTacklerWinning: 0xef4444,  // Red - tackler has leverage
  tackleNeutral: 0xf97316,  // Orange - neutral

  text: 0xffffff,
  textDim: 0xaaaaaa,
};

interface V2SimCanvasProps {
  simState: SimState | null;
  selectedPlayerId: string | null;
  onSelectPlayer: (id: string | null) => void;
}

export function V2SimCanvas({
  simState,
  selectedPlayerId,
  onSelectPlayer
}: V2SimCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const playersContainerRef = useRef<Container | null>(null);

  // Store position history for trails
  const positionHistoryRef = useRef<Map<string, Array<{ x: number; y: number }>>>(new Map());

  // Catch effects system
  const [catchEffects, setCatchEffects] = useState<CatchEffect[]>([]);
  const prevBallStateRef = useRef<{ state: string; carrierId: string | null } | null>(null);
  const effectsContainerRef = useRef<Container | null>(null);

  // Convert yard coords to screen coords
  const yardToScreen = useCallback((x: number, y: number): { x: number; y: number } => {
    return {
      x: FIELD_CENTER_X + x * PIXELS_PER_YARD,
      y: LOS_Y - y * PIXELS_PER_YARD, // Invert Y
    };
  }, []);

  // Initialize PixiJS
  useEffect(() => {
    if (!canvasRef.current || appRef.current) return;

    let mounted = true;

    const init = async () => {
      const app = new Application();
      await app.init({
        width: CANVAS_WIDTH,
        height: CANVAS_HEIGHT,
        backgroundColor: COLORS.field,
        antialias: true,
      });

      if (!mounted || !canvasRef.current) {
        app.destroy(true);
        return;
      }

      canvasRef.current.appendChild(app.canvas);
      appRef.current = app;

      // Draw static field
      drawField(app);

      // Container for dynamic elements
      const playersContainer = new Container();
      app.stage.addChild(playersContainer);
      playersContainerRef.current = playersContainer;

      // Container for effects (on top of players)
      const effectsContainer = new Container();
      app.stage.addChild(effectsContainer);
      effectsContainerRef.current = effectsContainer;
    };

    init();

    return () => {
      mounted = false;
      if (appRef.current) {
        appRef.current.destroy(true);
        appRef.current = null;
      }
    };
  }, []);

  // Draw static field elements
  const drawField = (app: Application) => {
    const g = new Graphics();

    // Yard lines every 5 yards
    for (let y = -5; y <= 35; y += 5) {
      const screenY = LOS_Y - y * PIXELS_PER_YARD;
      const alpha = y === 0 ? 1 : 0.4;
      const width = y === 0 ? 3 : 1;
      const color = y === 0 ? COLORS.los : COLORS.fieldLines;

      g.moveTo(0, screenY);
      g.lineTo(CANVAS_WIDTH, screenY);
      g.stroke({ color, width, alpha });

      // Yard label
      if (y % 5 === 0) {
        const label = new Text({
          text: `${y}`,
          style: new TextStyle({
            fontSize: 12,
            fill: COLORS.textDim,
          }),
        });
        label.x = 10;
        label.y = screenY - 8;
        app.stage.addChild(label);
      }
    }

    // Hash marks (NFL: 6.17 yards from center)
    const hashOffset = 6.17 * PIXELS_PER_YARD;
    for (let y = -5; y <= 35; y += 1) {
      const screenY = LOS_Y - y * PIXELS_PER_YARD;

      // Left hash
      g.moveTo(FIELD_CENTER_X - hashOffset - 5, screenY);
      g.lineTo(FIELD_CENTER_X - hashOffset + 5, screenY);
      g.stroke({ color: COLORS.hashMarks, width: 1, alpha: 0.5 });

      // Right hash
      g.moveTo(FIELD_CENTER_X + hashOffset - 5, screenY);
      g.lineTo(FIELD_CENTER_X + hashOffset + 5, screenY);
      g.stroke({ color: COLORS.hashMarks, width: 1, alpha: 0.5 });
    }

    // Center line
    g.moveTo(FIELD_CENTER_X, 0);
    g.lineTo(FIELD_CENTER_X, CANVAS_HEIGHT);
    g.stroke({ color: COLORS.fieldLines, width: 1, alpha: 0.2 });

    // Sidelines (26.67 yards from center = half of 53.33 yard field)
    const sidelineOffset = (FIELD_WIDTH_YARDS / 2) * PIXELS_PER_YARD;

    // Left sideline
    g.moveTo(FIELD_CENTER_X - sidelineOffset, 0);
    g.lineTo(FIELD_CENTER_X - sidelineOffset, CANVAS_HEIGHT);
    g.stroke({ color: COLORS.fieldLines, width: 3, alpha: 1 });

    // Right sideline
    g.moveTo(FIELD_CENTER_X + sidelineOffset, 0);
    g.lineTo(FIELD_CENTER_X + sidelineOffset, CANVAS_HEIGHT);
    g.stroke({ color: COLORS.fieldLines, width: 3, alpha: 1 });

    // Out of bounds areas (darker green turf)
    const leftOOBWidth = FIELD_CENTER_X - sidelineOffset;
    const rightOOBStart = FIELD_CENTER_X + sidelineOffset;

    g.rect(0, 0, leftOOBWidth, CANVAS_HEIGHT);
    g.fill({ color: 0x1a472a, alpha: 0.8 });

    g.rect(rightOOBStart, 0, CANVAS_WIDTH - rightOOBStart, CANVAS_HEIGHT);
    g.fill({ color: 0x1a472a, alpha: 0.8 });

    app.stage.addChild(g);

    // LOS label
    const losLabel = new Text({
      text: 'LOS',
      style: new TextStyle({
        fontSize: 14,
        fill: COLORS.los,
        fontWeight: 'bold',
      }),
    });
    losLabel.x = CANVAS_WIDTH - 40;
    losLabel.y = LOS_Y - 8;
    app.stage.addChild(losLabel);
  };

  // Draw waypoints for a receiver
  const drawWaypoints = (container: Container, waypoints: WaypointData[], currentIdx: number) => {
    const g = new Graphics();

    // Draw connecting lines first
    for (let i = 0; i < waypoints.length - 1; i++) {
      const wp1 = yardToScreen(waypoints[i].x, waypoints[i].y);
      const wp2 = yardToScreen(waypoints[i + 1].x, waypoints[i + 1].y);
      const color = i < currentIdx ? COLORS.waypointDone : COLORS.waypoint;

      g.moveTo(wp1.x, wp1.y);
      g.lineTo(wp2.x, wp2.y);
      g.stroke({ color, width: 2, alpha: 0.6 });
    }

    // Draw waypoint markers
    waypoints.forEach((wp, i) => {
      const screen = yardToScreen(wp.x, wp.y);
      let color: number;
      let radius: number;

      if (i < currentIdx) {
        color = COLORS.waypointDone;
        radius = 4;
      } else if (i === currentIdx) {
        color = COLORS.waypointCurrent;
        radius = 8;
      } else {
        color = wp.is_break ? COLORS.waypointBreak : COLORS.waypoint;
        radius = 6;
      }

      g.circle(screen.x, screen.y, radius);
      g.stroke({ color, width: 2 });

      // Waypoint number
      const label = new Text({
        text: `${i + 1}`,
        style: new TextStyle({
          fontSize: 10,
          fill: color,
        }),
      });
      label.x = screen.x + 10;
      label.y = screen.y - 5;
      container.addChild(label);
    });

    container.addChild(g);
  };

  // Draw zone boundary for selected defender
  const drawZoneBoundary = (container: Container, zoneType: string, zoneBoundaries: Record<string, ZoneBoundary>) => {
    const zone = zoneBoundaries[zoneType];
    if (!zone) return;

    const g = new Graphics();
    const topLeft = yardToScreen(zone.min_x, zone.max_y);
    const bottomRight = yardToScreen(zone.max_x, zone.min_y);

    const width = bottomRight.x - topLeft.x;
    const height = bottomRight.y - topLeft.y;

    // Zone rectangle
    g.rect(topLeft.x, topLeft.y, width, height);
    g.fill({ color: zone.is_deep ? COLORS.zoneDeep : COLORS.zoneUnder, alpha: 0.15 });
    g.stroke({ color: zone.is_deep ? COLORS.zoneDeep : COLORS.zoneUnder, width: 2, alpha: 0.5 });

    // Zone anchor
    const anchor = yardToScreen(zone.anchor_x, zone.anchor_y);
    g.circle(anchor.x, anchor.y, 6);
    g.stroke({ color: COLORS.anticipation, width: 2 });

    // Zone label
    const label = new Text({
      text: zoneType.replace(/_/g, ' '),
      style: new TextStyle({
        fontSize: 10,
        fill: COLORS.textDim,
      }),
    });
    label.x = topLeft.x + 5;
    label.y = topLeft.y + 5;
    container.addChild(label);

    container.addChild(g);
  };

  // Draw anticipated position for defender
  const drawAnticipatedPosition = (container: Container, player: PlayerState) => {
    if (player.anticipated_x === undefined || player.anticipated_y === undefined) return;

    const g = new Graphics();
    const screen = yardToScreen(player.x, player.y);
    const anticipated = yardToScreen(player.anticipated_x, player.anticipated_y);

    // Dashed line to anticipated position
    g.moveTo(screen.x, screen.y);
    g.lineTo(anticipated.x, anticipated.y);
    g.stroke({ color: COLORS.anticipation, width: 1, alpha: 0.5 });

    // Anticipated position marker
    g.circle(anticipated.x, anticipated.y, 5);
    g.fill({ color: COLORS.anticipation, alpha: 0.3 });
    g.stroke({ color: COLORS.anticipation, width: 1 });

    container.addChild(g);
  };

  // Draw separation line between defender and their target
  const drawSeparation = (container: Container, defender: PlayerState, players: PlayerState[]) => {
    if (!defender.man_target_id) return;

    const receiver = players.find(p => p.id === defender.man_target_id);
    if (!receiver) return;

    const g = new Graphics();
    const defScreen = yardToScreen(defender.x, defender.y);
    const rcvScreen = yardToScreen(receiver.x, receiver.y);

    // Line connecting defender to receiver
    g.moveTo(defScreen.x, defScreen.y);
    g.lineTo(rcvScreen.x, rcvScreen.y);
    g.stroke({ color: COLORS.separation, width: 1, alpha: 0.4 });

    // Calculate separation
    const dx = receiver.x - defender.x;
    const dy = receiver.y - defender.y;
    const separation = Math.sqrt(dx * dx + dy * dy);

    // Separation label at midpoint
    const midX = (defScreen.x + rcvScreen.x) / 2;
    const midY = (defScreen.y + rcvScreen.y) / 2;
    const label = new Text({
      text: `${separation.toFixed(1)}yd`,
      style: new TextStyle({
        fontSize: 9,
        fill: COLORS.separation,
      }),
    });
    label.x = midX + 5;
    label.y = midY - 5;
    container.addChild(label);

    container.addChild(g);
  };

  // Draw blocking engagement between OL and DL
  const drawBlockingEngagement = (
    container: Container,
    ol: PlayerState,
    dl: PlayerState,
  ) => {
    const g = new Graphics();
    const olScreen = yardToScreen(ol.x, ol.y);
    const dlScreen = yardToScreen(dl.x, dl.y);

    // Determine line color based on shed progress
    const shedProgress = dl.block_shed_progress ?? 0;
    const lineColor = shedProgress > 0.5 ? COLORS.blockDLWinning : COLORS.blockNeutral;

    // Line connecting engaged OL/DL
    g.moveTo(olScreen.x, olScreen.y);
    g.lineTo(dlScreen.x, dlScreen.y);
    g.stroke({ color: lineColor, width: 3, alpha: 0.8 });

    // Shed progress bar above DL
    if (shedProgress > 0) {
      const barWidth = 30;
      const barHeight = 5;
      const barX = dlScreen.x - barWidth / 2;
      const barY = dlScreen.y - 25;

      // Background bar
      g.rect(barX, barY, barWidth, barHeight);
      g.fill({ color: 0x333333, alpha: 0.8 });

      // Progress fill
      g.rect(barX, barY, barWidth * shedProgress, barHeight);
      g.fill({ color: COLORS.shedProgress });

      // "SHED!" text when complete
      if (shedProgress >= 1.0) {
        const shedLabel = new Text({
          text: 'SHED!',
          style: new TextStyle({
            fontSize: 10,
            fill: COLORS.shedProgress,
            fontWeight: 'bold',
          }),
        });
        shedLabel.anchor.set(0.5);
        shedLabel.x = dlScreen.x;
        shedLabel.y = dlScreen.y - 35;
        container.addChild(shedLabel);
      }
    }

    container.addChild(g);
  };

  // Draw pursuit line from defender to intercept point
  const drawPursuitLine = (container: Container, player: PlayerState) => {
    if (player.pursuit_target_x === undefined || player.pursuit_target_y === undefined) return;

    const g = new Graphics();
    const screen = yardToScreen(player.x, player.y);
    const target = yardToScreen(player.pursuit_target_x, player.pursuit_target_y);

    // Dashed line to pursuit target
    const dashLength = 8;
    const gapLength = 5;
    const dx = target.x - screen.x;
    const dy = target.y - screen.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const nx = dx / dist;
    const ny = dy / dist;

    let pos = 0;
    while (pos < dist) {
      const startX = screen.x + nx * pos;
      const startY = screen.y + ny * pos;
      const endPos = Math.min(pos + dashLength, dist);
      const endX = screen.x + nx * endPos;
      const endY = screen.y + ny * endPos;

      g.moveTo(startX, startY);
      g.lineTo(endX, endY);
      pos += dashLength + gapLength;
    }
    g.stroke({ color: COLORS.pursuitLine, width: 2, alpha: 0.7 });

    // Target marker (X)
    const markerSize = 6;
    g.moveTo(target.x - markerSize, target.y - markerSize);
    g.lineTo(target.x + markerSize, target.y + markerSize);
    g.moveTo(target.x + markerSize, target.y - markerSize);
    g.lineTo(target.x - markerSize, target.y + markerSize);
    g.stroke({ color: COLORS.pursuitLine, width: 2 });

    container.addChild(g);
  };

  // Draw ballcarrier move indicator
  const drawMoveIndicator = (container: Container, player: PlayerState, screen: { x: number; y: number }) => {
    if (!player.current_move) return;

    const g = new Graphics();
    const color = player.move_success ? COLORS.moveSuccess : COLORS.moveFailed;
    const moveY = screen.y - 35;

    // Draw move-specific icon
    if (player.current_move === 'juke') {
      // Arrow icon (horizontal zigzag)
      g.moveTo(screen.x - 12, moveY);
      g.lineTo(screen.x - 4, moveY - 6);
      g.lineTo(screen.x + 4, moveY + 6);
      g.lineTo(screen.x + 12, moveY);
      g.stroke({ color, width: 3 });
    } else if (player.current_move === 'spin') {
      // Circle icon
      g.circle(screen.x, moveY, 8);
      g.stroke({ color, width: 3 });
      // Add spin arrow
      g.moveTo(screen.x + 8, moveY);
      g.lineTo(screen.x + 12, moveY - 4);
      g.stroke({ color, width: 2 });
    } else if (player.current_move === 'truck') {
      // Impact icon (explosion lines)
      for (let i = 0; i < 6; i++) {
        const angle = (i / 6) * Math.PI * 2;
        g.moveTo(screen.x + Math.cos(angle) * 4, moveY + Math.sin(angle) * 4);
        g.lineTo(screen.x + Math.cos(angle) * 10, moveY + Math.sin(angle) * 10);
      }
      g.stroke({ color, width: 2 });
    }

    container.addChild(g);
  };

  // Draw DB recognition state indicator
  const drawRecognitionState = (container: Container, player: PlayerState, screen: { x: number; y: number }) => {
    if (player.has_recognized_break === undefined) return;

    const iconY = screen.y - 28;

    if (player.has_recognized_break) {
      // Show "!" when recognized
      const label = new Text({
        text: '!',
        style: new TextStyle({
          fontSize: 14,
          fill: COLORS.recognized,
          fontWeight: 'bold',
        }),
      });
      label.anchor.set(0.5);
      label.x = screen.x + 18;
      label.y = iconY;
      container.addChild(label);
    } else if (player.recognition_timer !== undefined && player.recognition_delay !== undefined) {
      // Show "?" with optional progress arc while reading
      const label = new Text({
        text: '?',
        style: new TextStyle({
          fontSize: 14,
          fill: COLORS.recognizing,
          fontWeight: 'bold',
        }),
      });
      label.anchor.set(0.5);
      label.x = screen.x + 18;
      label.y = iconY;
      container.addChild(label);

      // Progress arc around the "?"
      if (player.recognition_delay > 0) {
        const progress = player.recognition_timer / player.recognition_delay;
        const g = new Graphics();
        const arcRadius = 10;
        g.arc(screen.x + 18, iconY, arcRadius, -Math.PI / 2, -Math.PI / 2 + (progress * Math.PI * 2));
        g.stroke({ color: COLORS.recognizing, width: 2, alpha: 0.8 });
        container.addChild(g);
      }
    }
  };

  // Draw ballcarrier goal direction arrow
  const drawGoalDirection = (container: Container, player: PlayerState, screen: { x: number; y: number }) => {
    if (player.goal_direction === undefined || !player.has_ball) return;

    const g = new Graphics();
    const arrowY = screen.y + 22;
    const arrowLength = 15;
    const arrowHeadSize = 5;

    // Direction: 1 = upfield (positive Y = up on screen = toward top)
    // Direction: -1 = return (negative Y = down on screen = toward bottom)
    const yDir = -player.goal_direction;  // Invert because screen Y is inverted

    // Arrow body
    g.moveTo(screen.x, arrowY);
    g.lineTo(screen.x, arrowY + yDir * arrowLength);
    g.stroke({ color: COLORS.anticipation, width: 2 });

    // Arrow head
    const tipY = arrowY + yDir * arrowLength;
    g.moveTo(screen.x - arrowHeadSize, tipY - yDir * arrowHeadSize);
    g.lineTo(screen.x, tipY);
    g.lineTo(screen.x + arrowHeadSize, tipY - yDir * arrowHeadSize);
    g.stroke({ color: COLORS.anticipation, width: 2 });

    container.addChild(g);
  };

  // Draw tackle engagement visualization
  const drawTackleEngagement = (
    container: Container,
    ballcarrier: PlayerState,
    allPlayers: PlayerState[]
  ) => {
    const bcScreen = yardToScreen(ballcarrier.x, ballcarrier.y);
    const g = new Graphics();

    // Find the primary tackler
    const tackler = ballcarrier.primary_tackler_id
      ? allPlayers.find(p => p.id === ballcarrier.primary_tackler_id)
      : null;

    // Draw connection line between BC and tackler
    if (tackler) {
      const tacklerScreen = yardToScreen(tackler.x, tackler.y);

      // Pulsing tackle line
      g.moveTo(bcScreen.x, bcScreen.y);
      g.lineTo(tacklerScreen.x, tacklerScreen.y);
      g.stroke({ color: COLORS.tackleOrange, width: 4, alpha: 0.8 });

      // Draw struggle indicator at midpoint
      const midX = (bcScreen.x + tacklerScreen.x) / 2;
      const midY = (bcScreen.y + tacklerScreen.y) / 2;

      // Leverage bar (centered, shows who's winning)
      const barWidth = 50;
      const barHeight = 10;
      const leverage = ballcarrier.tackle_leverage ?? 0;

      // Background
      g.rect(midX - barWidth / 2, midY - barHeight / 2, barWidth, barHeight);
      g.fill({ color: 0x000000, alpha: 0.7 });

      // Center line (neutral point)
      g.moveTo(midX, midY - barHeight / 2);
      g.lineTo(midX, midY + barHeight / 2);
      g.stroke({ color: 0xffffff, width: 1, alpha: 0.5 });

      // Leverage fill - from center outward
      // Positive leverage (BC winning) = fill right (green)
      // Negative leverage (tackler winning) = fill left (red)
      const fillWidth = Math.abs(leverage) * (barWidth / 2);
      if (leverage > 0) {
        // BC winning - green fill from center to right
        g.rect(midX, midY - barHeight / 2, fillWidth, barHeight);
        g.fill({ color: COLORS.tackleBCWinning, alpha: 0.9 });
      } else if (leverage < 0) {
        // Tackler winning - red fill from center to left
        g.rect(midX - fillWidth, midY - barHeight / 2, fillWidth, barHeight);
        g.fill({ color: COLORS.tackleTacklerWinning, alpha: 0.9 });
      }

      // Border
      g.rect(midX - barWidth / 2, midY - barHeight / 2, barWidth, barHeight);
      g.stroke({ color: 0xffffff, width: 1 });

      // TACKLE label
      const tackleLabel = new Text({
        text: 'TACKLE',
        style: new TextStyle({
          fontSize: 10,
          fill: COLORS.tackleOrange,
          fontWeight: 'bold',
          fontFamily: 'Berkeley Mono, SF Mono, monospace',
        }),
      });
      tackleLabel.anchor.set(0.5);
      tackleLabel.x = midX;
      tackleLabel.y = midY - barHeight / 2 - 10;
      container.addChild(tackleLabel);

      // Yards gained during engagement (if any)
      if (ballcarrier.tackle_yards_gained && ballcarrier.tackle_yards_gained > 0.1) {
        const yacLabel = new Text({
          text: `+${ballcarrier.tackle_yards_gained.toFixed(1)} YAC`,
          style: new TextStyle({
            fontSize: 9,
            fill: COLORS.tackleBCWinning,
            fontWeight: 'bold',
            fontFamily: 'Berkeley Mono, SF Mono, monospace',
          }),
        });
        yacLabel.anchor.set(0.5);
        yacLabel.x = midX;
        yacLabel.y = midY + barHeight / 2 + 10;
        container.addChild(yacLabel);
      }

      // Highlight the primary tackler with an orange ring
      g.circle(tacklerScreen.x, tacklerScreen.y, 18);
      g.stroke({ color: COLORS.tackleOrange, width: 3, alpha: 0.8 });
    }

    // Draw struggle effect around ballcarrier (concentric rings based on leverage)
    const ringRadius = 24;
    const leverage = ballcarrier.tackle_leverage ?? 0;

    // Inner ring - color based on who's winning
    const ringColor = leverage > 0 ? COLORS.tackleBCWinning
      : leverage < 0 ? COLORS.tackleTacklerWinning
      : COLORS.tackleNeutral;
    g.circle(bcScreen.x, bcScreen.y, ringRadius);
    g.stroke({ color: ringColor, width: 3, alpha: 0.7 });

    // Outer ring (faded)
    g.circle(bcScreen.x, bcScreen.y, ringRadius + 6);
    g.stroke({ color: ringColor, width: 2, alpha: 0.3 });

    // "GOING DOWN" indicator when tackler is winning heavily
    if (leverage < -0.6) {
      const downLabel = new Text({
        text: 'GOING DOWN',
        style: new TextStyle({
          fontSize: 11,
          fill: COLORS.tackleTacklerWinning,
          fontWeight: 'bold',
          fontFamily: 'Berkeley Mono, SF Mono, monospace',
        }),
      });
      downLabel.anchor.set(0.5);
      downLabel.x = bcScreen.x;
      downLabel.y = bcScreen.y + ringRadius + 16;
      container.addChild(downLabel);
    } else if (leverage > 0.6) {
      // "BREAKING FREE" indicator when BC is about to escape
      const freeLabel = new Text({
        text: 'BREAKING FREE',
        style: new TextStyle({
          fontSize: 11,
          fill: COLORS.tackleBCWinning,
          fontWeight: 'bold',
          fontFamily: 'Berkeley Mono, SF Mono, monospace',
        }),
      });
      freeLabel.anchor.set(0.5);
      freeLabel.x = bcScreen.x;
      freeLabel.y = bcScreen.y + ringRadius + 16;
      container.addChild(freeLabel);
    }

    container.addChild(g);
  };

  // Update position history when we get new state
  useEffect(() => {
    if (!simState) return;

    const history = positionHistoryRef.current;

    simState.players.forEach(player => {
      if (!history.has(player.id)) {
        history.set(player.id, []);
      }

      const playerHistory = history.get(player.id)!;
      playerHistory.push({ x: player.x, y: player.y });

      // Keep max 60 positions (3 seconds at 20fps)
      if (playerHistory.length > 60) {
        playerHistory.shift();
      }
    });
  }, [simState]);

  // Clear history on reset (tick 0)
  useEffect(() => {
    if (simState?.tick === 0) {
      positionHistoryRef.current.clear();
      setCatchEffects([]);  // Clear catch effects on reset
    }
  }, [simState?.tick]);

  // Detect catches and spawn effects
  useEffect(() => {
    if (!simState?.ball) return;

    const prevState = prevBallStateRef.current;
    const currentState = simState.ball.state;
    const currentCarrier = simState.ball.carrier_id;

    // Detect catch: ball was in_flight, now held by a receiver
    if (prevState?.state === 'in_flight' && currentState === 'held' && currentCarrier) {
      const catcher = simState.players.find(p => p.id === currentCarrier);
      if (catcher && (catcher.player_type === 'receiver' || catcher.position === 'TE' || catcher.position === 'RB')) {
        // Calculate air yards (from LOS at y=0 to catch point)
        const airYards = Math.round(catcher.y);

        // Spawn catch effect
        const newEffect: CatchEffect = {
          id: `catch-${Date.now()}`,
          x: catcher.x,
          y: catcher.y,
          startTime: Date.now(),
          airYards,
          playerName: catcher.name,
        };

        setCatchEffects(prev => [...prev, newEffect]);

        // Auto-select the catcher
        onSelectPlayer(currentCarrier);
      }
    }

    // Update prev state
    prevBallStateRef.current = { state: currentState, carrierId: currentCarrier };
  }, [simState?.ball?.state, simState?.ball?.carrier_id, simState?.players, onSelectPlayer]);

  // Clean up expired catch effects (after 1.5 seconds)
  useEffect(() => {
    if (catchEffects.length === 0) return;

    const interval = setInterval(() => {
      const now = Date.now();
      setCatchEffects(prev => prev.filter(e => now - e.startTime < 1500));
    }, 100);

    return () => clearInterval(interval);
  }, [catchEffects.length]);

  // Draw catch effects
  const drawCatchEffects = useCallback((container: Container) => {
    const now = Date.now();

    catchEffects.forEach(effect => {
      const elapsed = now - effect.startTime;
      const duration = 1500;  // 1.5 second animation
      const progress = Math.min(elapsed / duration, 1);

      const screen = yardToScreen(effect.x, effect.y);
      const effectContainer = new Container();

      // Expanding ring (golden)
      const ringG = new Graphics();
      const maxRadius = 60;
      const ringRadius = 15 + progress * maxRadius;
      const ringAlpha = Math.max(0, 1 - progress * 1.2);  // Fade out
      const ringWidth = Math.max(1, 4 - progress * 3);

      ringG.circle(screen.x, screen.y, ringRadius);
      ringG.stroke({ color: COLORS.catchFlash, width: ringWidth, alpha: ringAlpha });

      // Second ring (slightly delayed)
      if (progress > 0.1) {
        const ring2Progress = Math.min((elapsed - 100) / duration, 1);
        const ring2Radius = 15 + ring2Progress * maxRadius * 0.8;
        const ring2Alpha = Math.max(0, 0.6 - ring2Progress * 1.2);

        ringG.circle(screen.x, screen.y, ring2Radius);
        ringG.stroke({ color: COLORS.catchFlashInner, width: 2, alpha: ring2Alpha });
      }

      effectContainer.addChild(ringG);

      // Floating yards popup
      if (effect.airYards > 0) {
        const popupProgress = Math.min(progress * 2, 1);  // Faster animation
        const popupY = screen.y - 40 - popupProgress * 30;  // Float upward
        const popupAlpha = progress < 0.7 ? 1 : Math.max(0, 1 - (progress - 0.7) / 0.3);

        // Background pill
        const pillG = new Graphics();
        const text = `+${effect.airYards} YDS`;
        const pillWidth = 60;
        const pillHeight = 22;

        pillG.roundRect(screen.x - pillWidth / 2, popupY - pillHeight / 2, pillWidth, pillHeight, 11);
        pillG.fill({ color: COLORS.yardsPopup, alpha: popupAlpha * 0.9 });

        effectContainer.addChild(pillG);

        // Text
        const ydsLabel = new Text({
          text,
          style: new TextStyle({
            fontSize: 13,
            fontWeight: 'bold',
            fill: 0xffffff,
          }),
        });
        ydsLabel.anchor.set(0.5);
        ydsLabel.x = screen.x;
        ydsLabel.y = popupY;
        ydsLabel.alpha = popupAlpha;
        effectContainer.addChild(ydsLabel);
      }

      container.addChild(effectContainer);
    });
  }, [catchEffects, yardToScreen]);

  // Update visualization when state changes
  useEffect(() => {
    if (!simState || !playersContainerRef.current) return;

    const container = playersContainerRef.current;

    // Clear previous frame
    container.removeChildren();

    // Get selected player for zone/separation drawing
    const selectedPlayer = simState.players.find(p => p.id === selectedPlayerId);

    // Draw zone boundary if selected defender has zone coverage
    if (selectedPlayer?.player_type === 'defender' && selectedPlayer.zone_type && simState.zone_boundaries) {
      drawZoneBoundary(container, selectedPlayer.zone_type, simState.zone_boundaries);
    }

    // Draw separation lines for selected defender
    if (selectedPlayer?.player_type === 'defender' && selectedPlayer.coverage_type === 'man') {
      drawSeparation(container, selectedPlayer, simState.players);
    }

    // Draw blocking engagements first (behind players)
    const olPlayers = simState.players.filter(p => p.player_type === 'ol');
    const dlPlayers = simState.players.filter(p => p.player_type === 'dl');

    olPlayers.forEach(ol => {
      if (ol.is_engaged && ol.engaged_with_id) {
        const dl = dlPlayers.find(d => d.id === ol.engaged_with_id);
        if (dl) {
          drawBlockingEngagement(container, ol, dl);
        }
      }
    });

    // Draw pursuit lines for defenders (behind players)
    simState.players.forEach(player => {
      if (player.player_type === 'defender' || player.player_type === 'dl') {
        if (player.pursuit_target_x !== undefined && player.pursuit_target_y !== undefined) {
          drawPursuitLine(container, player);
        }
      }
    });

    // Draw tackle engagement if ballcarrier is in tackle
    const ballcarrierInTackle = simState.players.find(p => p.in_tackle);
    if (ballcarrierInTackle) {
      drawTackleEngagement(container, ballcarrierInTackle, simState.players);
    }

    simState.players.forEach(player => {
      const playerContainer = new Container();
      const screen = yardToScreen(player.x, player.y);

      const isReceiver = player.player_type === 'receiver';
      const isQB = player.player_type === 'qb';
      const isDefender = player.player_type === 'defender';
      const isOL = player.player_type === 'ol';
      const isDL = player.player_type === 'dl';
      const isSelected = player.id === selectedPlayerId;

      // Draw waypoints for selected receiver
      if (isReceiver && isSelected) {
        const waypoints = simState.waypoints[player.id];
        if (waypoints) {
          drawWaypoints(playerContainer, waypoints, player.current_waypoint || 0);
        }
      }

      // Draw anticipated position for selected defender
      if (isDefender && isSelected) {
        drawAnticipatedPosition(playerContainer, player);
      }

      // Skip some visual elements for QB
      if (isQB) {
        // Draw QB body
        const bodyG = new Graphics();
        const radius = 14;

        bodyG.circle(screen.x, screen.y, radius);
        bodyG.fill({ color: COLORS.qb });
        bodyG.stroke({ color: 0xffffff, width: 2 });

        // Has ball indicator
        if (player.has_ball) {
          bodyG.circle(screen.x, screen.y, radius - 4);
          bodyG.fill({ color: COLORS.ball });
        }

        playerContainer.addChild(bodyG);

        // QB label
        const nameLabel = new Text({
          text: 'QB',
          style: new TextStyle({
            fontSize: 12,
            fill: COLORS.text,
            fontWeight: 'bold',
          }),
        });
        nameLabel.anchor.set(0.5);
        nameLabel.x = screen.x;
        nameLabel.y = screen.y - 22;
        playerContainer.addChild(nameLabel);

        container.addChild(playerContainer);
        return; // Skip the rest for QB
      }

      // Draw trail from history
      const history = positionHistoryRef.current.get(player.id);
      if (history && history.length > 1) {
        const trailG = new Graphics();
        const trailColor = isReceiver ? COLORS.offenseTrail
          : isOL ? COLORS.olTrail
          : isDL ? COLORS.dlTrail
          : COLORS.defenseTrail;

        for (let i = 0; i < history.length; i++) {
          const pos = history[i];
          const pastScreen = yardToScreen(pos.x, pos.y);
          const alpha = (i / history.length) * 0.5;
          trailG.circle(pastScreen.x, pastScreen.y, 3);
          trailG.fill({ color: trailColor, alpha });
        }

        playerContainer.addChild(trailG);
      }

      // Draw velocity vector
      if (player.speed > 0.5) {
        const velG = new Graphics();
        const velScale = 0.3; // Scale factor for velocity display
        const velEnd = yardToScreen(
          player.x + player.vx * velScale,
          player.y + player.vy * velScale
        );

        velG.moveTo(screen.x, screen.y);
        velG.lineTo(velEnd.x, velEnd.y);
        velG.stroke({ color: COLORS.velocity, width: 2 });

        // Arrowhead
        const angle = Math.atan2(velEnd.y - screen.y, velEnd.x - screen.x);
        const arrowLen = 8;
        velG.moveTo(velEnd.x, velEnd.y);
        velG.lineTo(
          velEnd.x - arrowLen * Math.cos(angle - 0.4),
          velEnd.y - arrowLen * Math.sin(angle - 0.4)
        );
        velG.moveTo(velEnd.x, velEnd.y);
        velG.lineTo(
          velEnd.x - arrowLen * Math.cos(angle + 0.4),
          velEnd.y - arrowLen * Math.sin(angle + 0.4)
        );
        velG.stroke({ color: COLORS.velocity, width: 2 });

        playerContainer.addChild(velG);
      }

      // Draw player body
      const bodyG = new Graphics();
      const radius = isOL || isDL ? 14 : 12;  // OL/DL are bigger

      // Determine colors based on player type
      const baseColor = isOL ? COLORS.ol
        : isDL ? COLORS.dl
        : isDefender ? COLORS.defense
        : COLORS.offense;
      const lightColor = isOL ? COLORS.olLight
        : isDL ? COLORS.dlLight
        : isDefender ? COLORS.defenseLight
        : COLORS.offenseLight;

      // Selection ring
      if (isSelected) {
        bodyG.circle(screen.x, screen.y, radius + 4);
        bodyG.stroke({ color: COLORS.waypointCurrent, width: 2 });
      }

      // Body
      bodyG.circle(screen.x, screen.y, radius);
      bodyG.fill({ color: isSelected ? lightColor : baseColor });
      bodyG.stroke({ color: 0xffffff, width: 2 });

      // Cut indicator (magenta ring)
      if (player.cut_occurred) {
        bodyG.circle(screen.x, screen.y, radius + 8);
        bodyG.stroke({ color: COLORS.cutIndicator, width: 2, alpha: 0.8 });
      }

      // Max speed indicator (green ring)
      if (player.at_max_speed) {
        bodyG.circle(screen.x, screen.y, radius + 2);
        bodyG.stroke({ color: COLORS.velocity, width: 1 });
      }

      // Flip hips indicator for defenders (orange flash)
      if (isDefender && player.coverage_phase === 'flip_hips') {
        bodyG.circle(screen.x, screen.y, radius + 6);
        bodyG.stroke({ color: COLORS.waypointBreak, width: 3, alpha: 0.9 });
      }

      // Triggered indicator for zone defenders (yellow pulse)
      if (isDefender && player.has_triggered) {
        bodyG.circle(screen.x, screen.y, radius + 5);
        bodyG.stroke({ color: COLORS.anticipation, width: 2, alpha: 0.7 });
      }

      playerContainer.addChild(bodyG);

      // Player label
      const shortName = player.name.split(' ').pop() || player.name;
      const nameLabel = new Text({
        text: shortName,
        style: new TextStyle({
          fontSize: 11,
          fill: COLORS.text,
          fontWeight: isSelected ? 'bold' : 'normal',
        }),
      });
      nameLabel.anchor.set(0.5);
      nameLabel.x = screen.x;
      nameLabel.y = screen.y - 22;
      playerContainer.addChild(nameLabel);

      // Coverage phase indicator for selected defender
      if (isDefender && isSelected && player.coverage_phase) {
        const phaseLabel = new Text({
          text: player.coverage_phase.toUpperCase(),
          style: new TextStyle({
            fontSize: 8,
            fill: COLORS.textDim,
          }),
        });
        phaseLabel.anchor.set(0.5);
        phaseLabel.x = screen.x;
        phaseLabel.y = screen.y + 20;
        playerContainer.addChild(phaseLabel);
      }

      // DB recognition state indicator (? or !)
      if (isDefender) {
        drawRecognitionState(playerContainer, player, screen);
      }

      // Ballcarrier move indicator (juke/spin/truck flash)
      if (player.has_ball && player.current_move) {
        drawMoveIndicator(playerContainer, player, screen);
      }

      // Goal direction arrow for ballcarrier
      if (player.has_ball) {
        drawGoalDirection(playerContainer, player, screen);
      }

      // OL/DL position label
      if (isOL || isDL) {
        const posLabel = new Text({
          text: isOL ? 'OL' : 'DL',
          style: new TextStyle({
            fontSize: 8,
            fill: COLORS.textDim,
          }),
        });
        posLabel.anchor.set(0.5);
        posLabel.x = screen.x;
        posLabel.y = screen.y + 20;
        playerContainer.addChild(posLabel);
      }

      // Make clickable
      playerContainer.eventMode = 'static';
      playerContainer.cursor = 'pointer';
      playerContainer.on('pointerdown', () => onSelectPlayer(player.id));

      container.addChild(playerContainer);
    });

    // Draw ball if present
    if (simState.ball && simState.ball.state !== 'dead') {
      const ballContainer = new Container();
      const ballScreen = yardToScreen(simState.ball.x, simState.ball.y);
      const ballHeight = simState.ball.height ?? 2.0;  // Height in yards

      const ballG = new Graphics();

      if (simState.ball.state === 'in_flight') {
        // Draw arc trail showing the flight path
        if (simState.ball.flight_origin_x != null && simState.ball.flight_target_x != null) {
          const originScreen = yardToScreen(simState.ball.flight_origin_x, simState.ball.flight_origin_y!);
          const targetScreen = yardToScreen(simState.ball.flight_target_x, simState.ball.flight_target_y!);
          const peakHeight = simState.ball.peak_height ?? 3.0;
          const heightScale = 8;  // Pixels per yard of height

          // Draw arc trail with multiple points
          const numPoints = 20;
          const progress = simState.ball.flight_progress ?? 0;

          // Draw full projected arc (faded)
          ballG.moveTo(originScreen.x, originScreen.y);
          for (let i = 1; i <= numPoints; i++) {
            const t = i / numPoints;
            const x = originScreen.x + (targetScreen.x - originScreen.x) * t;
            const baseY = originScreen.y + (targetScreen.y - originScreen.y) * t;
            // Parabolic arc: 4 * peak * t * (1-t)
            const arcOffset = 4 * peakHeight * heightScale * t * (1 - t);
            const y = baseY - arcOffset;  // Subtract because screen Y is inverted
            ballG.lineTo(x, y);
          }
          ballG.stroke({ color: COLORS.ballTarget, width: 2, alpha: 0.3 });

          // Draw traveled portion of arc (solid)
          if (progress > 0) {
            ballG.moveTo(originScreen.x, originScreen.y);
            for (let i = 1; i <= Math.ceil(numPoints * progress); i++) {
              const t = Math.min(i / numPoints, progress);
              const x = originScreen.x + (targetScreen.x - originScreen.x) * t;
              const baseY = originScreen.y + (targetScreen.y - originScreen.y) * t;
              const arcOffset = 4 * peakHeight * heightScale * t * (1 - t);
              const y = baseY - arcOffset;
              ballG.lineTo(x, y);
            }
            ballG.stroke({ color: COLORS.ballInFlight, width: 3, alpha: 0.8 });
          }

          // Target marker on ground
          ballG.circle(targetScreen.x, targetScreen.y, 10);
          ballG.stroke({ color: COLORS.ballTarget, width: 2 });
          ballG.moveTo(targetScreen.x - 6, targetScreen.y);
          ballG.lineTo(targetScreen.x + 6, targetScreen.y);
          ballG.stroke({ color: COLORS.ballTarget, width: 2 });
          ballG.moveTo(targetScreen.x, targetScreen.y - 6);
          ballG.lineTo(targetScreen.x, targetScreen.y + 6);
          ballG.stroke({ color: COLORS.ballTarget, width: 2 });
        }

        // Calculate ball's visual Y offset based on height (2.5D effect)
        const heightOffset = ballHeight * 8;  // 8 pixels per yard of height

        // Draw shadow on ground (ellipse, fades with height)
        const shadowAlpha = Math.max(0.1, 0.5 - ballHeight * 0.03);
        const shadowSize = Math.max(3, 8 - ballHeight * 0.3);
        ballG.ellipse(ballScreen.x, ballScreen.y, shadowSize, shadowSize * 0.5);
        ballG.fill({ color: 0x000000, alpha: shadowAlpha });

        // Draw vertical line connecting shadow to ball (height indicator)
        if (heightOffset > 5) {
          ballG.moveTo(ballScreen.x, ballScreen.y);
          ballG.lineTo(ballScreen.x, ballScreen.y - heightOffset);
          ballG.stroke({ color: 0xffffff, width: 1, alpha: 0.4 });
        }

        // Draw ball at elevated position
        const ballY = ballScreen.y - heightOffset;
        const ballSize = Math.max(5, 10 - ballHeight * 0.3);  // Smaller when higher (distance)

        // Ball glow/halo
        ballG.circle(ballScreen.x, ballY, ballSize + 3);
        ballG.fill({ color: COLORS.ballInFlight, alpha: 0.3 });

        // Ball (gold, with white outline)
        ballG.circle(ballScreen.x, ballY, ballSize);
        ballG.fill({ color: COLORS.ballInFlight });
        ballG.stroke({ color: 0xffffff, width: 2 });

        // Throw type label
        const throwType = simState.ball.throw_type ?? 'bullet';
        const typeLabel = new Text({
          text: throwType.toUpperCase(),
          style: new TextStyle({
            fontSize: 9,
            fontWeight: 'bold',
            fill: 0xffffff,
          }),
        });
        typeLabel.anchor.set(0.5);
        typeLabel.x = ballScreen.x;
        typeLabel.y = ballY - ballSize - 8;
        ballContainer.addChild(typeLabel);

      } else {
        // Ball held or loose (brown, smaller)
        ballG.circle(ballScreen.x, ballScreen.y, 5);
        ballG.fill({ color: COLORS.ball });
        ballG.stroke({ color: 0xffffff, width: 1 });
      }

      ballContainer.addChild(ballG);
      container.addChild(ballContainer);
    }

    // Draw catch effects (in effects container, on top of everything)
    if (effectsContainerRef.current) {
      effectsContainerRef.current.removeChildren();
      drawCatchEffects(effectsContainerRef.current);
    }
  }, [simState, selectedPlayerId, yardToScreen, onSelectPlayer, drawCatchEffects]);

  return <div ref={canvasRef} className="v2-sim-canvas" />;
}
