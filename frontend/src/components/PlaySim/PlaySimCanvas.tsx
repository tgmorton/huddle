/**
 * PixiJS Canvas for play simulation visualization
 * Shows QB, receivers, defenders, ball, and routes
 */

import { useEffect, useRef, useCallback } from 'react';
import { Application, Graphics, Text, TextStyle, Container } from 'pixi.js';

// Canvas dimensions - wider to fit all players, shorter for focused view
const CANVAS_WIDTH = 1000;
const CANVAS_HEIGHT = 500;

// Field conversion: 1 yard = 18 pixels (balanced zoom to fit width)
const PIXELS_PER_YARD = 18;

// Field origin - center of canvas horizontally, LOS near bottom
// Shows ~25 yards wide each side, ~20 yards deep
const CENTER_X = CANVAS_WIDTH / 2;
const LOS_Y = CANVAS_HEIGHT - 100;

// Colors
const COLORS = {
  field: 0x2d5016,
  los: 0xffffff,
  yardLine: 0xffffff,
  qb: 0x3b82f6,       // Blue for QB
  wr: 0x22c55e,       // Green for receivers
  db: 0xf97316,       // Orange for defenders
  ball: 0xffffff,     // White ball
  ballTrail: 0xfbbf24, // Yellow trail
  routePath: 0x3b82f6,
  target: 0xef4444,   // Red target indicator
  readIndicator: 0xfbbf24, // Yellow for current read
};

// Receiver colors by position
const WR_COLORS: Record<string, number> = {
  x: 0x22c55e,
  z: 0x10b981,
  slot_l: 0x14b8a6,
  slot_r: 0x06b6d4,
  te: 0x0ea5e9,
};

// DB colors by position
const DB_COLORS: Record<string, number> = {
  cb1: 0xf97316,
  cb2: 0xfb923c,
  nickel: 0xf59e0b,
  ss: 0xef4444,
  fs: 0xec4899,
};

interface Vec2 {
  x: number;
  y: number;
}

interface RouteWaypoint {
  position: Vec2;
  arrival_tick: number;
  is_break: boolean;
}

interface TeamReceiver {
  id: string;
  position: Vec2;
  alignment: string;
  route: RouteWaypoint[];
  route_type: string;
  animation: string;
  facing: Vec2;
}

interface TeamDefender {
  id: string;
  position: Vec2;
  alignment: string;
  zone_assignment: string | null;
  is_in_man: boolean;
  animation: string;
  facing: Vec2;
}

interface TeamQB {
  id: string;
  position: Vec2;
  attributes: {
    arm_strength: number;
    accuracy: number;
    decision_making: number;
    pocket_awareness: number;
  };
  read_order: string[];
  current_read_idx: number;
  ticks_on_read: number;
  target_receiver_id: string | null;
  throw_tick: number | null;
  has_thrown: boolean;
  animation: string;
  facing: Vec2;
}

interface Ball {
  position: Vec2;
  start_position: Vec2;
  target_position: Vec2;
  velocity: number;
  is_thrown: boolean;
  is_caught: boolean;
  is_incomplete: boolean;
  throw_tick: number;
  arrival_tick: number;
  target_receiver_id: string | null;
  intercepted_by_id: string | null;
}

interface MatchupResult {
  receiver_id: string;
  defender_id: string;
  separation: number;
  max_separation: number;
  result: string;
}

interface PlaySimState {
  receivers: TeamReceiver[];
  defenders: TeamDefender[];
  qb: TeamQB;
  ball: Ball;
  formation: string;
  coverage: string;
  concept: string;
  matchups: Record<string, MatchupResult>;
  tick: number;
  is_complete: boolean;
  play_result: string;
}

interface PlaySimCanvasProps {
  state: PlaySimState;
}

interface PlayerSprites {
  receivers: Map<string, Container>;
  defenders: Map<string, Container>;
  routePaths: Map<string, Graphics>;
  zones: Graphics | null;
  qb: Container | null;
  ball: Container | null;
  ballTrail: Graphics | null;
  targetIndicator: Graphics | null;
  readHighlight: Graphics | null;
}

