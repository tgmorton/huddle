/**
 * PixiJS Canvas for team route simulation visualization
 * Shows multiple receivers and defensive backs on a field view
 */

import { useEffect, useRef, useCallback } from 'react';
import { Application, Graphics, Text, TextStyle, Container } from 'pixi.js';

// Canvas dimensions - wider for full field width
const CANVAS_WIDTH = 900;
const CANVAS_HEIGHT = 700;

// Field conversion: 1 yard = 14 pixels (to fit wider routes)
const PIXELS_PER_YARD = 14;

// Field origin - center of canvas horizontally, LOS near bottom
const CENTER_X = CANVAS_WIDTH / 2;
const LOS_Y = CANVAS_HEIGHT - 80;

// Colors
const COLORS = {
  field: 0x2d5016,
  los: 0xffffff,
  yardLine: 0xffffff,
  wr: 0x22c55e,       // Green for receivers
  db: 0xf97316,       // Orange for defenders
  routePath: 0x3b82f6,
  zoneFill: 0x6366f1,
  text: 0xffffff,
};

// Receiver colors by position
const WR_COLORS: Record<string, number> = {
  x: 0x22c55e,      // Green
  z: 0x10b981,      // Emerald
  slot_l: 0x14b8a6, // Teal
  slot_r: 0x06b6d4, // Cyan
  te: 0x0ea5e9,     // Sky
};

// DB colors by position
const DB_COLORS: Record<string, number> = {
  cb1: 0xf97316,    // Orange
  cb2: 0xfb923c,    // Amber
  nickel: 0xf59e0b, // Yellow
  ss: 0xef4444,     // Red
  fs: 0xec4899,     // Pink
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

interface MatchupResult {
  receiver_id: string;
  defender_id: string;
  separation: number;
  max_separation: number;
  result: string;
}

interface TeamRouteSimState {
  receivers: TeamReceiver[];
  defenders: TeamDefender[];
  formation: string;
  coverage: string;
  concept: string;
  matchups: Record<string, MatchupResult>;
  tick: number;
  is_complete: boolean;
}

interface TeamRoutesCanvasProps {
  state: TeamRouteSimState;
}

interface PlayerSprites {
  receivers: Map<string, Container>;
  defenders: Map<string, Container>;
  routePaths: Map<string, Graphics>;
  zones: Graphics | null;
}

export function TeamRoutesCanvas({ state }: TeamRoutesCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const spritesRef = useRef<PlayerSprites>({
    receivers: new Map(),
    defenders: new Map(),
    routePaths: new Map(),
    zones: null,
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

    // Draw yard lines
    for (let yard = -2; yard <= 35; yard++) {
      const y = LOS_Y - yard * PIXELS_PER_YARD;
      if (y < 0) continue;

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
            fill: COLORS.text,
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
        fill: COLORS.text,
      }),
    });
    losText.x = CANVAS_WIDTH - 32;
    losText.y = LOS_Y + 4;
    app.stage.addChild(losText);

    // Hash marks
    for (let yard = 0; yard <= 35; yard++) {
      const y = LOS_Y - yard * PIXELS_PER_YARD;
      if (y < 0) continue;
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
  };

  const createPlayerSprite = (
    label: string,
    color: number,
    isDefender: boolean
  ): Container => {
    const container = new Container();

    const body = new Graphics();
    if (isDefender) {
      // Square for defenders
      body.rect(-8, -8, 16, 16);
    } else {
      // Circle for receivers
      body.circle(0, 0, 8);
    }
    body.fill({ color });
    body.stroke({ color: 0xffffff, width: 2 });
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
        fontSize: 8,
        fill: 0xffffff,
        fontWeight: 'bold',
      }),
    });
    text.anchor.set(0.5);
    text.name = 'label';
    container.addChild(text);

    return container;
  };

  const updatePlayers = () => {
    const app = appRef.current;
    if (!app) return;

    const sprites = spritesRef.current;

    // Draw zone areas first (if zone coverage)
    updateZones();

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
        app.stage.addChildAt(routePath, 1); // Behind players
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

  const updateZones = () => {
    const zones = spritesRef.current.zones;
    if (!zones) return;

    zones.clear();

    // Only draw zones for zone coverages
    if (!state.coverage.includes('cover_2') &&
        !state.coverage.includes('cover_3') &&
        !state.coverage.includes('cover_4')) {
      return;
    }

    // Draw zone areas for defenders with zone assignments
    for (const defender of state.defenders) {
      if (defender.zone_assignment) {
        const zoneCenter = getZoneCenter(defender.zone_assignment);
        if (zoneCenter) {
          const screen = gameToScreen(zoneCenter);
          const radius = getZoneRadius(defender.zone_assignment) * PIXELS_PER_YARD;

          const color = DB_COLORS[defender.alignment] || COLORS.zoneFill;
          zones.circle(screen.x, screen.y, radius);
          zones.fill({ color, alpha: 0.1 });
          zones.stroke({ color, width: 1, alpha: 0.3 });
        }
      }
    }
  };

  const getZoneCenter = (zone: string): Vec2 | null => {
    const centers: Record<string, Vec2> = {
      deep_third_l: { x: -15, y: 25 },
      deep_third_m: { x: 0, y: 28 },
      deep_third_r: { x: 15, y: 25 },
      deep_half_l: { x: -12, y: 22 },
      deep_half_r: { x: 12, y: 22 },
      deep_quarter_1: { x: -18, y: 20 },
      deep_quarter_2: { x: -6, y: 22 },
      deep_quarter_3: { x: 6, y: 22 },
      deep_quarter_4: { x: 18, y: 20 },
      flat_l: { x: -12, y: 3 },
      flat_r: { x: 12, y: 3 },
      hook_l: { x: -5, y: 10 },
      hook_r: { x: 5, y: 10 },
      curl_flat_l: { x: -10, y: 8 },
      curl_flat_r: { x: 10, y: 8 },
      middle: { x: 0, y: 12 },
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

    // Get starting position (first point of route minus the offset, or use alignment position)
    const startX = route[0]?.position.x - (route[0]?.position.x - rcvr.position.x) || rcvr.position.x;
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
    <div className="team-routes-canvas">
      <div ref={canvasRef} className="canvas-container" />
    </div>
  );
}
