/**
 * SimCanvas - PixiJS canvas for simulation visualization
 *
 * Supports two modes:
 * - Analysis Mode: Shows coverage zones, separation lines, pursuit lines, cognitive delays
 * - View Mode: Clean broadcast-style visualization
 *
 * Uses ManagementV2 color palette for consistency.
 */

import { useEffect, useRef, useCallback } from 'react';
import { Application, Graphics, Text, TextStyle, Container } from 'pixi.js';
import type { SimState, PlayerState, WaypointData, ZoneBoundary, BallState, GapType } from './types';

// Canvas configuration
const FIELD_WIDTH_YARDS = 53.33;  // NFL field width
const PIXELS_PER_YARD = 15;
const FIELD_PADDING = 24;

const CANVAS_WIDTH = Math.ceil(FIELD_WIDTH_YARDS * PIXELS_PER_YARD) + FIELD_PADDING * 2;
const CANVAS_HEIGHT = 700;

const FIELD_CENTER_X = CANVAS_WIDTH / 2;
// Move LOS higher to show more backfield (-8 to +35 yards view)
const LOS_Y_NORMAL = CANVAS_HEIGHT - 160;
// In zoom mode, center LOS vertically with slight offset for backfield view
const LOS_Y_ZOOMED = CANVAS_HEIGHT / 2 + 80;
const ZOOM_FACTOR = 2.0;

// Color palette - green field with ManagementV2 accents
const COLORS = {
  // Field - classic football green
  field: 0x2d5a27,         // Natural grass green
  fieldDark: 0x1e4620,     // Darker stripe
  fieldLines: 0xffffff,    // White lines
  los: 0xfbbf24,           // Yellow/gold LOS
  hashMarks: 0xcccccc,     // Light gray hashes
  endzone: 0x1a3d18,       // Darker endzone

  // Players - Offense (white/silver)
  offense: 0xf8fafc,       // Near white
  offenseLight: 0xffffff,
  offenseTrail: 0x94a3b8,
  offenseGlow: 0x3b82f6,   // Blue glow

  // Players - Defense (red)
  defense: 0xdc2626,       // Red
  defenseLight: 0xef4444,
  defenseTrail: 0x991b1b,
  defenseGlow: 0xef4444,

  // QB (gold jersey)
  qb: 0xfbbf24,            // Gold
  qbLight: 0xfcd34d,

  // OL (white with blue trim)
  ol: 0xe2e8f0,
  olLight: 0xf1f5f9,

  // DL (red)
  dl: 0xb91c1c,
  dlLight: 0xdc2626,

  // RB (blue-tinted offense)
  rb: 0x60a5fa,
  rbLight: 0x93c5fd,

  // FB (darker blue)
  fb: 0x3b82f6,
  fbLight: 0x60a5fa,

  // Ball
  ball: 0x92400e,          // Football brown
  ballInFlight: 0xfbbf24,  // Gold when thrown
  ballTarget: 0xef4444,    // Red target

  // Analysis overlays
  coverageLine: 0xff6b6b,  // Soft red
  zoneBoundary: 0xa855f7,  // Purple
  zoneBoundaryDeep: 0x7c3aed,
  separation: 0xfbbf24,
  recognizing: 0xfbbf24,   // Gold while processing
  recognized: 0x22c55e,    // Green when recognized
  pursuitLine: 0xf472b6,   // Pink

  // Route waypoints
  waypoint: 0x60a5fa,      // Blue
  waypointDone: 0x64748b,  // Slate
  waypointCurrent: 0xfbbf24,
  waypointBreak: 0xf97316, // Orange

  // Read progression
  readNumber: 0xffffff,
  readCurrent: 0xfbbf24,

  // Text
  text: 0xffffff,
  textDim: 0xd4d4d8,
  textMuted: 0xa1a1aa,

  // Run game
  gap: 0x22c55e,              // Green for gaps
  gapClosed: 0xef4444,        // Red for closed gaps
  gapDesigned: 0xfbbf24,      // Gold for designed gap
  blockEngaged: 0xf97316,     // Orange for engaged blocks
  blockWinning: 0x22c55e,     // Green for winning
  blockLosing: 0xef4444,      // Red for losing/shed
  pullPath: 0xa855f7,         // Purple for pulling linemen
  rbVision: 0x3b82f6,         // Blue for RB vision line
  rbReadPoint: 0xfbbf24,      // Gold for RB read point
};

interface SimCanvasProps {
  simState: SimState | null;
  analysisMode: boolean;
  showZones: boolean;
  runZoom: boolean;  // Zoomed-in view for run plays
  selectedPlayerId: string | null;
  onSelectPlayer: (id: string | null) => void;
  tacklerId?: string | null;  // Highlight the tackler when tackle occurs
}