export function PlaySimCanvas({ state }: PlaySimCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const spritesRef = useRef<PlayerSprites>({
    receivers: new Map(),
    defenders: new Map(),
    routePaths: new Map(),
    zones: null,
    qb: null,
    ball: null,
    ballTrail: null,
    targetIndicator: null,
    readHighlight: null,
  });
  const initializedRef = useRef(false);

  // Convert game coordinates to screen coordinates
  const gameToScreen = useCallback((pos: Vec2): { x: number; y: number } => {
    return {
      x: CENTER_X + pos.x * PIXELS_PER_YARD,
      y: LOS_Y - pos.y * PIXELS_PER_YARD,
    };
  }, []);

  // Initialize PixiJS
  useEffect(() => {
    if (!canvasRef.current || initializedRef.current) return;

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
      initializedRef.current = true;

      drawField(app);
    };

    init();

    return () => {
      mounted = false;
    };
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (appRef.current) {
        appRef.current.destroy(true);
        appRef.current = null;
      }
      initializedRef.current = false;
    };
  }, []);

  // Update when state changes
  useEffect(() => {
    if (!appRef.current || !initializedRef.current) return;
    updatePlayers();
  }, [state]);

  const drawField = (app: Application) => {
    const fieldGraphics = new Graphics();

    // Draw yard lines (shows -5 to 22 yards based on canvas size)
    for (let yard = -5; yard <= 22; yard++) {
      const y = LOS_Y - yard * PIXELS_PER_YARD;
      if (y < 0 || y > CANVAS_HEIGHT) continue;

      const alpha = yard === 0 ? 1 : 0.2;
      const height = yard === 0 ? 3 : 1;

      fieldGraphics.rect(0, y - height / 2, CANVAS_WIDTH, height);
      fieldGraphics.fill({ color: COLORS.yardLine, alpha });

      // Yard markers
      if (yard > 0 && yard % 5 === 0) {
        const yardText = new Text({
          text: `${yard}`,
          style: new TextStyle({
            fontFamily: 'Arial',
            fontSize: 10,
            fill: COLORS.yardLine,
          }),
        });
        yardText.x = 12;
        yardText.y = y - 5;
        yardText.alpha = 0.4;
        app.stage.addChild(yardText);
      }
    }

    // LOS label
    const losText = new Text({
      text: 'LOS',
      style: new TextStyle({
        fontFamily: 'Arial',
        fontSize: 11,
        fill: COLORS.yardLine,
      }),
    });
    losText.x = CANVAS_WIDTH - 32;
    losText.y = LOS_Y + 4;
    app.stage.addChild(losText);

    // Hash marks
    for (let yard = 0; yard <= 23; yard++) {
      const y = LOS_Y - yard * PIXELS_PER_YARD;
      if (y < 0 || y > CANVAS_HEIGHT) continue;
      fieldGraphics.rect(CENTER_X - 100, y - 1, 6, 2);
      fieldGraphics.fill({ color: COLORS.yardLine, alpha: 0.25 });
      fieldGraphics.rect(CENTER_X + 94, y - 1, 6, 2);
      fieldGraphics.fill({ color: COLORS.yardLine, alpha: 0.25 });
    }

    // Sideline indicators
    fieldGraphics.rect(50, 0, 2, CANVAS_HEIGHT);
    fieldGraphics.fill({ color: COLORS.yardLine, alpha: 0.15 });
    fieldGraphics.rect(CANVAS_WIDTH - 52, 0, 2, CANVAS_HEIGHT);
    fieldGraphics.fill({ color: COLORS.yardLine, alpha: 0.15 });

    app.stage.addChild(fieldGraphics);

    // Zone visualization container
    const zones = new Graphics();
    app.stage.addChild(zones);
    spritesRef.current.zones = zones;

    // Ball trail graphics
    const ballTrail = new Graphics();
    app.stage.addChild(ballTrail);
    spritesRef.current.ballTrail = ballTrail;

    // Target indicator
    const targetIndicator = new Graphics();
    app.stage.addChild(targetIndicator);
    spritesRef.current.targetIndicator = targetIndicator;

    // Read highlight
    const readHighlight = new Graphics();
    app.stage.addChild(readHighlight);
    spritesRef.current.readHighlight = readHighlight;
  };

  const createPlayerSprite = (
    label: string,
    color: number,
    isDefender: boolean,
    isQB: boolean = false
  ): Container => {
    const container = new Container();

    const body = new Graphics();
    if (isQB) {
      // Larger circle for QB
      body.circle(0, 0, 12);
      body.fill({ color });
      body.stroke({ color: 0xffffff, width: 3 });
    } else if (isDefender) {
      // Square for defenders
      body.rect(-8, -8, 16, 16);
      body.fill({ color });
      body.stroke({ color: 0xffffff, width: 2 });
    } else {
      // Circle for receivers
      body.circle(0, 0, 8);
      body.fill({ color });
      body.stroke({ color: 0xffffff, width: 2 });
    }
    body.name = 'body';
    container.addChild(body);

    // Direction indicator
    const direction = new Graphics();
    direction.moveTo(0, -6);
    direction.lineTo(0, -12);
    direction.stroke({ color: 0xffffff, width: 2 });
    direction.name = 'direction';
    container.addChild(direction);

    // Label
    const text = new Text({
      text: label,
      style: new TextStyle({
        fontFamily: 'Arial',
        fontSize: isQB ? 10 : 8,
        fill: 0xffffff,
        fontWeight: 'bold',
      }),
    });
    text.anchor.set(0.5);
    text.name = 'label';
    container.addChild(text);

    return container;
  };

  const createBallSprite = (): Container => {
    const container = new Container();

    const ball = new Graphics();
    ball.circle(0, 0, 5);
    ball.fill({ color: COLORS.ball });
    ball.stroke({ color: 0x8b4513, width: 2 }); // Brown lacing
    ball.name = 'ball';
    container.addChild(ball);

    return container;
  };

  const updatePlayers = () => {
    const app = appRef.current;
    if (!app) return;

    const sprites = spritesRef.current;

    // Draw zone areas first
    updateZones();

    // Update ball trail and target
    updateBallVisuals();

    // Update read highlight
    updateReadHighlight();

    // Update or create QB sprite
    if (state.qb) {
      if (!sprites.qb) {
        sprites.qb = createPlayerSprite('QB', COLORS.qb, false, true);
        app.stage.addChild(sprites.qb);
      }

      const screen = gameToScreen(state.qb.position);
      sprites.qb.x = screen.x;
      sprites.qb.y = screen.y;

      // Update direction
      const direction = sprites.qb.getChildByName('direction') as Graphics;
      if (direction && state.qb.facing) {
        const angle = Math.atan2(-state.qb.facing.y, state.qb.facing.x) - Math.PI / 2;
        direction.rotation = angle;
      }
    }

    // Update or create ball sprite
    if (state.ball) {
      if (!sprites.ball) {
        sprites.ball = createBallSprite();
        app.stage.addChild(sprites.ball);
      }

      const screen = gameToScreen(state.ball.position);
      sprites.ball.x = screen.x;
      sprites.ball.y = screen.y;

      // Hide ball if not thrown and in QB's hands
      sprites.ball.visible = state.ball.is_thrown || state.ball.is_caught || state.ball.is_incomplete;

      // Pulse effect when caught or intercepted
      if (state.ball.is_caught || state.ball.intercepted_by_id) {
        sprites.ball.scale.set(1.5);
      } else {
        sprites.ball.scale.set(1.0);
      }
    }

    // Update or create receiver sprites
    for (const rcvr of state.receivers) {
      let sprite = sprites.receivers.get(rcvr.id);

      if (!sprite) {
        const color = WR_COLORS[rcvr.alignment] || COLORS.wr;
        sprite = createPlayerSprite(rcvr.alignment.toUpperCase(), color, false);
        app.stage.addChild(sprite);
        sprites.receivers.set(rcvr.id, sprite);

        // Create route path
        const routePath = new Graphics();
        app.stage.addChildAt(routePath, 1);
        sprites.routePaths.set(rcvr.id, routePath);
      }

      // Update position
      const screen = gameToScreen(rcvr.position);
      sprite.x = screen.x;
      sprite.y = screen.y;

      // Update direction
      const direction = sprite.getChildByName('direction') as Graphics;
      if (direction && rcvr.facing) {
        const angle = Math.atan2(-rcvr.facing.y, rcvr.facing.x) - Math.PI / 2;
        direction.rotation = angle;
      }

      // Highlight target receiver
      const body = sprite.getChildByName('body') as Graphics;
      if (body && state.qb.target_receiver_id === rcvr.id) {
        sprite.scale.set(1.3);
      } else if (body) {
        sprite.scale.set(1.0);
      }

      // Update route path
      updateRoutePath(rcvr);
    }

    // Update or create defender sprites
    for (const defender of state.defenders) {
      let sprite = sprites.defenders.get(defender.id);

      if (!sprite) {
        const color = DB_COLORS[defender.alignment] || COLORS.db;
        sprite = createPlayerSprite(defender.alignment.toUpperCase(), color, true);
        app.stage.addChild(sprite);
        sprites.defenders.set(defender.id, sprite);
      }

      // Update position
      const screen = gameToScreen(defender.position);
      sprite.x = screen.x;
      sprite.y = screen.y;

      // Update direction
      const direction = sprite.getChildByName('direction') as Graphics;
      if (direction && defender.facing) {
        const angle = Math.atan2(-defender.facing.y, defender.facing.x) - Math.PI / 2;
        direction.rotation = angle;
      }

      // Highlight intercepting defender
      if (state.ball.intercepted_by_id === defender.id) {
        sprite.scale.set(1.4);
      } else {
        sprite.scale.set(1.0);
      }
    }

    // Remove old sprites
    for (const [id, sprite] of sprites.receivers) {
      if (!state.receivers.find((r) => r.id === id)) {
        app.stage.removeChild(sprite);
        sprites.receivers.delete(id);
        const routePath = sprites.routePaths.get(id);
        if (routePath) {
          app.stage.removeChild(routePath);
          sprites.routePaths.delete(id);
        }
      }
    }

    for (const [id, sprite] of sprites.defenders) {
      if (!state.defenders.find((d) => d.id === id)) {
        app.stage.removeChild(sprite);
        sprites.defenders.delete(id);
      }
    }
  };

  const updateBallVisuals = () => {
    const ballTrail = spritesRef.current.ballTrail;
    const targetIndicator = spritesRef.current.targetIndicator;
    if (!ballTrail || !targetIndicator) return;

    ballTrail.clear();
    targetIndicator.clear();

    if (!state.ball.is_thrown || state.ball.is_caught || state.ball.is_incomplete) return;

    // Draw ball trajectory line
    const startScreen = gameToScreen(state.ball.start_position);
    const targetScreen = gameToScreen(state.ball.target_position);

    // Dashed line from start to target
    ballTrail.moveTo(startScreen.x, startScreen.y);
    ballTrail.lineTo(targetScreen.x, targetScreen.y);
    ballTrail.stroke({
      color: COLORS.ballTrail,
      width: 2,
      alpha: 0.5,
    });

    // Target indicator (X marks the spot)
    targetIndicator.moveTo(targetScreen.x - 8, targetScreen.y - 8);
    targetIndicator.lineTo(targetScreen.x + 8, targetScreen.y + 8);
    targetIndicator.moveTo(targetScreen.x + 8, targetScreen.y - 8);
    targetIndicator.lineTo(targetScreen.x - 8, targetScreen.y + 8);
    targetIndicator.stroke({
      color: COLORS.target,
      width: 3,
      alpha: 0.8,
    });

    // Circle around target
    targetIndicator.circle(targetScreen.x, targetScreen.y, 12);
    targetIndicator.stroke({
      color: COLORS.target,
      width: 2,
      alpha: 0.5,
    });
  };

  const updateReadHighlight = () => {
    const readHighlight = spritesRef.current.readHighlight;
    if (!readHighlight) return;

    readHighlight.clear();

    // Don't show if QB has thrown
    if (state.qb.has_thrown) return;

    // Find current read receiver
    const currentReadId = state.qb.read_order[state.qb.current_read_idx];
    const currentReadReceiver = state.receivers.find((r) => r.id === currentReadId);
    if (!currentReadReceiver) return;

    const screen = gameToScreen(currentReadReceiver.position);

    // Draw pulsing ring around current read
    readHighlight.circle(screen.x, screen.y, 18);
    readHighlight.stroke({
      color: COLORS.readIndicator,
      width: 3,
      alpha: 0.7,
    });

    // Draw line from QB to current read
    const qbScreen = gameToScreen(state.qb.position);
    readHighlight.moveTo(qbScreen.x, qbScreen.y);
    readHighlight.lineTo(screen.x, screen.y);
    readHighlight.stroke({
      color: COLORS.readIndicator,
      width: 1,
      alpha: 0.3,
    });
  };

  const updateZones = () => {
    const zones = spritesRef.current.zones;
    if (!zones) return;

    zones.clear();

    // Only draw zones for zone coverages
    if (
      !state.coverage.includes('cover_2') &&
      !state.coverage.includes('cover_3') &&
      !state.coverage.includes('cover_4')
    ) {
      return;
    }

    // Draw zone areas for defenders with zone assignments
    for (const defender of state.defenders) {
      if (defender.zone_assignment) {
        const zoneCenter = getZoneCenter(defender.zone_assignment);
        if (zoneCenter) {
          const screen = gameToScreen(zoneCenter);
          const radius = getZoneRadius(defender.zone_assignment) * PIXELS_PER_YARD;

          const color = DB_COLORS[defender.alignment] || 0x6366f1;
          zones.circle(screen.x, screen.y, radius);
          zones.fill({ color, alpha: 0.1 });
          zones.stroke({ color, width: 1, alpha: 0.3 });
        }
      }
    }
  };

  const getZoneCenter = (zone: string): Vec2 | null => {
    // Zone anchors - matches backend ZONE_BOUNDARIES
    const centers: Record<string, Vec2> = {
      deep_third_l: { x: -16, y: 12 },
      deep_third_m: { x: 0, y: 14 },
      deep_third_r: { x: 16, y: 12 },
      deep_half_l: { x: -12, y: 12 },
      deep_half_r: { x: 12, y: 12 },
      deep_quarter_1: { x: -16, y: 10 },
      deep_quarter_2: { x: -6, y: 12 },
      deep_quarter_3: { x: 6, y: 12 },
      deep_quarter_4: { x: 16, y: 10 },
      flat_l: { x: -14, y: 4 },
      flat_r: { x: 14, y: 4 },
      hook_l: { x: -6, y: 8 },
      hook_r: { x: 6, y: 8 },
      curl_flat_l: { x: -12, y: 6 },
      curl_flat_r: { x: 12, y: 6 },
      middle: { x: 0, y: 10 },
    };
    return centers[zone] || null;
  };

  const getZoneRadius = (zone: string): number => {
    if (zone.includes('deep')) return 10;
    return 7;
  };

  const updateRoutePath = (rcvr: TeamReceiver) => {
    const routePath = spritesRef.current.routePaths.get(rcvr.id);
    if (!routePath) return;

    routePath.clear();

    const route = rcvr.route;
    if (route.length === 0) return;

    // Get starting position - use first waypoint's X since routes are absolute
    // Start at y=0 (LOS) where receiver lined up
    const startX = route[0]?.position.x ?? 0;
    const start = gameToScreen({ x: startX, y: 0 });

    // Draw full route path (faded)
    routePath.moveTo(start.x, start.y);
    route.forEach((waypoint) => {
      const screen = gameToScreen(waypoint.position);
      routePath.lineTo(screen.x, screen.y);
    });

    const color = WR_COLORS[rcvr.alignment] || COLORS.routePath;
    routePath.stroke({
      color,
      width: 2,
      alpha: 0.3,
    });

    // Draw break point markers
    route.forEach((waypoint) => {
      if (waypoint.is_break) {
        const screen = gameToScreen(waypoint.position);
        routePath.circle(screen.x, screen.y, 4);
        routePath.fill({ color: 0xfbbf24, alpha: 0.6 });
      }
    });
  };

  return (
    <div className="play-sim-canvas">
      <div ref={canvasRef} className="canvas-container" />
    </div>
  );
}
