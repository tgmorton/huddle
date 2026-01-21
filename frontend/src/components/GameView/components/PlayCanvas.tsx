/**
 * PlayCanvas - PixiJS canvas for play visualization in spectator mode
 *
 * Displays player movement during plays with:
 * - Vertical field orientation (downfield = north/up)
 * - Player circles with labels
 * - Route waypoints and lines
 * - Coverage assignment lines
 * - Motion trails
 * - Ball visualization
 *
 * Ported from SimAnalyzer/SimCanvas.tsx with vertical orientation.
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { Application, Graphics, Text, TextStyle, Container } from 'pixi.js';

// =============================================================================
// Types
// =============================================================================

export type PlayerType = 'qb' | 'receiver' | 'defender' | 'ol' | 'dl' | 'rb' | 'fb';
export type BallStateType = 'dead' | 'held' | 'in_flight' | 'loose';

export interface PlayerFrame {
  id: string;
  name: string;
  team: 'offense' | 'defense';
  position: string;
  player_type: PlayerType;
  x: number;
  y: number;
  vx: number;
  vy: number;
  speed: number;
  facing_x?: number;
  facing_y?: number;
  has_ball?: boolean;
  is_engaged?: boolean;

  // Route info
  route_name?: string;
  route_phase?: string;
  current_waypoint?: number;
  total_waypoints?: number;
  target_x?: number;
  target_y?: number;

  // Coverage info
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

export interface BallFrame {
  x: number;
  y: number;
  height: number;
  state: BallStateType;
  carrier_id: string | null;
}

export interface PlayFrame {
  tick: number;
  time: number;
  phase: string;
  players: PlayerFrame[];
  ball: BallFrame;
  waypoints: Record<string, WaypointFrame[]>;
}

// =============================================================================
// Canvas Configuration (Vertical Orientation)
// =============================================================================

const FIELD_WIDTH_YARDS = 53.33;  // NFL field width
const PIXELS_PER_YARD = 12;       // Slightly smaller for vertical layout
const FIELD_PADDING = 16;

// Canvas dimensions - taller for vertical field
const CANVAS_WIDTH = Math.ceil(FIELD_WIDTH_YARDS * PIXELS_PER_YARD) + FIELD_PADDING * 2;
const CANVAS_HEIGHT = 600;  // Show about 50 yards of field

const FIELD_CENTER_X = CANVAS_WIDTH / 2;
// LOS positioned in lower third to show more downfield
const LOS_SCREEN_Y = CANVAS_HEIGHT - 120;

// =============================================================================
// Color Palette
// =============================================================================

const COLORS = {
  // Field
  field: 0x2d5a27,
  fieldDark: 0x1e4620,
  fieldLines: 0xffffff,
  los: 0xfbbf24,
  hashMarks: 0xcccccc,

  // Offense
  offense: 0xf8fafc,
  offenseTrail: 0x94a3b8,
  qb: 0xfbbf24,
  ol: 0xe2e8f0,
  rb: 0x60a5fa,
  fb: 0x3b82f6,

  // Defense
  defense: 0xdc2626,
  defenseTrail: 0x991b1b,
  dl: 0xb91c1c,

  // Ball
  ball: 0x92400e,
  ballInFlight: 0xfbbf24,

  // Routes and coverage
  route: 0x60a5fa,
  routeBreak: 0xf97316,
  coverageLine: 0xff6b6b,
  waypointCurrent: 0xfbbf24,

  // Text
  text: 0xffffff,
};

// =============================================================================
// PlayCanvas Component
// =============================================================================

interface PlayCanvasProps {
  frames: PlayFrame[];
  currentTick: number;
  isPlaying: boolean;
  playbackSpeed: number;
  onTickChange: (tick: number) => void;
  onComplete?: () => void;
  width?: number;
  height?: number;
}

export function PlayCanvas({
  frames,
  currentTick,
  isPlaying,
  playbackSpeed,
  onTickChange,
  onComplete,
  width,
  height,
}: PlayCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const playersContainerRef = useRef<Container | null>(null);
  const fieldContainerRef = useRef<Container | null>(null);
  const analysisContainerRef = useRef<Container | null>(null);

  // Position history for trails (player_id -> positions)
  const positionHistoryRef = useRef<Map<string, Array<{ x: number; y: number }>>>(new Map());

  // Animation frame reference
  const animationRef = useRef<number | null>(null);
  const lastTickTimeRef = useRef<number>(0);

  // Canvas dimensions (allow override)
  const canvasWidth = width || CANVAS_WIDTH;
  const canvasHeight = height || CANVAS_HEIGHT;

  // Convert yard coordinates to screen coordinates (VERTICAL orientation)
  // X: lateral position (left-right on field)
  // Y: depth from LOS (positive = downfield = UP on screen)
  const yardToScreen = useCallback((x: number, y: number): { x: number; y: number } => {
    return {
      x: FIELD_CENTER_X + x * PIXELS_PER_YARD,
      y: LOS_SCREEN_Y - y * PIXELS_PER_YARD,  // Y flipped: positive yards = up
    };
  }, []);

  // Draw field elements
  const drawField = useCallback((container: Container) => {
    container.removeChildren();

    const g = new Graphics();

    // Field boundaries
    const sidelineOffsetYards = FIELD_WIDTH_YARDS / 2;
    const fieldLeft = FIELD_CENTER_X - sidelineOffsetYards * PIXELS_PER_YARD;
    const fieldRight = FIELD_CENTER_X + sidelineOffsetYards * PIXELS_PER_YARD;

    // Yard range to draw (-10 backfield to +40 downfield)
    const yardMin = -10;
    const yardMax = 40;

    // Draw grass stripes
    for (let y = yardMin; y <= yardMax; y += 5) {
      const screenY1 = LOS_SCREEN_Y - y * PIXELS_PER_YARD;
      const screenY2 = LOS_SCREEN_Y - (y + 5) * PIXELS_PER_YARD;
      const stripeColor = Math.floor((y + 10) / 5) % 2 === 0 ? COLORS.field : COLORS.fieldDark;

      g.rect(fieldLeft, screenY2, fieldRight - fieldLeft, screenY1 - screenY2);
      g.fill({ color: stripeColor });
    }

    // Out of bounds (darker green)
    g.rect(0, 0, fieldLeft, canvasHeight);
    g.fill({ color: 0x1a3318 });
    g.rect(fieldRight, 0, canvasWidth - fieldRight, canvasHeight);
    g.fill({ color: 0x1a3318 });

    // LOS (at y=0)
    g.moveTo(fieldLeft, LOS_SCREEN_Y);
    g.lineTo(fieldRight, LOS_SCREEN_Y);
    g.stroke({ color: COLORS.los, width: 3 });

    // Yard lines every 5 yards
    for (let y = yardMin; y <= yardMax; y += 5) {
      if (y === 0) continue;
      const screenY = LOS_SCREEN_Y - y * PIXELS_PER_YARD;
      g.moveTo(fieldLeft, screenY);
      g.lineTo(fieldRight, screenY);
      g.stroke({ color: COLORS.fieldLines, width: 1.5, alpha: 0.6 });

      // Yard numbers
      if (y > 0 && y % 10 === 0 && y <= 35) {
        const label = new Text({
          text: y.toString(),
          style: new TextStyle({
            fontSize: 14,
            fill: COLORS.fieldLines,
            fontWeight: 'bold',
          }),
        });
        label.anchor.set(0.5);
        label.x = fieldLeft + 20;
        label.y = screenY;
        label.alpha = 0.4;
        container.addChild(label);
      }
    }

    // Hash marks
    const hashOffset = 6.17; // Yards from center
    for (let y = yardMin; y <= yardMax; y += 1) {
      const screenY = LOS_SCREEN_Y - y * PIXELS_PER_YARD;

      // Left hash
      const hashLeftX = FIELD_CENTER_X - hashOffset * PIXELS_PER_YARD;
      g.moveTo(hashLeftX - 3, screenY);
      g.lineTo(hashLeftX + 3, screenY);
      g.stroke({ color: COLORS.fieldLines, width: 1, alpha: 0.4 });

      // Right hash
      const hashRightX = FIELD_CENTER_X + hashOffset * PIXELS_PER_YARD;
      g.moveTo(hashRightX - 3, screenY);
      g.lineTo(hashRightX + 3, screenY);
      g.stroke({ color: COLORS.fieldLines, width: 1, alpha: 0.4 });
    }

    // Sidelines
    g.moveTo(fieldLeft, 0);
    g.lineTo(fieldLeft, canvasHeight);
    g.stroke({ color: COLORS.fieldLines, width: 3 });

    g.moveTo(fieldRight, 0);
    g.lineTo(fieldRight, canvasHeight);
    g.stroke({ color: COLORS.fieldLines, width: 3 });

    container.addChild(g);

    // LOS label
    const losLabel = new Text({
      text: 'LOS',
      style: new TextStyle({
        fontSize: 10,
        fill: COLORS.los,
        fontWeight: 'bold',
        fontFamily: 'monospace',
      }),
    });
    losLabel.x = fieldRight + 4;
    losLabel.y = LOS_SCREEN_Y - 5;
    container.addChild(losLabel);
  }, [canvasWidth, canvasHeight]);

  // Draw a single player
  const drawPlayer = useCallback((
    container: Container,
    player: PlayerFrame,
    yardToScreenFn: (x: number, y: number) => { x: number; y: number }
  ) => {
    const screen = yardToScreenFn(player.x, player.y);
    const g = new Graphics();

    // Determine color based on player type
    let color = player.team === 'offense' ? COLORS.offense : COLORS.defense;
    if (player.player_type === 'qb') color = COLORS.qb;
    else if (player.player_type === 'ol') color = COLORS.ol;
    else if (player.player_type === 'dl') color = COLORS.dl;
    else if (player.player_type === 'rb') color = COLORS.rb;
    else if (player.player_type === 'fb') color = COLORS.fb;

    // Circle radius
    const radius = player.player_type === 'ol' || player.player_type === 'dl' ? 10 : 8;

    // Draw body circle
    g.circle(screen.x, screen.y, radius);
    g.fill({ color });
    g.stroke({ color: 0xffffff, width: 1.5 });

    // Ball indicator
    if (player.has_ball || player.is_ball_carrier) {
      g.circle(screen.x, screen.y, radius - 3);
      g.fill({ color: COLORS.ball });
    }

    container.addChild(g);

    // Player label (jersey number or short name)
    const displayName = player.name.length > 3 ? player.name.substring(0, 2) : player.name;
    const label = new Text({
      text: displayName,
      style: new TextStyle({
        fontSize: 9,
        fill: COLORS.text,
        fontFamily: 'monospace',
      }),
    });
    label.anchor.set(0.5);
    label.x = screen.x;
    label.y = screen.y - radius - 8;
    container.addChild(label);
  }, []);

  // Draw route waypoints
  const drawWaypoints = useCallback((
    container: Container,
    waypoints: WaypointFrame[],
    currentWaypoint: number,
    yardToScreenFn: (x: number, y: number) => { x: number; y: number }
  ) => {
    const g = new Graphics();

    // Draw connecting lines
    for (let i = 0; i < waypoints.length - 1; i++) {
      const from = yardToScreenFn(waypoints[i].x, waypoints[i].y);
      const to = yardToScreenFn(waypoints[i + 1].x, waypoints[i + 1].y);

      g.moveTo(from.x, from.y);
      g.lineTo(to.x, to.y);
      g.stroke({
        color: i < currentWaypoint ? COLORS.route : 0x60a5fa,
        width: 2,
        alpha: i < currentWaypoint ? 0.4 : 0.7,
      });
    }

    // Draw waypoint markers
    waypoints.forEach((wp, i) => {
      const screen = yardToScreenFn(wp.x, wp.y);
      const radius = i === currentWaypoint ? 5 : wp.is_break ? 4 : 3;
      const color = i === currentWaypoint ? COLORS.waypointCurrent :
                    wp.is_break ? COLORS.routeBreak : COLORS.route;

      g.circle(screen.x, screen.y, radius);
      g.fill({ color, alpha: i < currentWaypoint ? 0.4 : 0.8 });
    });

    container.addChild(g);
  }, []);

  // Draw coverage lines (man-to-man)
  const drawCoverageLines = useCallback((
    container: Container,
    players: PlayerFrame[],
    yardToScreenFn: (x: number, y: number) => { x: number; y: number }
  ) => {
    const g = new Graphics();

    // Find defenders with man assignments
    const defenders = players.filter(p => p.team === 'defense' && p.coverage_type === 'man' && p.man_target_id);

    defenders.forEach(defender => {
      const receiver = players.find(p => p.id === defender.man_target_id);
      if (!receiver) return;

      const defScreen = yardToScreenFn(defender.x, defender.y);
      const rcvScreen = yardToScreenFn(receiver.x, receiver.y);

      // Dashed line from defender to receiver
      g.moveTo(defScreen.x, defScreen.y);
      g.lineTo(rcvScreen.x, rcvScreen.y);
      g.stroke({ color: COLORS.coverageLine, width: 1, alpha: 0.4 });
    });

    container.addChild(g);
  }, []);

  // Draw motion trails
  const drawTrails = useCallback((
    container: Container,
    players: PlayerFrame[],
    yardToScreenFn: (x: number, y: number) => { x: number; y: number }
  ) => {
    const g = new Graphics();
    const maxHistory = 30;

    players.forEach(player => {
      // Get or create history
      let history = positionHistoryRef.current.get(player.id);
      if (!history) {
        history = [];
        positionHistoryRef.current.set(player.id, history);
      }

      // Add current position
      history.push({ x: player.x, y: player.y });
      if (history.length > maxHistory) {
        history.shift();
      }

      // Draw trail
      const trailColor = player.team === 'offense' ? COLORS.offenseTrail : COLORS.defenseTrail;
      history.forEach((pos, i) => {
        if (i === history.length - 1) return; // Skip current position
        const screen = yardToScreenFn(pos.x, pos.y);
        const alpha = (i / history.length) * 0.4;

        g.circle(screen.x, screen.y, 2);
        g.fill({ color: trailColor, alpha });
      });
    });

    container.addChild(g);
  }, []);

  // Draw ball
  const drawBall = useCallback((
    container: Container,
    ball: BallFrame,
    yardToScreenFn: (x: number, y: number) => { x: number; y: number }
  ) => {
    if (ball.state === 'held') return; // Ball shown on player when held

    const screen = yardToScreenFn(ball.x, ball.y);
    const g = new Graphics();

    // Ball size based on height
    const baseRadius = 4;
    const heightBonus = Math.min(ball.height / 5, 2);
    const radius = baseRadius + heightBonus;

    const color = ball.state === 'in_flight' ? COLORS.ballInFlight : COLORS.ball;

    g.circle(screen.x, screen.y, radius);
    g.fill({ color });
    g.stroke({ color: 0xffffff, width: 1 });

    container.addChild(g);
  }, []);

  // Render current frame
  const renderFrame = useCallback((frame: PlayFrame) => {
    if (!playersContainerRef.current || !analysisContainerRef.current) return;

    // Clear containers
    playersContainerRef.current.removeChildren();
    analysisContainerRef.current.removeChildren();

    // Draw analysis elements
    drawTrails(analysisContainerRef.current, frame.players, yardToScreen);
    drawCoverageLines(analysisContainerRef.current, frame.players, yardToScreen);

    // Draw routes for receivers
    frame.players.forEach(player => {
      if (player.route_name && frame.waypoints[player.id]) {
        drawWaypoints(
          analysisContainerRef.current!,
          frame.waypoints[player.id],
          player.current_waypoint || 0,
          yardToScreen
        );
      }
    });

    // Draw players
    frame.players.forEach(player => {
      drawPlayer(playersContainerRef.current!, player, yardToScreen);
    });

    // Draw ball
    drawBall(playersContainerRef.current!, frame.ball, yardToScreen);
  }, [yardToScreen, drawPlayer, drawWaypoints, drawCoverageLines, drawTrails, drawBall]);

  // Initialize PixiJS
  useEffect(() => {
    if (!canvasRef.current || appRef.current) return;

    let mounted = true;

    const init = async () => {
      const app = new Application();
      await app.init({
        width: canvasWidth,
        height: canvasHeight,
        backgroundColor: COLORS.field,
        antialias: true,
        resolution: Math.min(window.devicePixelRatio || 1, 2),
        autoDensity: true,
      });

      if (!mounted || !canvasRef.current) {
        app.destroy(true);
        return;
      }

      canvasRef.current.appendChild(app.canvas);
      appRef.current = app;

      // Create containers
      const fieldContainer = new Container();
      app.stage.addChild(fieldContainer);
      fieldContainerRef.current = fieldContainer;

      const analysisContainer = new Container();
      app.stage.addChild(analysisContainer);
      analysisContainerRef.current = analysisContainer;

      const playersContainer = new Container();
      app.stage.addChild(playersContainer);
      playersContainerRef.current = playersContainer;

      // Draw field
      drawField(fieldContainer);
    };

    init();

    return () => {
      mounted = false;
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      if (appRef.current) {
        appRef.current.destroy(true);
        appRef.current = null;
      }
    };
  }, [canvasWidth, canvasHeight, drawField]);

  // Animation loop
  useEffect(() => {
    if (!isPlaying || frames.length === 0) {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
      return;
    }

    const msPerTick = 50 / playbackSpeed;  // 20 ticks/sec base rate
    lastTickTimeRef.current = performance.now();

    const animate = (timestamp: number) => {
      const elapsed = timestamp - lastTickTimeRef.current;

      if (elapsed >= msPerTick) {
        const newTick = currentTick + 1;

        if (newTick >= frames.length) {
          // Animation complete
          onComplete?.();
          return;
        }

        onTickChange(newTick);
        lastTickTimeRef.current = timestamp;
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isPlaying, playbackSpeed, currentTick, frames.length, onTickChange, onComplete]);

  // Render current frame when tick changes
  useEffect(() => {
    if (frames.length === 0) return;

    const frameIndex = Math.min(currentTick, frames.length - 1);
    const frame = frames[frameIndex];

    if (frame) {
      renderFrame(frame);
    }
  }, [currentTick, frames, renderFrame]);

  // Clear trails when frames change (new play)
  useEffect(() => {
    positionHistoryRef.current.clear();
  }, [frames]);

  return (
    <div
      ref={canvasRef}
      className="play-canvas"
      style={{
        width: canvasWidth,
        height: canvasHeight,
        overflow: 'hidden',
        borderRadius: 'var(--radius-md)',
      }}
    />
  );
}

export default PlayCanvas;
