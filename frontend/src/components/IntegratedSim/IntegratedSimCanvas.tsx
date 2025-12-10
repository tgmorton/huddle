/**
 * PixiJS Canvas for integrated simulation visualization
 * Shows pocket (OL, DL, QB) + play (receivers, defenders, ball, routes)
 */

import { useEffect, useRef, useCallback } from 'react';
import { Application, Graphics, Text, TextStyle, Container } from 'pixi.js';

// Canvas dimensions - wide to show both pocket and routes
const CANVAS_WIDTH = 1100;
const CANVAS_HEIGHT = 550;

// Field conversion: 1 yard = 16 pixels
const PIXELS_PER_YARD = 16;

// Field origin - center of canvas horizontally, LOS near bottom
const CENTER_X = CANVAS_WIDTH / 2;
const LOS_Y = CANVAS_HEIGHT - 120;

// Colors
const COLORS = {
  field: 0x2d5016,
  los: 0xffffff,
  yardLine: 0xffffff,
  qb: 0x3b82f6,       // Blue for QB
  wr: 0x22c55e,       // Green for receivers
  db: 0xf97316,       // Orange for defenders
  ol: 0x60a5fa,       // Light blue for O-line
  dl: 0xfb7185,       // Pink for D-line
  ball: 0xffffff,     // White ball
  ballTrail: 0xfbbf24, // Yellow trail
  routePath: 0x3b82f6,
  target: 0xef4444,   // Red target indicator
  readIndicator: 0xfbbf24, // Yellow for current read
  pressureZone: 0xef4444,  // Red for pressure area
  engagement: 0xfbbf24,    // Yellow for engagement lines
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

// OL colors by role
const OL_COLORS: Record<string, number> = {
  lt: 0x3b82f6,
  lg: 0x60a5fa,
  c: 0x93c5fd,
  rg: 0x60a5fa,
  rt: 0x3b82f6,
};

// DL colors by role
const DL_COLORS: Record<string, number> = {
  le: 0xef4444,
  ldt: 0xfb7185,
  nt: 0xfda4af,
  rdt: 0xfb7185,
  re: 0xef4444,
  blitz: 0xdc2626,
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
  target_receiver_id: string | null;
  has_thrown: boolean;
  animation: string;
  facing: Vec2;
}

interface Ball {
  position: Vec2;
  start_position: Vec2;
  target_position: Vec2;
  is_thrown: boolean;
  is_caught: boolean;
  is_incomplete: boolean;
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

interface PlayState {
  receivers: TeamReceiver[];
  defenders: TeamDefender[];
  qb: TeamQB;
  ball: Ball;
  matchups: Record<string, MatchupResult>;
  tick: number;
  is_complete: boolean;
  play_result: string;
}

interface Player {
  id: string;
  role: string;
  position: Vec2;
  is_free: boolean;
  is_down: boolean;
  animation: string;
  facing: Vec2;
}

interface Engagement {
  blocker_roles: string[];
  rusher_role: string;
  contact_point: Vec2;
  state: string;
}

interface PocketState {
  qb: Player;
  blockers: Player[];
  rushers: Player[];
  engagements: Engagement[];
  tick: number;
  is_complete: boolean;
  result: string;
}

interface PressureState {
  total: number;
  level: string;
  panic: boolean;
  qb_position: Vec2;
}

interface IntegratedSimCanvasProps {
  playState: PlayState;
  pocketState: PocketState;
  pressureState: PressureState | null;
}

interface PlayerSprites {
  // Play sim sprites
  receivers: Map<string, Container>;
  defenders: Map<string, Container>;
  routePaths: Map<string, Graphics>;
  zones: Graphics | null;
  ball: Container | null;
  ballTrail: Graphics | null;
  targetIndicator: Graphics | null;
  readHighlight: Graphics | null;
  // Pocket sim sprites
  qb: Container | null;
  blockers: Map<string, Container>;
  rushers: Map<string, Container>;
  engagementLines: Graphics | null;
  pressureOverlay: Graphics | null;
}

export function IntegratedSimCanvas({ playState, pocketState, pressureState }: IntegratedSimCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const spritesRef = useRef<PlayerSprites>({
    receivers: new Map(),
    defenders: new Map(),
    routePaths: new Map(),
    zones: null,
    ball: null,
    ballTrail: null,
    targetIndicator: null,
    readHighlight: null,
    qb: null,
    blockers: new Map(),
    rushers: new Map(),
    engagementLines: null,
    pressureOverlay: null,
  });
  const initializedRef = useRef(false);
  const lastTickRef = useRef<number>(0);
  const lastQbIdRef = useRef<string | null>(null);
  const lastBlockerIdsRef = useRef<Set<string>>(new Set());
  const lastRusherIdsRef = useRef<Set<string>>(new Set());

  // Clear all player sprites (called on reset)
  const clearAllSprites = useCallback(() => {
    const app = appRef.current;
    const sprites = spritesRef.current;
    if (!app) return;

    // Remove receivers
    for (const [, sprite] of sprites.receivers) {
      app.stage.removeChild(sprite);
      sprite.destroy();
    }
    sprites.receivers.clear();

    // Remove route paths
    for (const [, path] of sprites.routePaths) {
      app.stage.removeChild(path);
      path.destroy();
    }
    sprites.routePaths.clear();

    // Remove defenders
    for (const [, sprite] of sprites.defenders) {
      app.stage.removeChild(sprite);
      sprite.destroy();
    }
    sprites.defenders.clear();

    // Remove blockers
    for (const [, sprite] of sprites.blockers) {
      app.stage.removeChild(sprite);
      sprite.destroy();
    }
    sprites.blockers.clear();

    // Remove rushers
    for (const [, sprite] of sprites.rushers) {
      app.stage.removeChild(sprite);
      sprite.destroy();
    }
    sprites.rushers.clear();

    // Remove QB
    if (sprites.qb) {
      app.stage.removeChild(sprites.qb);
      sprites.qb.destroy();
      sprites.qb = null;
    }

    // Remove ball
    if (sprites.ball) {
      app.stage.removeChild(sprites.ball);
      sprites.ball.destroy();
      sprites.ball = null;
    }

    // Clear graphics objects (don't destroy, just clear)
    sprites.ballTrail?.clear();
    sprites.targetIndicator?.clear();
    sprites.readHighlight?.clear();
    sprites.engagementLines?.clear();
    sprites.pressureOverlay?.clear();
    sprites.zones?.clear();
  }, []);

  // Convert game coordinates to screen coordinates
  // Pocket sim uses y-positive = backfield, so we need to handle both
  const gameToScreen = useCallback((pos: Vec2, isPocketCoord: boolean = false): { x: number; y: number } => {
    if (isPocketCoord) {
      // Pocket sim: y > 0 means behind LOS
      return {
        x: CENTER_X + pos.x * PIXELS_PER_YARD,
        y: LOS_Y + pos.y * PIXELS_PER_YARD, // Add y (behind LOS)
      };
    }
    // Play sim: y > 0 means downfield
    return {
      x: CENTER_X + pos.x * PIXELS_PER_YARD,
      y: LOS_Y - pos.y * PIXELS_PER_YARD, // Subtract y (downfield)
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

    const currentTick = pocketState?.tick ?? 0;
    const currentQbId = pocketState?.qb?.id ?? null;

    // Build sets of current player IDs
    const currentBlockerIds = new Set(pocketState?.blockers?.map(b => b.id) ?? []);
    const currentRusherIds = new Set(pocketState?.rushers?.map(r => r.id) ?? []);

    // Detect reset or new simulation:
    // 1. Tick goes back to a lower value
    // 2. QB ID changed (new simulation with new player IDs)
    // 3. Blocker/Rusher IDs changed (indicates new simulation even if tick is same)
    const tickReset = currentTick < lastTickRef.current;
    const newSimulation = currentQbId !== null && lastQbIdRef.current !== null && currentQbId !== lastQbIdRef.current;

    // Check if player IDs differ from last render (any ID not present = new simulation)
    const blockerIdsChanged = lastBlockerIdsRef.current.size > 0 &&
      currentBlockerIds.size > 0 &&
      ![...currentBlockerIds].every(id => lastBlockerIdsRef.current.has(id));

    const rusherIdsChanged = lastRusherIdsRef.current.size > 0 &&
      currentRusherIds.size > 0 &&
      ![...currentRusherIds].every(id => lastRusherIdsRef.current.has(id));

    const shouldClear = tickReset || newSimulation || blockerIdsChanged || rusherIdsChanged;

    if (shouldClear) {
      clearAllSprites();
    }

    lastTickRef.current = currentTick;
    lastQbIdRef.current = currentQbId;
    lastBlockerIdsRef.current = currentBlockerIds;
    lastRusherIdsRef.current = currentRusherIds;

    updatePlayers();
  }, [playState, pocketState, pressureState, clearAllSprites]);

  const drawField = (app: Application) => {
    const fieldGraphics = new Graphics();

    // Draw yard lines (shows -10 to 25 yards based on canvas size)
    for (let yard = -10; yard <= 25; yard++) {
      const y = LOS_Y - yard * PIXELS_PER_YARD;
      if (y < 0 || y > CANVAS_HEIGHT) continue;

      const alpha = yard === 0 ? 1 : 0.2;
      const height = yard === 0 ? 3 : 1;

      fieldGraphics.rect(0, y - height / 2, CANVAS_WIDTH, height);
      fieldGraphics.fill({ color: COLORS.yardLine, alpha });

      // Yard markers
      if (yard % 5 === 0 && yard !== 0) {
        const yardText = new Text({
          text: yard > 0 ? `+${yard}` : `${yard}`,
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
    for (let yard = -8; yard <= 25; yard++) {
      const y = LOS_Y - yard * PIXELS_PER_YARD;
      if (y < 0 || y > CANVAS_HEIGHT) continue;
      fieldGraphics.rect(CENTER_X - 100, y - 1, 6, 2);
      fieldGraphics.fill({ color: COLORS.yardLine, alpha: 0.25 });
      fieldGraphics.rect(CENTER_X + 94, y - 1, 6, 2);
      fieldGraphics.fill({ color: COLORS.yardLine, alpha: 0.25 });
    }

    // Pocket zone indicator (behind LOS)
    fieldGraphics.rect(CENTER_X - 80, LOS_Y, 160, 130);
    fieldGraphics.fill({ color: 0x1a3d0c, alpha: 0.5 });

    app.stage.addChild(fieldGraphics);

    // Pressure overlay (for pressure visualization)
    const pressureOverlay = new Graphics();
    app.stage.addChild(pressureOverlay);
    spritesRef.current.pressureOverlay = pressureOverlay;

    // Zone visualization container
    const zones = new Graphics();
    app.stage.addChild(zones);
    spritesRef.current.zones = zones;

    // Engagement lines
    const engagementLines = new Graphics();
    app.stage.addChild(engagementLines);
    spritesRef.current.engagementLines = engagementLines;

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
    shape: 'circle' | 'square' | 'diamond',
    size: number = 8
  ): Container => {
    const container = new Container();

    const body = new Graphics();
    if (shape === 'circle') {
      body.circle(0, 0, size);
      body.fill({ color });
      body.stroke({ color: 0xffffff, width: 2 });
    } else if (shape === 'square') {
      body.rect(-size, -size, size * 2, size * 2);
      body.fill({ color });
      body.stroke({ color: 0xffffff, width: 2 });
    } else if (shape === 'diamond') {
      body.moveTo(0, -size);
      body.lineTo(size, 0);
      body.lineTo(0, size);
      body.lineTo(-size, 0);
      body.closePath();
      body.fill({ color });
      body.stroke({ color: 0xffffff, width: 2 });
    }
    body.name = 'body';
    container.addChild(body);

    // Direction indicator
    const direction = new Graphics();
    direction.moveTo(0, -size * 0.7);
    direction.lineTo(0, -size * 1.4);
    direction.stroke({ color: 0xffffff, width: 2 });
    direction.name = 'direction';
    container.addChild(direction);

    // Label
    const text = new Text({
      text: label,
      style: new TextStyle({
        fontFamily: 'Arial',
        fontSize: 9,
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
    ball.circle(0, 0, 7);
    ball.fill({ color: COLORS.ball });
    ball.stroke({ color: 0x8b4513, width: 2 });
    ball.name = 'ball';
    container.addChild(ball);

    return container;
  };

  const updatePlayers = () => {
    const app = appRef.current;
    if (!app) return;

    const sprites = spritesRef.current;

    // Update pressure overlay
    updatePressureOverlay();

    // Update engagement lines
    updateEngagementLines();

    // Update ball trail and target
    updateBallVisuals();

    // Update read highlight
    updateReadHighlight();

    // Update QB from pocket state (use pocket position for accurate pressure visualization)
    if (pocketState.qb) {
      if (!sprites.qb) {
        sprites.qb = createPlayerSprite('QB', COLORS.qb, 'circle', 16);
        app.stage.addChild(sprites.qb);
      }

      const screen = gameToScreen(pocketState.qb.position, true);
      sprites.qb.x = screen.x;
      sprites.qb.y = screen.y;

      // Update direction from play state QB facing
      const direction = sprites.qb.getChildByName('direction') as Graphics;
      if (direction && playState.qb.facing) {
        const angle = Math.atan2(-playState.qb.facing.y, playState.qb.facing.x) - Math.PI / 2;
        direction.rotation = angle;
      }
    }

    // Update blockers
    for (const blocker of pocketState.blockers) {
      let sprite = sprites.blockers.get(blocker.id);

      if (!sprite) {
        const color = OL_COLORS[blocker.role] || COLORS.ol;
        sprite = createPlayerSprite(blocker.role.toUpperCase(), color, 'square', 10);
        app.stage.addChild(sprite);
        sprites.blockers.set(blocker.id, sprite);
      }

      const screen = gameToScreen(blocker.position, true);
      sprite.x = screen.x;
      sprite.y = screen.y;

      // Update direction
      const direction = sprite.getChildByName('direction') as Graphics;
      if (direction && blocker.facing) {
        const angle = Math.atan2(-blocker.facing.y, blocker.facing.x) - Math.PI / 2;
        direction.rotation = angle;
      }

      // Dim if down
      sprite.alpha = blocker.is_down ? 0.4 : 1.0;
    }

    // Update rushers
    for (const rusher of pocketState.rushers) {
      let sprite = sprites.rushers.get(rusher.id);

      if (!sprite) {
        const color = DL_COLORS[rusher.role] || COLORS.dl;
        sprite = createPlayerSprite(rusher.role.toUpperCase(), color, 'diamond', 10);
        app.stage.addChild(sprite);
        sprites.rushers.set(rusher.id, sprite);
      }

      const screen = gameToScreen(rusher.position, true);
      sprite.x = screen.x;
      sprite.y = screen.y;

      // Update direction
      const direction = sprite.getChildByName('direction') as Graphics;
      if (direction && rusher.facing) {
        const angle = Math.atan2(-rusher.facing.y, rusher.facing.x) - Math.PI / 2;
        direction.rotation = angle;
      }

      // Scale up if free rusher
      sprite.scale.set(rusher.is_free ? 1.3 : 1.0);
      sprite.alpha = rusher.is_down ? 0.4 : 1.0;
    }

    // Update ball
    if (playState.ball) {
      if (!sprites.ball) {
        sprites.ball = createBallSprite();
        app.stage.addChild(sprites.ball);
      }

      const screen = gameToScreen(playState.ball.position, false);
      sprites.ball.x = screen.x;
      sprites.ball.y = screen.y;

      sprites.ball.visible = playState.ball.is_thrown || playState.ball.is_caught || playState.ball.is_incomplete;

      if (playState.ball.is_caught || playState.ball.intercepted_by_id) {
        sprites.ball.scale.set(1.5);
      } else {
        sprites.ball.scale.set(1.0);
      }
    }

    // Update receivers
    for (const rcvr of playState.receivers) {
      let sprite = sprites.receivers.get(rcvr.id);

      if (!sprite) {
        const color = WR_COLORS[rcvr.alignment] || COLORS.wr;
        sprite = createPlayerSprite(rcvr.alignment.toUpperCase(), color, 'circle', 11);
        app.stage.addChild(sprite);
        sprites.receivers.set(rcvr.id, sprite);

        // Create route path
        const routePath = new Graphics();
        app.stage.addChildAt(routePath, 1);
        sprites.routePaths.set(rcvr.id, routePath);
      }

      const screen = gameToScreen(rcvr.position, false);
      sprite.x = screen.x;
      sprite.y = screen.y;

      // Update direction
      const direction = sprite.getChildByName('direction') as Graphics;
      if (direction && rcvr.facing) {
        const angle = Math.atan2(-rcvr.facing.y, rcvr.facing.x) - Math.PI / 2;
        direction.rotation = angle;
      }

      // Highlight target
      if (playState.qb.target_receiver_id === rcvr.id) {
        sprite.scale.set(1.3);
      } else {
        sprite.scale.set(1.0);
      }

      // Update route path
      updateRoutePath(rcvr);
    }

    // Update defenders
    for (const defender of playState.defenders) {
      let sprite = sprites.defenders.get(defender.id);

      if (!sprite) {
        const color = DB_COLORS[defender.alignment] || COLORS.db;
        sprite = createPlayerSprite(defender.alignment.toUpperCase(), color, 'square', 11);
        app.stage.addChild(sprite);
        sprites.defenders.set(defender.id, sprite);
      }

      const screen = gameToScreen(defender.position, false);
      sprite.x = screen.x;
      sprite.y = screen.y;

      // Update direction
      const direction = sprite.getChildByName('direction') as Graphics;
      if (direction && defender.facing) {
        const angle = Math.atan2(-defender.facing.y, defender.facing.x) - Math.PI / 2;
        direction.rotation = angle;
      }

      // Highlight interceptor
      if (playState.ball.intercepted_by_id === defender.id) {
        sprite.scale.set(1.4);
      } else {
        sprite.scale.set(1.0);
      }
    }
  };

  const updatePressureOverlay = () => {
    const overlay = spritesRef.current.pressureOverlay;
    if (!overlay || !pressureState) return;

    overlay.clear();

    // Draw pressure gradient around QB
    if (pressureState.total > 0.1) {
      const qbScreen = gameToScreen(pocketState.qb.position, true);
      const radius = 60 - pressureState.total * 40; // Shrinks with pressure

      overlay.circle(qbScreen.x, qbScreen.y, radius);
      overlay.fill({
        color: COLORS.pressureZone,
        alpha: pressureState.total * 0.3,
      });

      // Panic flash
      if (pressureState.panic) {
        overlay.circle(qbScreen.x, qbScreen.y, 80);
        overlay.stroke({
          color: 0xef4444,
          width: 4,
          alpha: 0.8,
        });
      }
    }
  };

  const updateEngagementLines = () => {
    const lines = spritesRef.current.engagementLines;
    if (!lines) return;

    lines.clear();

    for (const eng of pocketState.engagements) {
      const contactScreen = gameToScreen(eng.contact_point, true);

      // Draw engagement indicator
      let color = COLORS.engagement;
      if (eng.state === 'rusher_winning' || eng.state === 'shed') {
        color = 0xef4444; // Red
      } else if (eng.state === 'blocker_winning' || eng.state === 'pancake') {
        color = 0x22c55e; // Green
      }

      lines.circle(contactScreen.x, contactScreen.y, 6);
      lines.fill({ color, alpha: 0.6 });
    }
  };

  const updateBallVisuals = () => {
    const ballTrail = spritesRef.current.ballTrail;
    const targetIndicator = spritesRef.current.targetIndicator;
    if (!ballTrail || !targetIndicator) return;

    ballTrail.clear();
    targetIndicator.clear();

    if (!playState.ball.is_thrown || playState.ball.is_caught || playState.ball.is_incomplete) return;

    // Draw ball trajectory line
    const startScreen = gameToScreen(playState.ball.start_position, false);
    const targetScreen = gameToScreen(playState.ball.target_position, false);

    ballTrail.moveTo(startScreen.x, startScreen.y);
    ballTrail.lineTo(targetScreen.x, targetScreen.y);
    ballTrail.stroke({
      color: COLORS.ballTrail,
      width: 2,
      alpha: 0.5,
    });

    // Target indicator
    targetIndicator.moveTo(targetScreen.x - 8, targetScreen.y - 8);
    targetIndicator.lineTo(targetScreen.x + 8, targetScreen.y + 8);
    targetIndicator.moveTo(targetScreen.x + 8, targetScreen.y - 8);
    targetIndicator.lineTo(targetScreen.x - 8, targetScreen.y + 8);
    targetIndicator.stroke({
      color: COLORS.target,
      width: 3,
      alpha: 0.8,
    });

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

    if (playState.qb.has_thrown) return;

    const currentReadId = playState.qb.read_order[playState.qb.current_read_idx];
    const currentReadReceiver = playState.receivers.find((r) => r.id === currentReadId);
    if (!currentReadReceiver) return;

    const screen = gameToScreen(currentReadReceiver.position, false);

    readHighlight.circle(screen.x, screen.y, 18);
    readHighlight.stroke({
      color: COLORS.readIndicator,
      width: 3,
      alpha: 0.7,
    });

    // Line from QB to current read
    const qbScreen = gameToScreen(pocketState.qb.position, true);
    readHighlight.moveTo(qbScreen.x, qbScreen.y);
    readHighlight.lineTo(screen.x, screen.y);
    readHighlight.stroke({
      color: COLORS.readIndicator,
      width: 1,
      alpha: 0.3,
    });
  };

  const updateRoutePath = (rcvr: TeamReceiver) => {
    const routePath = spritesRef.current.routePaths.get(rcvr.id);
    if (!routePath) return;

    routePath.clear();

    const route = rcvr.route;
    if (route.length === 0) return;

    const startX = route[0]?.position.x ?? 0;
    const start = gameToScreen({ x: startX, y: 0 }, false);

    routePath.moveTo(start.x, start.y);
    route.forEach((waypoint) => {
      const screen = gameToScreen(waypoint.position, false);
      routePath.lineTo(screen.x, screen.y);
    });

    const color = WR_COLORS[rcvr.alignment] || COLORS.routePath;
    routePath.stroke({
      color,
      width: 2,
      alpha: 0.3,
    });

    // Break point markers
    route.forEach((waypoint) => {
      if (waypoint.is_break) {
        const screen = gameToScreen(waypoint.position, false);
        routePath.circle(screen.x, screen.y, 4);
        routePath.fill({ color: 0xfbbf24, alpha: 0.6 });
      }
    });
  };

  return (
    <div className="integrated-sim-canvas">
      <div ref={canvasRef} className="canvas-container" />
    </div>
  );
}
