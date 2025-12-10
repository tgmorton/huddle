/**
 * PixiJS Canvas for sandbox blocking simulation visualization
 */

import { useEffect, useRef, useCallback } from 'react';
import { Application, Graphics, Text, TextStyle } from 'pixi.js';
import { useSandboxStore } from '../../stores/sandboxStore';
import type { Position2D } from '../../types/sandbox';

// Canvas dimensions
const CANVAS_WIDTH = 800;
const CANVAS_HEIGHT = 300;

// Field conversion: 1 yard = 80 pixels
const PIXELS_PER_YARD = 80;
const LOS_X = 150; // Line of scrimmage X position
const CENTER_Y = CANVAS_HEIGHT / 2;

// Colors
const COLORS = {
  field: 0x2d5016,  // Green field
  los: 0xffffff,     // White LOS
  qbZone: 0xff000033, // Red QB zone (transparent)
  blocker: 0x3b82f6,  // Blue for OL
  rusher: 0xef4444,   // Red for DT
  engaged: 0xfbbf24,  // Yellow glow when engaged
  text: 0xffffff,
};

interface SandboxCanvasProps {
  qbZoneDepth?: number;
}

export function SandboxCanvas({ qbZoneDepth = 7 }: SandboxCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const blockerRef = useRef<Graphics | null>(null);
  const rusherRef = useRef<Graphics | null>(null);
  const animationFrameRef = useRef<number>(0);

  const {
    currentBlockerPos,
    currentRusherPos,
    targetBlockerPos,
    targetRusherPos,
    updatePositions,
    lastTick,
  } = useSandboxStore();

  // Convert game coordinates to screen coordinates
  const gameToScreen = useCallback((pos: Position2D): { x: number; y: number } => {
    return {
      x: LOS_X + pos.x * PIXELS_PER_YARD,
      y: CENTER_Y + pos.y * PIXELS_PER_YARD,
    };
  }, []);

  // Initialize PixiJS application
  useEffect(() => {
    if (!canvasRef.current) return;

    // Prevent double initialization
    if (appRef.current) {
      return;
    }

    // Clear any existing canvas children (handles StrictMode remount)
    while (canvasRef.current.firstChild) {
      canvasRef.current.removeChild(canvasRef.current.firstChild);
    }

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

      // Draw field markings
      drawField(app);

      // Create player sprites
      createPlayers(app);
    };

    init();

    return () => {
      mounted = false;
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (appRef.current) {
        appRef.current.destroy(true);
        appRef.current = null;
      }
      blockerRef.current = null;
      rusherRef.current = null;
    };
  }, []);

  // Draw field markings
  const drawField = (app: Application) => {
    const fieldGraphics = new Graphics();

    // Draw yard lines
    for (let yard = -3; yard <= 10; yard++) {
      const x = LOS_X + yard * PIXELS_PER_YARD;
      const alpha = yard === 0 ? 1 : 0.3;
      const width = yard === 0 ? 3 : 1;

      fieldGraphics.rect(x - width / 2, 0, width, CANVAS_HEIGHT);
      fieldGraphics.fill({ color: COLORS.los, alpha });
    }

    // Draw QB zone (red shaded area)
    const qbZoneX = LOS_X + qbZoneDepth * PIXELS_PER_YARD;
    fieldGraphics.rect(qbZoneX, 0, CANVAS_WIDTH - qbZoneX, CANVAS_HEIGHT);
    fieldGraphics.fill({ color: 0xff0000, alpha: 0.15 });

    // Add "QB ZONE" label
    const qbZoneText = new Text({
      text: 'QB ZONE',
      style: new TextStyle({
        fontFamily: 'Arial',
        fontSize: 16,
        fill: 0xff6666,
        fontWeight: 'bold',
      }),
    });
    qbZoneText.x = qbZoneX + 10;
    qbZoneText.y = 10;
    app.stage.addChild(qbZoneText);

    // Add LOS label
    const losText = new Text({
      text: 'LOS',
      style: new TextStyle({
        fontFamily: 'Arial',
        fontSize: 14,
        fill: COLORS.text,
      }),
    });
    losText.x = LOS_X - 15;
    losText.y = CANVAS_HEIGHT - 25;
    app.stage.addChild(losText);

    // Add yard markers
    for (let yard = -2; yard <= 8; yard += 2) {
      if (yard === 0) continue;
      const x = LOS_X + yard * PIXELS_PER_YARD;
      const text = new Text({
        text: `${yard > 0 ? '+' : ''}${yard}`,
        style: new TextStyle({
          fontFamily: 'Arial',
          fontSize: 12,
          fill: 0xaaaaaa,
        }),
      });
      text.x = x - 10;
      text.y = CANVAS_HEIGHT - 20;
      app.stage.addChild(text);
    }

    app.stage.addChild(fieldGraphics);
  };

  // Create player sprites
  const createPlayers = (app: Application) => {
    // Blocker (OL) - Blue rectangle
    const blocker = new Graphics();
    drawPlayerSprite(blocker, COLORS.blocker, 'OL');
    const blockerScreen = gameToScreen(currentBlockerPos);
    blocker.x = blockerScreen.x;
    blocker.y = blockerScreen.y;
    app.stage.addChild(blocker);
    blockerRef.current = blocker;

    // Rusher (DT) - Red rectangle
    const rusher = new Graphics();
    drawPlayerSprite(rusher, COLORS.rusher, 'DT');
    const rusherScreen = gameToScreen(currentRusherPos);
    rusher.x = rusherScreen.x;
    rusher.y = rusherScreen.y;
    app.stage.addChild(rusher);
    rusherRef.current = rusher;
  };

  // Draw a player sprite
  const drawPlayerSprite = (graphics: Graphics, color: number, label: string) => {
    const width = 40;
    const height = 50;

    // Body
    graphics.roundRect(-width / 2, -height / 2, width, height, 8);
    graphics.fill({ color });
    graphics.stroke({ color: 0xffffff, width: 2 });

    // Label
    const text = new Text({
      text: label,
      style: new TextStyle({
        fontFamily: 'Arial',
        fontSize: 14,
        fill: COLORS.text,
        fontWeight: 'bold',
      }),
    });
    text.anchor.set(0.5);
    text.y = 0;
    graphics.addChild(text);
  };

  // Animation loop for smooth interpolation
  useEffect(() => {
    const animate = () => {
      // Lerp toward target positions
      const lerpFactor = 0.15; // Smooth interpolation

      const newBlockerPos = {
        x: currentBlockerPos.x + (targetBlockerPos.x - currentBlockerPos.x) * lerpFactor,
        y: currentBlockerPos.y + (targetBlockerPos.y - currentBlockerPos.y) * lerpFactor,
      };

      const newRusherPos = {
        x: currentRusherPos.x + (targetRusherPos.x - currentRusherPos.x) * lerpFactor,
        y: currentRusherPos.y + (targetRusherPos.y - currentRusherPos.y) * lerpFactor,
      };

      // Update store positions
      updatePositions(newBlockerPos, newRusherPos);

      // Update sprite positions
      if (blockerRef.current) {
        const screen = gameToScreen(newBlockerPos);
        blockerRef.current.x = screen.x;
        blockerRef.current.y = screen.y;
      }

      if (rusherRef.current) {
        const screen = gameToScreen(newRusherPos);
        rusherRef.current.x = screen.x;
        rusherRef.current.y = screen.y;
      }

      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [
    currentBlockerPos,
    currentRusherPos,
    targetBlockerPos,
    targetRusherPos,
    updatePositions,
    gameToScreen,
  ]);

  // Update player colors based on matchup state
  useEffect(() => {
    if (!lastTick) return;

    // Could add visual effects here based on state
    // For now, we keep it simple
  }, [lastTick]);

  return (
    <div className="sandbox-canvas">
      <div ref={canvasRef} className="canvas-container" />
      {lastTick && (
        <div className="tick-info">
          <span>Tick: {lastTick.tick_number}</span>
          <span>Depth: {lastTick.rusher_depth.toFixed(2)}yd</span>
          <span>State: {lastTick.matchup_state}</span>
          <span>
            {lastTick.rusher_technique} vs {lastTick.blocker_technique}
          </span>
        </div>
      )}
    </div>
  );
}
