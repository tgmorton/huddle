/**
 * PixiJS Canvas for pocket collapse simulation visualization
 * Top-down view: offense going up (positive y), defense at bottom
 */

import { useEffect, useRef, useCallback } from 'react';
import { Application, Graphics, Text, TextStyle, Container } from 'pixi.js';

// Canvas dimensions
const CANVAS_WIDTH = 700;
const CANVAS_HEIGHT = 500;

// Field conversion: 1 yard = 45 pixels
const PIXELS_PER_YARD = 45;

// Field origin - center of canvas horizontally, LOS near bottom
const CENTER_X = CANVAS_WIDTH / 2;
const LOS_Y = CANVAS_HEIGHT - 80;  // LOS near bottom

// Colors
const COLORS = {
  field: 0x2d5016,
  los: 0xffffff,
  qbZone: 0xff0000,
  qb: 0xf59e0b,
  blocker: 0x3b82f6,
  rusher: 0xef4444,
  engaged: 0xfbbf24,
  text: 0xffffff,
};

interface Vec2 {
  x: number;
  y: number;
}

interface Player {
  id: string;
  role: string;
  position: Vec2;
  is_free: boolean;
  is_down: boolean;
  animation: string;
}

interface Engagement {
  blocker_roles: string[];
  rusher_role: string;
  contact_point: Vec2;
  state: string;
}

interface QBState {
  action: string;
  pressure_level: string;
  throw_timer: number;
  throw_target_tick: number;
  pressure_left: number;
  pressure_right: number;
  pressure_front: number;
}

interface PocketState {
  qb: Player;
  blockers: Player[];
  rushers: Player[];
  engagements: Engagement[];
  tick: number;
  is_complete: boolean;
  result: string;
  qb_state: QBState | null;
}

interface PocketCanvasProps {
  state: PocketState;
}

interface SpriteRefs {
  qb: Container | null;
  blockers: Map<string, Container>;
  rushers: Map<string, Container>;
  engagementLines: Graphics | null;
  pressureRing: Graphics | null;
}

// Role to label mapping
const ROLE_LABELS: Record<string, string> = {
  qb: 'QB',
  lt: 'LT', lg: 'LG', c: 'C', rg: 'RG', rt: 'RT',
  le: 'LE', dt_l: 'DT', nt: 'NT', dt_r: 'DT', re: 'RE',
  blitz_l: 'LB', blitz_r: 'LB',
};

