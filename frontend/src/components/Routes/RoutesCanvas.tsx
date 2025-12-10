/**
 * PixiJS Canvas for route running simulation visualization
 * Top-down view: offense going up (positive y), defense tracking
 */

import { useEffect, useRef, useCallback } from 'react';
import { Application, Graphics, Text, TextStyle, Container } from 'pixi.js';

// Canvas dimensions - wider for horizontal routes
const CANVAS_WIDTH = 700;
const CANVAS_HEIGHT = 700;

// Field conversion: 1 yard = 22 pixels (smaller to fit deep routes up to 30 yards)
const PIXELS_PER_YARD = 22;

// Field origin - center of canvas horizontally, LOS near bottom
const CENTER_X = CANVAS_WIDTH / 2;
const LOS_Y = CANVAS_HEIGHT - 60; // LOS near bottom

// Colors
const COLORS = {
  field: 0x2d5016,
  los: 0xffffff,
  yardLine: 0xffffff,
  wr: 0x22c55e, // Green for receiver
  db: 0xf97316, // Orange for defender
  routePath: 0x3b82f6,
  breakPoint: 0xfbbf24,
  separation: 0xef4444,
  text: 0xffffff,
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

interface Receiver {
  id: string;
  position: Vec2;
  route: RouteWaypoint[];
  current_waypoint_idx: number;
  animation: string;
  facing: Vec2;
}

interface DefensiveBack {
  id: string;
  position: Vec2;
  coverage_type: string;
  animation: string;
  facing: Vec2;
  reaction_delay: number;
}

interface RouteSimState {
  receiver: Receiver;
  defender: DefensiveBack;
  separation: number;
  max_separation: number;
  tick: number;
  is_complete: boolean;
  result: string;
  phase: string;
  route_type: string;
  release_result: string | null;
}

interface RoutesCanvasProps {
  state: RouteSimState;
}

interface SpriteRefs {
  wr: Container | null;
  db: Container | null;
  routePath: Graphics | null;
  separationLine: Graphics | null;
  breakMarkers: Graphics | null;
}

export function RoutesCanvas({ state }: RoutesCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const spritesRef = useRef<SpriteRefs>({
    wr: null,
    db: null,
    routePath: null,
    separationLine: null,
    breakMarkers: null,
  });
  const initializedRef = useRef(false);

  // Convert game coordinates to screen coordinates
  // Game: x = lateral (neg=left), y = depth (pos=toward endzone/up)
  // Screen: x = right, y = down (inverted)
  const gameToScreen = useCallback((pos: Vec2): { x: number; y: number } => {
    return {
      x: CENTER_X + pos.x * PIXELS_PER_YARD,
      y: LOS_Y - pos.y * PIXELS_PER_YARD, // Invert Y so positive goes up
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
      createSprites(app);
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

  // Update positions when state changes
  useEffect(() => {
    if (!appRef.current || !initializedRef.current) return;
    updatePositions();
  }, [state]);

  const drawField = (app: Application) => {
    const fieldGraphics = new Graphics();

    // Draw yard lines (horizontal) - now showing up to 30 yards
    for (let yard = -2; yard <= 30; yard++) {
      const y = LOS_Y - yard * PIXELS_PER_YARD;
      if (y < 0) continue; // Don't draw off screen

      const alpha = yard === 0 ? 1 : 0.25;
      const height = yard === 0 ? 3 : 1;

      fieldGraphics.rect(0, y - height / 2, CANVAS_WIDTH, height);
      fieldGraphics.fill({ color: COLORS.yardLine, alpha });

      // Yard markers (every 5 yards)
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
        yardText.alpha = 0.5;
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

    // Hash marks (simplified)
    for (let yard = 0; yard <= 30; yard++) {
      const y = LOS_Y - yard * PIXELS_PER_YARD;
      if (y < 0) continue;
      // Left hash
      fieldGraphics.rect(CENTER_X - 80, y - 1, 8, 2);
      fieldGraphics.fill({ color: COLORS.yardLine, alpha: 0.3 });
      // Right hash
      fieldGraphics.rect(CENTER_X + 72, y - 1, 8, 2);
      fieldGraphics.fill({ color: COLORS.yardLine, alpha: 0.3 });
    }

    app.stage.addChild(fieldGraphics);
  };

  const createSprites = (app: Application) => {
    const sprites = spritesRef.current;

    // Route path (behind players)
    const routePath = new Graphics();
    app.stage.addChild(routePath);
    sprites.routePath = routePath;

    // Break markers
    const breakMarkers = new Graphics();
    app.stage.addChild(breakMarkers);
    sprites.breakMarkers = breakMarkers;

    // Separation line
    const separationLine = new Graphics();
    app.stage.addChild(separationLine);
    sprites.separationLine = separationLine;

    // Create WR sprite
    const wrContainer = createPlayerSprite('WR', COLORS.wr);
    app.stage.addChild(wrContainer);
    sprites.wr = wrContainer;

    // Create DB sprite
    const dbContainer = createPlayerSprite('DB', COLORS.db);
    app.stage.addChild(dbContainer);
    sprites.db = dbContainer;
  };

  const createPlayerSprite = (label: string, color: number): Container => {
    const container = new Container();

    // Player body (circle for players) - smaller for zoomed out view
    const body = new Graphics();
    body.circle(0, 0, 10);
    body.fill({ color });
    body.stroke({ color: 0xffffff, width: 2 });
    body.name = 'body';
    container.addChild(body);

    // Direction indicator
    const direction = new Graphics();
    direction.moveTo(0, -8);
    direction.lineTo(0, -14);
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

  const updatePositions = () => {
    const sprites = spritesRef.current;
    if (!sprites.wr || !sprites.db) return;

    // Update WR position
    const wrScreen = gameToScreen(state.receiver.position);
    sprites.wr.x = wrScreen.x;
    sprites.wr.y = wrScreen.y;

    // Update WR direction indicator
    const wrDirection = sprites.wr.getChildByName('direction') as Graphics;
    if (wrDirection) {
      const facing = state.receiver.facing;
      const angle = Math.atan2(-facing.y, facing.x) - Math.PI / 2;
      wrDirection.rotation = angle;
    }

    // Update DB position
    const dbScreen = gameToScreen(state.defender.position);
    sprites.db.x = dbScreen.x;
    sprites.db.y = dbScreen.y;

    // Update DB direction indicator
    const dbDirection = sprites.db.getChildByName('direction') as Graphics;
    if (dbDirection) {
      const facing = state.defender.facing;
      const angle = Math.atan2(-facing.y, facing.x) - Math.PI / 2;
      dbDirection.rotation = angle;
    }

    updateRoutePath();
    updateSeparationLine();
    updateBreakMarkers();
  };

  const updateRoutePath = () => {
    const routePath = spritesRef.current.routePath;
    if (!routePath) return;

    routePath.clear();

    // Draw the route as a dashed line
    const route = state.receiver.route;
    if (route.length === 0) return;

    // Start from LOS (0, 0)
    const start = gameToScreen({ x: 0, y: 0 });

    routePath.moveTo(start.x, start.y);

    // Draw path through waypoints
    route.forEach((waypoint, _idx) => {
      const screen = gameToScreen(waypoint.position);

      // Dashed line effect
      routePath.lineTo(screen.x, screen.y);
    });

    routePath.stroke({
      color: COLORS.routePath,
      width: 2,
      alpha: 0.5,
    });

    // Highlight completed portion of route
    const currentIdx = state.receiver.current_waypoint_idx;
    if (currentIdx > 0) {
      routePath.moveTo(start.x, start.y);

      for (let i = 0; i < currentIdx && i < route.length; i++) {
        const screen = gameToScreen(route[i].position);
        routePath.lineTo(screen.x, screen.y);
      }

      // Draw to current position
      const wrScreen = gameToScreen(state.receiver.position);
      routePath.lineTo(wrScreen.x, wrScreen.y);

      routePath.stroke({
        color: COLORS.routePath,
        width: 3,
        alpha: 0.8,
      });
    }
  };

  const updateBreakMarkers = () => {
    const breakMarkers = spritesRef.current.breakMarkers;
    if (!breakMarkers) return;

    breakMarkers.clear();

    // Mark break points
    state.receiver.route.forEach((waypoint) => {
      if (waypoint.is_break) {
        const screen = gameToScreen(waypoint.position);

        // Diamond marker for break - smaller for zoomed out view
        breakMarkers.moveTo(screen.x, screen.y - 5);
        breakMarkers.lineTo(screen.x + 5, screen.y);
        breakMarkers.lineTo(screen.x, screen.y + 5);
        breakMarkers.lineTo(screen.x - 5, screen.y);
        breakMarkers.closePath();
        breakMarkers.fill({ color: COLORS.breakPoint, alpha: 0.7 });
        breakMarkers.stroke({ color: 0xffffff, width: 1, alpha: 0.5 });
      }
    });
  };

  const updateSeparationLine = () => {
    const separationLine = spritesRef.current.separationLine;
    if (!separationLine) return;

    separationLine.clear();

    const wrScreen = gameToScreen(state.receiver.position);
    const dbScreen = gameToScreen(state.defender.position);

    // Draw line between WR and DB
    separationLine.moveTo(wrScreen.x, wrScreen.y);
    separationLine.lineTo(dbScreen.x, dbScreen.y);

    // Color based on separation
    const sepColor =
      state.separation > 3
        ? 0x22c55e // Open
        : state.separation > 1
        ? 0xf59e0b // Contested
        : 0xef4444; // Covered

    separationLine.stroke({
      color: sepColor,
      width: 2,
      alpha: 0.6,
    });

    // Separation text at midpoint
    const midX = (wrScreen.x + dbScreen.x) / 2;
    const midY = (wrScreen.y + dbScreen.y) / 2;

    // Find or create separation text
    const app = appRef.current;
    if (app) {
      let sepText = app.stage.getChildByName('separation-text') as Text;
      if (!sepText) {
        sepText = new Text({
          text: '',
          style: new TextStyle({
            fontFamily: 'Arial',
            fontSize: 12,
            fill: 0xffffff,
            fontWeight: 'bold',
          }),
        });
        sepText.name = 'separation-text';
        sepText.anchor.set(0.5);
        app.stage.addChild(sepText);
      }

      sepText.text = `${state.separation.toFixed(1)}yd`;
      sepText.x = midX + 15;
      sepText.y = midY;
      sepText.style.fill = sepColor;
    }
  };

  return (
    <div className="routes-canvas">
      <div ref={canvasRef} className="canvas-container" />
    </div>
  );
}