export function SimCanvas({
  simState,
  analysisMode,
  showZones,
  runZoom,
  selectedPlayerId,
  onSelectPlayer,
  tacklerId,
}: SimCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const playersContainerRef = useRef<Container | null>(null);
  const analysisContainerRef = useRef<Container | null>(null);
  const fieldContainerRef = useRef<Container | null>(null);

  // Position history for trails
  const positionHistoryRef = useRef<Map<string, Array<{ x: number; y: number }>>>(new Map());

  // Convert yard coordinates to screen coordinates
  // When runZoom is enabled, zoom in 2x and center on line of scrimmage
  const yardToScreen = useCallback((x: number, y: number): { x: number; y: number } => {
    if (runZoom) {
      const zoomedPPY = PIXELS_PER_YARD * ZOOM_FACTOR;
      return {
        x: FIELD_CENTER_X + x * zoomedPPY,
        y: LOS_Y_ZOOMED - y * zoomedPPY,
      };
    }
    return {
      x: FIELD_CENTER_X + x * PIXELS_PER_YARD,
      y: LOS_Y_NORMAL - y * PIXELS_PER_YARD,
    };
  }, [runZoom]);

  // Draw field elements - redraws when runZoom changes
  const drawField = useCallback((container: Container, isZoomed: boolean) => {
    container.removeChildren();

    const zoomFactor = isZoomed ? ZOOM_FACTOR : 1.0;
    const ppy = PIXELS_PER_YARD * zoomFactor;
    // In zoom mode, LOS is centered; in normal mode, use fixed position
    const losScreenY = isZoomed ? LOS_Y_ZOOMED : LOS_Y_NORMAL;

    // Helper to convert yard Y to screen Y
    const yardYToScreen = (y: number) => losScreenY - y * ppy;
    // Helper to convert yard X to screen X (for zoomed sidelines)
    const yardXToScreen = (x: number) => FIELD_CENTER_X + x * ppy;

    const g = new Graphics();

    // Field boundaries depend on zoom
    const sidelineOffsetYards = FIELD_WIDTH_YARDS / 2;
    const fieldLeft = yardXToScreen(-sidelineOffsetYards);
    const fieldRight = yardXToScreen(sidelineOffsetYards);

    // Yard range to draw (extend range in zoomed mode to fill canvas)
    const yardMin = isZoomed ? -8 : -10;
    const yardMax = isZoomed ? 15 : 40;

    // Draw grass stripes (alternating light/dark every 5 yards)
    for (let y = yardMin; y <= yardMax; y += 5) {
      const screenY1 = yardYToScreen(y);
      const screenY2 = yardYToScreen(y + 5);
      const stripeColor = Math.floor((y + 10) / 5) % 2 === 0 ? COLORS.field : COLORS.fieldDark;

      g.rect(fieldLeft, screenY2, fieldRight - fieldLeft, screenY1 - screenY2);
      g.fill({ color: stripeColor });
    }

    // Out of bounds areas (darker)
    g.rect(0, 0, fieldLeft, CANVAS_HEIGHT);
    g.fill({ color: 0x1a3318, alpha: 1 });
    g.rect(fieldRight, 0, CANVAS_WIDTH - fieldRight, CANVAS_HEIGHT);
    g.fill({ color: 0x1a3318, alpha: 1 });

    // Draw LOS first (always at y=0)
    const losScreenY_line = yardYToScreen(0);
    g.moveTo(fieldLeft, losScreenY_line);
    g.lineTo(fieldRight, losScreenY_line);
    g.stroke({ color: COLORS.los, width: 3, alpha: 1 });

    // Yard lines every 5 yards (skip LOS since we drew it above)
    for (let y = yardMin; y <= yardMax; y += 5) {
      if (y === 0) continue; // Already drew LOS
      const screenY = yardYToScreen(y);
      // White yard lines
      g.moveTo(fieldLeft, screenY);
      g.lineTo(fieldRight, screenY);
      g.stroke({ color: COLORS.fieldLines, width: 2, alpha: 0.7 });

      // Yard numbers (on field)
      if (y > 0 && y % 10 === 0 && y <= 35) {
        const yardNum = y.toString();
        const fontSize = isZoomed ? 28 : 20;
        const labelOffset = isZoomed ? 50 : 30;

        const leftLabel = new Text({
          text: yardNum,
          style: new TextStyle({
            fontSize,
            fill: COLORS.fieldLines,
            fontWeight: 'bold',
            fontFamily: 'Arial, sans-serif',
          }),
        });
        leftLabel.anchor.set(0.5);
        leftLabel.x = fieldLeft + labelOffset;
        leftLabel.y = screenY;
        leftLabel.alpha = 0.4;
        container.addChild(leftLabel);

        const rightLabel = new Text({
          text: yardNum,
          style: new TextStyle({
            fontSize,
            fill: COLORS.fieldLines,
            fontWeight: 'bold',
            fontFamily: 'Arial, sans-serif',
          }),
        });
        rightLabel.anchor.set(0.5);
        rightLabel.x = fieldRight - labelOffset;
        rightLabel.y = screenY;
        rightLabel.alpha = 0.4;
        container.addChild(rightLabel);
      }
    }

    // Hash marks (NFL: 70'9" from sideline = ~23.6 yards from center)
    const hashOffsetYards = 18.5 / 3;
    const hashLeft = yardXToScreen(-hashOffsetYards);
    const hashRight = yardXToScreen(hashOffsetYards);
    const hashWidth = isZoomed ? 5 : 3;

    for (let y = yardMin; y <= yardMax; y += 1) {
      const screenY = yardYToScreen(y);

      // Left hash
      g.moveTo(hashLeft - hashWidth, screenY);
      g.lineTo(hashLeft + hashWidth, screenY);
      g.stroke({ color: COLORS.fieldLines, width: 1, alpha: 0.5 });

      // Right hash
      g.moveTo(hashRight - hashWidth, screenY);
      g.lineTo(hashRight + hashWidth, screenY);
      g.stroke({ color: COLORS.fieldLines, width: 1, alpha: 0.5 });
    }

    // Sidelines (thick white) - only visible if on screen
    if (fieldLeft > 0) {
      g.moveTo(fieldLeft, 0);
      g.lineTo(fieldLeft, CANVAS_HEIGHT);
      g.stroke({ color: COLORS.fieldLines, width: 4, alpha: 1 });
    }

    if (fieldRight < CANVAS_WIDTH) {
      g.moveTo(fieldRight, 0);
      g.lineTo(fieldRight, CANVAS_HEIGHT);
      g.stroke({ color: COLORS.fieldLines, width: 4, alpha: 1 });
    }

    container.addChild(g);

    // LOS label (in margin if visible)
    const losLabelX = Math.min(fieldRight + 6, CANVAS_WIDTH - 30);
    const losLabel = new Text({
      text: 'LOS',
      style: new TextStyle({
        fontSize: isZoomed ? 12 : 10,
        fill: COLORS.los,
        fontWeight: 'bold',
        fontFamily: 'Berkeley Mono, SF Mono, monospace',
      }),
    });
    losLabel.x = losLabelX;
    losLabel.y = losScreenY - 5;
    container.addChild(losLabel);
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
        resolution: Math.min(window.devicePixelRatio || 1, 2),  // Cap at 2x for performance
        autoDensity: true,  // Auto-scale CSS to match resolution
      });

      if (!mounted || !canvasRef.current) {
        app.destroy(true);
        return;
      }

      canvasRef.current.appendChild(app.canvas);
      appRef.current = app;

      // Container for field elements (redrawn when zoom changes)
      const fieldContainer = new Container();
      app.stage.addChild(fieldContainer);
      fieldContainerRef.current = fieldContainer;

      // Container for analysis overlays (below players)
      const analysisContainer = new Container();
      app.stage.addChild(analysisContainer);
      analysisContainerRef.current = analysisContainer;

      // Container for dynamic elements
      const playersContainer = new Container();
      app.stage.addChild(playersContainer);
      playersContainerRef.current = playersContainer;

      // Draw field immediately after init (effect may have already run)
      drawField(fieldContainer, runZoom);
    };

    init();

    return () => {
      mounted = false;
      if (appRef.current) {
        appRef.current.destroy(true);
        appRef.current = null;
      }
    };
  }, [drawField]);

  // Redraw field when runZoom changes
  useEffect(() => {
    if (fieldContainerRef.current) {
      drawField(fieldContainerRef.current, runZoom);
    }
  }, [runZoom, drawField]);

  // Update position history
  useEffect(() => {
    if (!simState) return;

    const history = positionHistoryRef.current;
    simState.players.forEach(player => {
      if (!history.has(player.id)) {
        history.set(player.id, []);
      }
      const playerHistory = history.get(player.id)!;
      playerHistory.push({ x: player.x, y: player.y });
      if (playerHistory.length > 40) {
        playerHistory.shift();
      }
    });
  }, [simState]);

  // Clear history on reset
  useEffect(() => {
    if (simState?.tick === 0) {
      positionHistoryRef.current.clear();
    }
  }, [simState?.tick]);

  // Main render loop
  useEffect(() => {
    if (!simState || !playersContainerRef.current || !analysisContainerRef.current) return;

    const playersContainer = playersContainerRef.current;
    const analysisContainer = analysisContainerRef.current;

    // Clear previous frame
    playersContainer.removeChildren();
    analysisContainer.removeChildren();

    // Note: selectedPlayer lookup available if needed:
    // const selectedPlayer = simState.players.find(p => p.id === selectedPlayerId);

    // Analysis mode: Draw overlays first (behind players)
    if (analysisMode) {
      // Draw zone boundaries (only if showZones is enabled)
      if (showZones) {
        Object.entries(simState.zone_boundaries).forEach(([zoneType, zone]) => {
          drawZoneBoundary(analysisContainer, zoneType, zone);
        });
      }

      // Draw coverage lines (man coverage)
      simState.players
        .filter(p => p.player_type === 'defender' && p.coverage_type === 'man' && p.man_target_id)
        .forEach(defender => {
          const target = simState.players.find(p => p.id === defender.man_target_id);
          if (target) {
            drawCoverageLine(analysisContainer, defender, target);
          }
        });

      // Draw pursuit lines
      simState.players
        .filter(p => p.pursuit_target_x !== undefined)
        .forEach(player => {
          drawPursuitLine(analysisContainer, player);
        });

      // Run game visualizations
      if (simState.is_run_play || runZoom) {
        const olPlayers = simState.players.filter(p => p.player_type === 'ol');

        // Draw gap indicators
        drawGapIndicators(analysisContainer, olPlayers, simState.designed_gap);

        // Draw blocking engagements with shed progress
        drawBlockingEngagements(analysisContainer, simState.players);

        // Draw OL blocking assignments
        drawBlockingAssignments(analysisContainer, olPlayers);

        // Draw RB vision if ballcarrier is an RB
        const rb = simState.players.find(p =>
          p.has_ball && (p.position === 'RB' || p.position === 'HB' || p.position === 'FB')
        );
        if (rb) {
          drawRBVision(analysisContainer, rb);
        }
      }
    }

    // Draw route waypoints for receivers (in analysis mode or when selected)
    simState.players
      .filter(p => p.player_type === 'receiver')
      .forEach(receiver => {
        const waypoints = simState.waypoints[receiver.id];
        if (waypoints && (analysisMode || receiver.id === selectedPlayerId)) {
          drawRouteWaypoints(playersContainer, waypoints, receiver.current_waypoint || 0, receiver.id === selectedPlayerId);
        }
      });

    // Draw players
    simState.players.forEach(player => {
      const isTackler = tacklerId === player.id && simState.is_complete;
      drawPlayer(playersContainer, player, selectedPlayerId === player.id, analysisMode, isTackler);
    });

    // Draw ball
    if (simState.ball && simState.ball.state !== 'dead') {
      drawBall(playersContainer, simState.ball);
    }

    // Draw tackle engagement visualization
    const ballcarrier = simState.players.find(p => p.in_tackle);
    if (ballcarrier && ballcarrier.tackle_leverage !== undefined) {
      drawTackleEngagement(playersContainer, ballcarrier, simState.players);
    }

    // Draw read progression numbers (analysis mode only)
    if (analysisMode) {
      simState.players
        .filter(p => p.player_type === 'receiver' && p.read_order)
        .forEach(receiver => {
          drawReadNumber(playersContainer, receiver, simState.qb_state?.current_read);
        });
    }
  }, [simState, selectedPlayerId, analysisMode, showZones, runZoom, yardToScreen, onSelectPlayer, tacklerId]);

  // Helper: Draw zone boundary
  const drawZoneBoundary = (container: Container, _zoneType: string, zone: ZoneBoundary) => {
    const g = new Graphics();
    const topLeft = yardToScreen(zone.min_x, zone.max_y);
    const bottomRight = yardToScreen(zone.max_x, zone.min_y);
    const width = bottomRight.x - topLeft.x;
    const height = bottomRight.y - topLeft.y;

    const color = zone.is_deep ? COLORS.zoneBoundaryDeep : COLORS.zoneBoundary;

    g.rect(topLeft.x, topLeft.y, width, height);
    g.fill({ color, alpha: 0.08 });
    g.stroke({ color, width: 1, alpha: 0.3 });

    // Zone anchor
    const anchor = yardToScreen(zone.anchor_x, zone.anchor_y);
    g.circle(anchor.x, anchor.y, 4);
    g.stroke({ color, width: 1, alpha: 0.5 });

    container.addChild(g);
  };

  // Helper: Draw coverage line (man coverage)
  const drawCoverageLine = (container: Container, defender: PlayerState, receiver: PlayerState) => {
    const g = new Graphics();
    const defScreen = yardToScreen(defender.x, defender.y);
    const rcvScreen = yardToScreen(receiver.x, receiver.y);

    // Dashed line for trailing, solid for in-phase
    const isTrailing = defender.coverage_phase === 'trailing' || defender.coverage_phase === 'trail';

    if (isTrailing) {
      // Dashed line
      const dx = rcvScreen.x - defScreen.x;
      const dy = rcvScreen.y - defScreen.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const nx = dx / dist;
      const ny = dy / dist;
      let pos = 0;

      while (pos < dist) {
        const startX = defScreen.x + nx * pos;
        const startY = defScreen.y + ny * pos;
        const endPos = Math.min(pos + 6, dist);
        const endX = defScreen.x + nx * endPos;
        const endY = defScreen.y + ny * endPos;

        g.moveTo(startX, startY);
        g.lineTo(endX, endY);
        pos += 10;
      }
      g.stroke({ color: COLORS.coverageLine, width: 1, alpha: 0.4 });
    } else {
      g.moveTo(defScreen.x, defScreen.y);
      g.lineTo(rcvScreen.x, rcvScreen.y);
      g.stroke({ color: COLORS.coverageLine, width: 1, alpha: 0.3 });
    }

    // Separation label at midpoint
    const midX = (defScreen.x + rcvScreen.x) / 2;
    const midY = (defScreen.y + rcvScreen.y) / 2;
    const dx = receiver.x - defender.x;
    const dy = receiver.y - defender.y;
    const separation = Math.sqrt(dx * dx + dy * dy);

    const label = new Text({
      text: `${separation.toFixed(1)}`,
      style: new TextStyle({
        fontSize: 9,
        fill: COLORS.separation,
        fontFamily: 'Berkeley Mono, SF Mono, monospace',
      }),
    });
    label.x = midX + 4;
    label.y = midY - 4;
    container.addChild(label);

    container.addChild(g);
  };

  // Helper: Draw pursuit line
  const drawPursuitLine = (container: Container, player: PlayerState) => {
    if (player.pursuit_target_x === undefined || player.pursuit_target_y === undefined) return;

    const g = new Graphics();
    const screen = yardToScreen(player.x, player.y);
    const target = yardToScreen(player.pursuit_target_x, player.pursuit_target_y);

    // Dashed line
    const dx = target.x - screen.x;
    const dy = target.y - screen.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const nx = dx / dist;
    const ny = dy / dist;
    let pos = 0;

    while (pos < dist) {
      const startX = screen.x + nx * pos;
      const startY = screen.y + ny * pos;
      const endPos = Math.min(pos + 6, dist);
      const endX = screen.x + nx * endPos;
      const endY = screen.y + ny * endPos;

      g.moveTo(startX, startY);
      g.lineTo(endX, endY);
      pos += 10;
    }
    g.stroke({ color: COLORS.pursuitLine, width: 2, alpha: 0.5 });

    // Target X marker
    g.moveTo(target.x - 4, target.y - 4);
    g.lineTo(target.x + 4, target.y + 4);
    g.moveTo(target.x + 4, target.y - 4);
    g.lineTo(target.x - 4, target.y + 4);
    g.stroke({ color: COLORS.pursuitLine, width: 2 });

    container.addChild(g);
  };

  // Helper: Draw route waypoints
  const drawRouteWaypoints = (
    container: Container,
    waypoints: WaypointData[],
    currentIdx: number,
    isSelected: boolean
  ) => {
    const g = new Graphics();

    // Draw connecting lines
    for (let i = 0; i < waypoints.length - 1; i++) {
      const wp1 = yardToScreen(waypoints[i].x, waypoints[i].y);
      const wp2 = yardToScreen(waypoints[i + 1].x, waypoints[i + 1].y);
      const color = i < currentIdx ? COLORS.waypointDone : COLORS.waypoint;
      const alpha = isSelected ? 0.6 : 0.3;

      g.moveTo(wp1.x, wp1.y);
      g.lineTo(wp2.x, wp2.y);
      g.stroke({ color, width: 2, alpha });
    }

    // Draw waypoint markers
    waypoints.forEach((wp, i) => {
      const screen = yardToScreen(wp.x, wp.y);
      let color: number;
      let radius: number;

      if (i < currentIdx) {
        color = COLORS.waypointDone;
        radius = 3;
      } else if (i === currentIdx) {
        color = COLORS.waypointCurrent;
        radius = 6;
      } else {
        color = wp.is_break ? COLORS.waypointBreak : COLORS.waypoint;
        radius = 4;
      }

      const alpha = isSelected ? 1 : 0.5;
      g.circle(screen.x, screen.y, radius);
      g.stroke({ color, width: 2, alpha });
    });

    container.addChild(g);
  };

  // Helper: Draw player
  const drawPlayer = (
    container: Container,
    player: PlayerState,
    isSelected: boolean,
    showAnalysis: boolean,
    isTackler: boolean = false
  ) => {
    const playerContainer = new Container();
    const screen = yardToScreen(player.x, player.y);

    const isQB = player.player_type === 'qb';
    const isReceiver = player.player_type === 'receiver';
    const isDefender = player.player_type === 'defender';
    const isOL = player.player_type === 'ol';
    const isDL = player.player_type === 'dl';
    const isRB = player.player_type === 'rb';
    const isFB = player.player_type === 'fb';
    const isOffense = isQB || isReceiver || isOL || isRB || isFB;
    const isDefense = isDefender || isDL;

    // Draw trail
    const history = positionHistoryRef.current.get(player.id);
    if (history && history.length > 1) {
      const trailG = new Graphics();
      const trailColor = isOffense
        ? COLORS.offenseTrail
        : isDefense
          ? COLORS.defenseTrail
          : COLORS.textMuted;

      for (let i = 0; i < history.length; i++) {
        const pos = history[i];
        const pastScreen = yardToScreen(pos.x, pos.y);
        const alpha = (i / history.length) * 0.4;
        trailG.circle(pastScreen.x, pastScreen.y, 2);
        trailG.fill({ color: trailColor, alpha });
      }
      playerContainer.addChild(trailG);
    }

    // Player body
    const bodyG = new Graphics();
    const radius = isOL || isDL ? 12 : 10;

    // Determine color
    let baseColor: number;
    let lightColor: number;

    if (isQB) {
      baseColor = COLORS.qb;
      lightColor = COLORS.qbLight;
    } else if (isRB) {
      baseColor = COLORS.rb;
      lightColor = COLORS.rbLight;
    } else if (isFB) {
      baseColor = COLORS.fb;
      lightColor = COLORS.fbLight;
    } else if (isReceiver) {
      baseColor = COLORS.offense;
      lightColor = COLORS.offenseLight;
    } else if (isOL) {
      baseColor = COLORS.ol;
      lightColor = COLORS.olLight;
    } else if (isDL) {
      baseColor = COLORS.dl;
      lightColor = COLORS.dlLight;
    } else {
      baseColor = COLORS.defense;
      lightColor = COLORS.defenseLight;
    }

    // Tackler highlight ring (pulsing effect simulated with thicker ring)
    if (isTackler) {
      bodyG.circle(screen.x, screen.y, radius + 8);
      bodyG.stroke({ color: 0x22c55e, width: 4 });  // Green highlight
      bodyG.circle(screen.x, screen.y, radius + 5);
      bodyG.stroke({ color: 0x22c55e, width: 2, alpha: 0.6 });
    }

    // Selection ring
    if (isSelected) {
      bodyG.circle(screen.x, screen.y, radius + 4);
      bodyG.stroke({ color: COLORS.los, width: 2 });
    }

    // Body circle
    bodyG.circle(screen.x, screen.y, radius);
    bodyG.fill({ color: isSelected ? lightColor : baseColor });
    bodyG.stroke({ color: 0xffffff, width: 1.5 });

    // Ball indicator
    if (player.has_ball) {
      bodyG.circle(screen.x, screen.y, radius - 4);
      bodyG.fill({ color: COLORS.ball });
    }

    playerContainer.addChild(bodyG);

    // Draw facing direction indicator (arrow)
    if (player.facing_x !== undefined && player.facing_y !== undefined) {
      const facingG = new Graphics();
      const arrowLength = radius + 8;
      const arrowHeadSize = 5;

      // Normalize and calculate end point
      const mag = Math.sqrt(player.facing_x * player.facing_x + player.facing_y * player.facing_y);
      if (mag > 0.01) {
        const nx = player.facing_x / mag;
        const ny = player.facing_y / mag;

        // Arrow end point (note: screen Y is inverted)
        const endX = screen.x + nx * arrowLength;
        const endY = screen.y - ny * arrowLength;  // Invert Y for screen coords

        // Draw arrow line
        facingG.moveTo(screen.x, screen.y);
        facingG.lineTo(endX, endY);

        // Arrow head
        const angle = Math.atan2(-ny, nx);  // Invert Y
        const headX1 = endX - arrowHeadSize * Math.cos(angle - Math.PI / 6);
        const headY1 = endY - arrowHeadSize * Math.sin(angle - Math.PI / 6);
        const headX2 = endX - arrowHeadSize * Math.cos(angle + Math.PI / 6);
        const headY2 = endY - arrowHeadSize * Math.sin(angle + Math.PI / 6);

        facingG.moveTo(endX, endY);
        facingG.lineTo(headX1, headY1);
        facingG.moveTo(endX, endY);
        facingG.lineTo(headX2, headY2);

        // Color based on player type
        const arrowColor = isOffense ? 0x60a5fa : 0xf87171;  // Blue for offense, red for defense
        facingG.stroke({ color: arrowColor, width: 2, alpha: 0.7 });
      }

      playerContainer.addChild(facingG);
    }

    // Recognition state indicator (analysis mode)
    if (showAnalysis && isDefender && player.has_recognized_break !== undefined) {
      drawRecognitionState(playerContainer, player, screen);
    }

    // Player name label (with TACKLER indicator if applicable)
    const shortName = player.name.split(' ').pop() || player.name;
    const displayName = isTackler ? `${shortName} ★` : shortName;
    const nameLabel = new Text({
      text: displayName,
      style: new TextStyle({
        fontSize: 10,
        fill: isTackler ? 0x22c55e : COLORS.text,
        fontWeight: isSelected || isTackler ? 'bold' : 'normal',
        fontFamily: 'Berkeley Mono, SF Mono, monospace',
      }),
    });
    nameLabel.anchor.set(0.5);
    nameLabel.x = screen.x;
    nameLabel.y = screen.y - radius - 8;
    playerContainer.addChild(nameLabel);

    // Make clickable
    playerContainer.eventMode = 'static';
    playerContainer.cursor = 'pointer';
    playerContainer.on('pointerdown', () => onSelectPlayer(player.id));

    container.addChild(playerContainer);
  };

  // Helper: Draw recognition state
  const drawRecognitionState = (
    container: Container,
    player: PlayerState,
    screen: { x: number; y: number }
  ) => {
    const iconX = screen.x + 14;
    const iconY = screen.y - 14;

    if (player.has_recognized_break) {
      // Show "!" when recognized
      const label = new Text({
        text: '!',
        style: new TextStyle({
          fontSize: 12,
          fill: COLORS.recognized,
          fontWeight: 'bold',
          fontFamily: 'Berkeley Mono, SF Mono, monospace',
        }),
      });
      label.anchor.set(0.5);
      label.x = iconX;
      label.y = iconY;
      container.addChild(label);
    } else if (player.recognition_timer !== undefined && player.recognition_delay !== undefined) {
      // Show "?" with progress arc
      const label = new Text({
        text: '?',
        style: new TextStyle({
          fontSize: 12,
          fill: COLORS.recognizing,
          fontWeight: 'bold',
          fontFamily: 'Berkeley Mono, SF Mono, monospace',
        }),
      });
      label.anchor.set(0.5);
      label.x = iconX;
      label.y = iconY;
      container.addChild(label);

      // Progress arc
      if (player.recognition_delay > 0) {
        const progress = player.recognition_timer / player.recognition_delay;
        const g = new Graphics();
        g.arc(iconX, iconY, 8, -Math.PI / 2, -Math.PI / 2 + (progress * Math.PI * 2));
        g.stroke({ color: COLORS.recognizing, width: 2, alpha: 0.8 });
        container.addChild(g);
      }
    }
  };

  // Helper: Draw read number
  const drawReadNumber = (
    container: Container,
    receiver: PlayerState,
    currentRead: number | undefined
  ) => {
    if (!receiver.read_order) return;

    const screen = yardToScreen(receiver.x, receiver.y);
    const isCurrent = currentRead === receiver.read_order;

    // Background circle
    const g = new Graphics();
    g.circle(screen.x, screen.y + 20, 8);
    g.fill({ color: isCurrent ? COLORS.readCurrent : 0x1e1e24, alpha: isCurrent ? 1 : 0.8 });
    g.stroke({ color: isCurrent ? COLORS.readCurrent : COLORS.textMuted, width: 1 });
    container.addChild(g);

    // Number
    const label = new Text({
      text: `${receiver.read_order}`,
      style: new TextStyle({
        fontSize: 10,
        fill: isCurrent ? 0x000000 : COLORS.text,
        fontWeight: 'bold',
        fontFamily: 'Berkeley Mono, SF Mono, monospace',
      }),
    });
    label.anchor.set(0.5);
    label.x = screen.x;
    label.y = screen.y + 20;
    container.addChild(label);
  };

  // Helper: Draw ball
  const drawBall = (container: Container, ball: BallState) => {
    const ballG = new Graphics();
    const screen = yardToScreen(ball.x, ball.y);
    const height = ball.height ?? 2.0;

    if (ball.state === 'in_flight') {
      // Draw arc trail
      if (ball.flight_origin_x != null && ball.flight_target_x != null) {
        const origin = yardToScreen(ball.flight_origin_x, ball.flight_origin_y!);
        const target = yardToScreen(ball.flight_target_x, ball.flight_target_y!);
        const peakHeight = ball.peak_height ?? 3.0;
        const heightScale = 6;
        const progress = ball.flight_progress ?? 0;

        // Full projected arc (faded)
        ballG.moveTo(origin.x, origin.y);
        for (let i = 1; i <= 20; i++) {
          const t = i / 20;
          const x = origin.x + (target.x - origin.x) * t;
          const baseY = origin.y + (target.y - origin.y) * t;
          const arcOffset = 4 * peakHeight * heightScale * t * (1 - t);
          ballG.lineTo(x, baseY - arcOffset);
        }
        ballG.stroke({ color: COLORS.ballTarget, width: 2, alpha: 0.2 });

        // Traveled portion (solid)
        if (progress > 0) {
          ballG.moveTo(origin.x, origin.y);
          for (let i = 1; i <= Math.ceil(20 * progress); i++) {
            const t = Math.min(i / 20, progress);
            const x = origin.x + (target.x - origin.x) * t;
            const baseY = origin.y + (target.y - origin.y) * t;
            const arcOffset = 4 * peakHeight * heightScale * t * (1 - t);
            ballG.lineTo(x, baseY - arcOffset);
          }
          ballG.stroke({ color: COLORS.ballInFlight, width: 2, alpha: 0.7 });
        }

        // Target marker
        ballG.circle(target.x, target.y, 8);
        ballG.stroke({ color: COLORS.ballTarget, width: 2 });
      }

      // Ball at elevated position
      const heightOffset = height * 6;
      const ballY = screen.y - heightOffset;

      // Shadow
      ballG.ellipse(screen.x, screen.y, 6, 3);
      ballG.fill({ color: 0x000000, alpha: 0.3 });

      // Ball
      ballG.circle(screen.x, ballY, 6);
      ballG.fill({ color: COLORS.ballInFlight });
      ballG.stroke({ color: 0xffffff, width: 1.5 });
    } else {
      // Held ball
      ballG.circle(screen.x, screen.y, 4);
      ballG.fill({ color: COLORS.ball });
      ballG.stroke({ color: 0xffffff, width: 1 });
    }

    container.addChild(ballG);
  };

  // =========================================================================
  // Run Game Visualization Helpers
  // =========================================================================

  // Helper: Draw gap indicators between OL players
  const drawGapIndicators = (container: Container, olPlayers: PlayerState[], designedGap?: GapType) => {
    // Sort OL by x position (left to right)
    const sortedOL = [...olPlayers].sort((a, b) => a.x - b.x);
    if (sortedOL.length < 2) return;

    const g = new Graphics();
    const gapLabels = ['c', 'b', 'a', 'a', 'b', 'c', 'd'];  // Gaps from left to right (lowercase to match backend)
    const gapSides = ['left', 'left', 'left', 'right', 'right', 'right', 'right'];

    for (let i = 0; i < sortedOL.length - 1; i++) {
      const left = sortedOL[i];
      const right = sortedOL[i + 1];
      const midX = (left.x + right.x) / 2;
      const midY = (left.y + right.y) / 2;
      const screen = yardToScreen(midX, midY);

      // Calculate gap width (separation between linemen)
      const gapWidth = Math.abs(right.x - left.x);
      const isOpen = gapWidth > 1.5;  // Gap is "open" if > 1.5 yards

      // Check if this is the designed gap
      const gapName = `${gapLabels[i]}_${gapSides[i]}` as GapType;
      const isDesigned = designedGap === gapName;

      // Draw gap indicator (vertical line or opening)
      const color = isDesigned ? COLORS.gapDesigned : (isOpen ? COLORS.gap : COLORS.gapClosed);
      const lineHeight = runZoom ? 30 : 15;

      g.moveTo(screen.x, screen.y - lineHeight / 2);
      g.lineTo(screen.x, screen.y + lineHeight / 2);
      g.stroke({ color, width: isDesigned ? 4 : 2, alpha: isOpen ? 0.9 : 0.5 });

      // Gap label (display uppercase for readability)
      const label = new Text({
        text: gapLabels[i].toUpperCase(),
        style: new TextStyle({
          fontSize: runZoom ? 14 : 10,
          fill: color,
          fontWeight: isDesigned ? 'bold' : 'normal',
          fontFamily: 'Berkeley Mono, SF Mono, monospace',
        }),
      });
      label.anchor.set(0.5);
      label.x = screen.x;
      label.y = screen.y + lineHeight / 2 + 10;
      container.addChild(label);
    }

    container.addChild(g);
  };

  // Helper: Draw blocking engagement visualization
  const drawBlockingEngagements = (container: Container, players: PlayerState[]) => {
    const olPlayers = players.filter(p => p.player_type === 'ol');
    const dlPlayers = players.filter(p => p.player_type === 'dl');

    olPlayers.forEach(ol => {
      if (!ol.is_engaged || !ol.engaged_with_id) return;

      const dl = dlPlayers.find(d => d.id === ol.engaged_with_id);
      if (!dl) return;

      const olScreen = yardToScreen(ol.x, ol.y);
      const dlScreen = yardToScreen(dl.x, dl.y);
      const g = new Graphics();

      // Draw engagement line
      g.moveTo(olScreen.x, olScreen.y);
      g.lineTo(dlScreen.x, dlScreen.y);
      g.stroke({ color: COLORS.blockEngaged, width: 3, alpha: 0.7 });

      // Draw shed progress bar on the engagement line
      if (ol.block_shed_progress !== undefined) {
        const progress = ol.block_shed_progress;
        const midX = (olScreen.x + dlScreen.x) / 2;
        const midY = (olScreen.y + dlScreen.y) / 2;
        const barWidth = runZoom ? 30 : 20;
        const barHeight = runZoom ? 8 : 5;

        // Background
        g.rect(midX - barWidth / 2, midY - barHeight / 2, barWidth, barHeight);
        g.fill({ color: 0x000000, alpha: 0.6 });

        // Progress fill (green = OL winning, red = DL winning/shedding)
        const fillColor = progress < 0.5 ? COLORS.blockWinning : COLORS.blockLosing;
        const fillWidth = barWidth * progress;
        g.rect(midX - barWidth / 2, midY - barHeight / 2, fillWidth, barHeight);
        g.fill({ color: fillColor, alpha: 0.9 });

        // Border
        g.rect(midX - barWidth / 2, midY - barHeight / 2, barWidth, barHeight);
        g.stroke({ color: 0xffffff, width: 1 });
      }

      container.addChild(g);
    });
  };

  // Helper: Draw tackle engagement visualization
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
      g.stroke({ color: 0xf97316, width: 4, alpha: 0.8 });  // Orange

      // Draw struggle indicator at midpoint
      const midX = (bcScreen.x + tacklerScreen.x) / 2;
      const midY = (bcScreen.y + tacklerScreen.y) / 2;

      // Leverage bar (centered, shows who's winning)
      const barWidth = runZoom ? 50 : 35;
      const barHeight = runZoom ? 10 : 7;
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
        g.fill({ color: 0x22c55e, alpha: 0.9 });  // Green
      } else if (leverage < 0) {
        // Tackler winning - red fill from center to left
        g.rect(midX - fillWidth, midY - barHeight / 2, fillWidth, barHeight);
        g.fill({ color: 0xef4444, alpha: 0.9 });  // Red
      }

      // Border
      g.rect(midX - barWidth / 2, midY - barHeight / 2, barWidth, barHeight);
      g.stroke({ color: 0xffffff, width: 1 });

      // TACKLE label
      const tackleLabel = new Text({
        text: 'TACKLE',
        style: new TextStyle({
          fontSize: runZoom ? 10 : 8,
          fill: 0xf97316,
          fontWeight: 'bold',
          fontFamily: 'Berkeley Mono, SF Mono, monospace',
        }),
      });
      tackleLabel.anchor.set(0.5);
      tackleLabel.x = midX;
      tackleLabel.y = midY - barHeight / 2 - 8;
      container.addChild(tackleLabel);

      // Highlight the primary tackler with an orange ring
      g.circle(tacklerScreen.x, tacklerScreen.y, runZoom ? 18 : 14);
      g.stroke({ color: 0xf97316, width: 3, alpha: 0.8 });
    }

    // Draw struggle effect around ballcarrier (concentric rings that pulse based on leverage)
    const ringRadius = runZoom ? 24 : 18;
    const leverage = ballcarrier.tackle_leverage ?? 0;

    // Inner ring - color based on who's winning
    const ringColor = leverage > 0 ? 0x22c55e : leverage < 0 ? 0xef4444 : 0xf97316;
    g.circle(bcScreen.x, bcScreen.y, ringRadius);
    g.stroke({ color: ringColor, width: 3, alpha: 0.7 });

    // Outer ring (faded)
    g.circle(bcScreen.x, bcScreen.y, ringRadius + 6);
    g.stroke({ color: ringColor, width: 2, alpha: 0.3 });

    container.addChild(g);
  };

  // Helper: Draw OL blocking assignments
  const drawBlockingAssignments = (container: Container, olPlayers: PlayerState[]) => {
    olPlayers.forEach(ol => {
      if (!ol.blocking_assignment) return;

      const screen = yardToScreen(ol.x, ol.y);
      const radius = runZoom ? 14 : 10;

      // Assignment label above player
      const assignmentText = ol.blocking_assignment.replace('_', ' ').toUpperCase();
      const shortText = assignmentText.substring(0, 4);

      const label = new Text({
        text: shortText,
        style: new TextStyle({
          fontSize: runZoom ? 10 : 8,
          fill: COLORS.text,
          fontWeight: 'bold',
          fontFamily: 'Berkeley Mono, SF Mono, monospace',
        }),
      });
      label.anchor.set(0.5);
      label.x = screen.x;
      label.y = screen.y + radius + 12;
      container.addChild(label);

      // Draw pull path if pulling
      if (ol.is_pulling && ol.pull_target_x !== undefined && ol.pull_target_y !== undefined) {
        const g = new Graphics();
        const target = yardToScreen(ol.pull_target_x, ol.pull_target_y);

        // Dashed pull path
        const dx = target.x - screen.x;
        const dy = target.y - screen.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const nx = dx / dist;
        const ny = dy / dist;
        let pos = 0;

        while (pos < dist) {
          const startX = screen.x + nx * pos;
          const startY = screen.y + ny * pos;
          const endPos = Math.min(pos + 8, dist);
          const endX = screen.x + nx * endPos;
          const endY = screen.y + ny * endPos;

          g.moveTo(startX, startY);
          g.lineTo(endX, endY);
          pos += 14;
        }
        g.stroke({ color: COLORS.pullPath, width: 3, alpha: 0.7 });

        // Pull target marker
        g.circle(target.x, target.y, 6);
        g.stroke({ color: COLORS.pullPath, width: 2 });

        container.addChild(g);
      }
    });
  };

  // Helper: Draw RB vision and decision-making
  const drawRBVision = (container: Container, rb: PlayerState) => {
    const screen = yardToScreen(rb.x, rb.y);
    const g = new Graphics();

    // Draw vision line to target
    if (rb.vision_target_x !== undefined && rb.vision_target_y !== undefined) {
      const target = yardToScreen(rb.vision_target_x, rb.vision_target_y);

      g.moveTo(screen.x, screen.y);
      g.lineTo(target.x, target.y);
      g.stroke({ color: COLORS.rbVision, width: 2, alpha: 0.7 });

      // Vision target marker
      g.circle(target.x, target.y, 5);
      g.fill({ color: COLORS.rbVision, alpha: 0.5 });
    }

    // Draw read point
    if (rb.read_point_x !== undefined && rb.read_point_y !== undefined) {
      const readPoint = yardToScreen(rb.read_point_x, rb.read_point_y);

      // Read point circle
      g.circle(readPoint.x, readPoint.y, runZoom ? 10 : 6);
      g.stroke({ color: COLORS.rbReadPoint, width: 2, alpha: 0.8 });

      // Label
      const label = new Text({
        text: 'READ',
        style: new TextStyle({
          fontSize: runZoom ? 10 : 8,
          fill: COLORS.rbReadPoint,
          fontWeight: 'bold',
          fontFamily: 'Berkeley Mono, SF Mono, monospace',
        }),
      });
      label.anchor.set(0.5);
      label.x = readPoint.x;
      label.y = readPoint.y - (runZoom ? 16 : 12);
      container.addChild(label);
    }

    // Draw target gap indicator
    if (rb.target_gap) {
      const label = new Text({
        text: `→ ${rb.target_gap.replace('_', ' ')}`,
        style: new TextStyle({
          fontSize: runZoom ? 12 : 9,
          fill: COLORS.gapDesigned,
          fontWeight: 'bold',
          fontFamily: 'Berkeley Mono, SF Mono, monospace',
        }),
      });
      label.anchor.set(0.5);
      label.x = screen.x;
      label.y = screen.y - (runZoom ? 28 : 20);
      container.addChild(label);
    }

    container.addChild(g);
  };

  return <div ref={canvasRef} className="sim-canvas" />;
}