export function PocketCanvas({ state }: PocketCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const spritesRef = useRef<SpriteRefs>({
    qb: null,
    blockers: new Map(),
    rushers: new Map(),
    engagementLines: null,
    pressureRing: null,
  });
  const initializedRef = useRef(false);
  const playerCountRef = useRef({ blockers: 0, rushers: 0 });

  // Convert game coordinates to screen coordinates
  // Game: x = lateral (neg=left), y = depth (pos=toward QB/up)
  // Screen: x = right, y = down (inverted)
  const gameToScreen = useCallback((pos: Vec2): { x: number; y: number } => {
    return {
      x: CENTER_X + pos.x * PIXELS_PER_YARD,
      y: LOS_Y - pos.y * PIXELS_PER_YARD,  // Invert Y so positive goes up
    };
  }, []);

  // Check if we need to recreate sprites (player count changed)
  const needsReinit = useCallback(() => {
    return (
      state.blockers.length !== playerCountRef.current.blockers ||
      state.rushers.length !== playerCountRef.current.rushers
    );
  }, [state.blockers.length, state.rushers.length]);

  // Initialize PixiJS
  useEffect(() => {
    if (!canvasRef.current) return;

    // Check if we need to reinitialize due to player count change
    if (initializedRef.current && !needsReinit()) {
      return;
    }

    // Clean up existing
    if (appRef.current) {
      appRef.current.destroy(true);
      appRef.current = null;
    }

    // Clear canvas
    while (canvasRef.current.firstChild) {
      canvasRef.current.removeChild(canvasRef.current.firstChild);
    }

    // Reset refs
    spritesRef.current = {
      qb: null,
      blockers: new Map(),
      rushers: new Map(),
      engagementLines: null,
      pressureRing: null,
    };

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
      playerCountRef.current = {
        blockers: state.blockers.length,
        rushers: state.rushers.length,
      };

      drawField(app);

      // Pressure ring (behind everything else)
      const pressureRing = new Graphics();
      app.stage.addChild(pressureRing);
      spritesRef.current.pressureRing = pressureRing;

      const engLines = new Graphics();
      app.stage.addChild(engLines);
      spritesRef.current.engagementLines = engLines;

      createSprites(app);
    };

    init();

    return () => {
      mounted = false;
    };
  }, [state.blockers.length, state.rushers.length]);

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

    // Draw yard lines (horizontal)
    for (let yard = -1; yard <= 10; yard++) {
      const y = LOS_Y - yard * PIXELS_PER_YARD;
      const alpha = yard === 0 ? 1 : 0.3;
      const height = yard === 0 ? 3 : 1;

      fieldGraphics.rect(0, y - height / 2, CANVAS_WIDTH, height);
      fieldGraphics.fill({ color: COLORS.los, alpha });
    }

    // LOS label
    const losText = new Text({
      text: 'LOS',
      style: new TextStyle({
        fontFamily: 'Arial',
        fontSize: 12,
        fill: COLORS.text,
      }),
    });
    losText.x = 10;
    losText.y = LOS_Y + 5;
    app.stage.addChild(losText);

    // QB zone indicator
    const qbY = LOS_Y - state.qb.position.y * PIXELS_PER_YARD;
    fieldGraphics.circle(CENTER_X, qbY, 30);
    fieldGraphics.fill({ color: COLORS.qbZone, alpha: 0.15 });
    fieldGraphics.stroke({ color: COLORS.qbZone, width: 2, alpha: 0.5 });

    app.stage.addChild(fieldGraphics);
  };

  const createSprites = (app: Application) => {
    const sprites = spritesRef.current;

    // Create QB sprite
    const qbContainer = createPlayerSprite(state.qb, COLORS.qb, 'qb');
    const qbScreen = gameToScreen(state.qb.position);
    qbContainer.x = qbScreen.x;
    qbContainer.y = qbScreen.y;
    app.stage.addChild(qbContainer);
    sprites.qb = qbContainer;

    // Create blocker sprites
    state.blockers.forEach((blocker) => {
      const container = createPlayerSprite(blocker, COLORS.blocker, 'blocker');
      const screen = gameToScreen(blocker.position);
      container.x = screen.x;
      container.y = screen.y;
      app.stage.addChild(container);
      sprites.blockers.set(blocker.role, container);
    });

    // Create rusher sprites
    state.rushers.forEach((rusher) => {
      const container = createPlayerSprite(rusher, COLORS.rusher, 'rusher');
      const screen = gameToScreen(rusher.position);
      container.x = screen.x;
      container.y = screen.y;
      app.stage.addChild(container);
      sprites.rushers.set(rusher.role, container);
    });
  };

  const createPlayerSprite = (player: Player, color: number, type: string): Container => {
    const container = new Container();

    // Glow for free rushers
    if (type === 'rusher') {
      const glow = new Graphics();
      glow.circle(0, 0, 22);
      glow.fill({ color: 0xffff00, alpha: 0 });
      glow.name = 'glow';
      container.addChild(glow);
    }

    // Player body
    const body = new Graphics();
    if (type === 'qb') {
      body.circle(0, 0, 18);
    } else {
      body.roundRect(-14, -16, 28, 32, 6);
    }
    body.fill({ color });
    body.stroke({ color: 0xffffff, width: 2 });
    body.name = 'body';
    container.addChild(body);

    // Label
    const label = ROLE_LABELS[player.role] || player.role.toUpperCase();
    const text = new Text({
      text: label,
      style: new TextStyle({
        fontFamily: 'Arial',
        fontSize: type === 'qb' ? 12 : 10,
        fill: type === 'qb' ? 0x000000 : COLORS.text,
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
    if (!sprites.qb) return;

    // Update QB position
    const qbScreen = gameToScreen(state.qb.position);
    sprites.qb.x = qbScreen.x;
    sprites.qb.y = qbScreen.y;

    // Update blocker positions
    state.blockers.forEach((blocker) => {
      const sprite = sprites.blockers.get(blocker.role);
      if (sprite) {
        const screen = gameToScreen(blocker.position);
        sprite.x = screen.x;
        sprite.y = screen.y;
      }
    });

    // Update rusher positions and visual state
    state.rushers.forEach((rusher) => {
      const sprite = sprites.rushers.get(rusher.role);
      if (sprite) {
        const screen = gameToScreen(rusher.position);
        sprite.x = screen.x;
        sprite.y = screen.y;

        const body = sprite.getChildByName('body') as Graphics;
        const glow = sprite.getChildByName('glow') as Graphics;
        const label = sprite.getChildByName('label') as Text;

        if (body && glow && label) {
          body.clear();
          body.roundRect(-14, -16, 28, 32, 6);

          if (rusher.is_down) {
            body.fill({ color: 0x666666, alpha: 0.6 });
            body.stroke({ color: 0x888888, width: 2 });
            label.style.fill = 0x999999;
            glow.clear();
          } else if (rusher.is_free) {
            body.fill({ color: COLORS.rusher });
            body.stroke({ color: 0xffff00, width: 3 });
            label.style.fill = COLORS.text;
            glow.clear();
            glow.circle(0, 0, 22);
            glow.fill({ color: 0xffff00, alpha: 0.3 });
          } else {
            body.fill({ color: COLORS.rusher });
            body.stroke({ color: 0xffffff, width: 2 });
            label.style.fill = COLORS.text;
            glow.clear();
          }
        }
      }
    });

    updateEngagementLines();
    updatePressureRing();
  };

  const updatePressureRing = () => {
    const ring = spritesRef.current.pressureRing;
    if (!ring) return;

    ring.clear();

    const qbState = state.qb_state;
    if (!qbState) return;

    const qbScreen = gameToScreen(state.qb.position);

    // Get pressure level color
    const pressureColors: Record<string, number> = {
      clean: 0x22c55e,
      light: 0x84cc16,
      moderate: 0xf59e0b,
      heavy: 0xf97316,
      critical: 0xef4444,
    };
    const ringColor = pressureColors[qbState.pressure_level] || 0x888888;

    // Draw main pressure ring
    const ringRadius = 35;
    ring.circle(qbScreen.x, qbScreen.y, ringRadius);
    ring.stroke({ color: ringColor, width: 3, alpha: 0.8 });

    // Draw directional pressure indicators (arcs)
    const arcRadius = 45;
    const arcWidth = 4;

    // Left pressure (PI to PI/2, going counter-clockwise from left)
    if (qbState.pressure_left > 0) {
      const alpha = Math.min(qbState.pressure_left, 1);
      ring.arc(qbScreen.x, qbScreen.y, arcRadius, Math.PI * 0.6, Math.PI * 1.4);
      ring.stroke({ color: 0xef4444, width: arcWidth, alpha });
    }

    // Right pressure (0 to -PI/2, right side)
    if (qbState.pressure_right > 0) {
      const alpha = Math.min(qbState.pressure_right, 1);
      ring.arc(qbScreen.x, qbScreen.y, arcRadius, -Math.PI * 0.4, Math.PI * 0.4);
      ring.stroke({ color: 0xef4444, width: arcWidth, alpha });
    }

    // Front pressure (bottom of screen, toward LOS)
    if (qbState.pressure_front > 0) {
      const alpha = Math.min(qbState.pressure_front, 1);
      ring.arc(qbScreen.x, qbScreen.y, arcRadius, Math.PI * 0.1, Math.PI * 0.9);
      ring.stroke({ color: 0xf59e0b, width: arcWidth, alpha });
    }

    // Draw throw timer progress arc (inside ring)
    if (qbState.throw_target_tick > 0) {
      const progress = Math.min(state.tick / qbState.throw_target_tick, 1);
      const timerRadius = 28;
      const endAngle = -Math.PI / 2 + (progress * Math.PI * 2);
      ring.arc(qbScreen.x, qbScreen.y, timerRadius, -Math.PI / 2, endAngle);
      ring.stroke({
        color: progress >= 1 ? 0x3b82f6 : 0x666666,
        width: 2,
        alpha: 0.6
      });
    }
  };

  const updateEngagementLines = () => {
    const engLines = spritesRef.current.engagementLines;
    if (!engLines) return;

    engLines.clear();

    state.engagements.forEach((eng) => {
      // Find blocker(s) and rusher by role
      const blockers = state.blockers.filter(b =>
        eng.blocker_roles.includes(b.role)
      );
      const rusher = state.rushers.find(r => r.role === eng.rusher_role);

      if (blockers.length === 0 || !rusher) return;

      // Skip if shed or pancake
      if (eng.state === 'shed' || eng.state === 'pancake') return;

      // Average blocker position for double teams
      const blockerX = blockers.reduce((sum, b) => sum + b.position.x, 0) / blockers.length;
      const blockerY = blockers.reduce((sum, b) => sum + b.position.y, 0) / blockers.length;
      const blockerScreen = gameToScreen({ x: blockerX, y: blockerY });
      const rusherScreen = gameToScreen(rusher.position);

      let lineColor = COLORS.engaged;
      let lineWidth = 2;
      if (eng.state === 'rusher_winning') {
        lineColor = 0xef4444;
        lineWidth = 3;
      } else if (eng.state === 'blocker_winning') {
        lineColor = 0x22c55e;
        lineWidth = 3;
      }

      engLines.moveTo(blockerScreen.x, blockerScreen.y);
      engLines.lineTo(rusherScreen.x, rusherScreen.y);
      engLines.stroke({ color: lineColor, width: lineWidth, alpha: 0.7 });

      // Draw double team indicator
      if (blockers.length > 1) {
        blockers.forEach(b => {
          const bScreen = gameToScreen(b.position);
          engLines.moveTo(bScreen.x, bScreen.y);
          engLines.lineTo(blockerScreen.x, blockerScreen.y);
          engLines.stroke({ color: 0x3b82f6, width: 1, alpha: 0.5 });
        });
      }
    });
  };

  return (
    <div className="pocket-canvas">
      <div ref={canvasRef} className="canvas-container" />
    </div>
  );
}
