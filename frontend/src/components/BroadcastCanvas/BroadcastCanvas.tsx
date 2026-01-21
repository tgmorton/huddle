/**
 * BroadcastCanvas - AWS Next Gen Stats style play visualization
 *
 * A PixiJS canvas that renders plays with:
 * - Player chips with jersey numbers
 * - Blue LOS / Yellow first down lines
 * - Route traces with fog of war
 * - Brown football oval
 * - Field view (zoomed out) or Game view (zoomed in, tilted)
 */

import { useEffect, useRef, useCallback, useState, useLayoutEffect } from 'react';
import { Application, Container } from 'pixi.js';

import type { BroadcastCanvasProps, PlayFrame, Vec2 } from './types';
import {
  COLORS,
  FIELD_WIDTH_YARDS,
  DEFAULT_WIDTH,
  DEFAULT_HEIGHT,
  GAME_VIEW_CONFIG,
  FIELD_PADDING,
} from './constants';
import {
  drawField,
  drawAllPlayers,
  drawBall,
  shouldShowBall,
  clearBallHistory,
  drawRouteTraces,
  drawWaypoints,
  drawCoverageLines,
  updatePositionHistory,
  clearPositionHistory,
} from './renderers';
import { usePlaybackState } from './hooks/usePlaybackState';

import './BroadcastCanvas.css';

export function BroadcastCanvas({
  frames,
  currentTick,
  isPlaying,
  viewMode,
  homeTeam,
  awayTeam,
  userControlsHome,
  possessionHome,
  fieldPosition,
  showOffenseRoutes,
  showDefenseCoverage,
  onTickChange,
  onComplete,
  width: propWidth,
  height: propHeight,
  zoomLevel = 1,
}: BroadcastCanvasProps) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);

  // World container - holds everything that moves with the camera
  const worldContainerRef = useRef<Container | null>(null);

  // Layer containers (children of world container)
  const fieldContainerRef = useRef<Container | null>(null);
  const routesContainerRef = useRef<Container | null>(null);
  const playersContainerRef = useRef<Container | null>(null);
  const ballContainerRef = useRef<Container | null>(null);

  // Track when PixiJS is initialized
  const [pixiReady, setPixiReady] = useState(false);

  // Camera Y position in yards (which yard line is centered on screen)
  // This controls where the world container is positioned
  const [cameraYardLine, setCameraYardLine] = useState(fieldPosition?.yardLine ?? 25);
  const targetCameraYardRef = useRef(fieldPosition?.yardLine ?? 25);

  // Current field position for LOS/first down line placement
  const currentLosYardLine = fieldPosition?.yardLine ?? 25;
  const currentFirstDownYardLine = Math.min(currentLosYardLine + (fieldPosition?.yardsToGo ?? 10), 100);

  // Field transition state - hide players during field movement
  const [, setIsFieldTransitioning] = useState(false);
  const [playersVisible, setPlayersVisible] = useState(true);

  // Dynamic size based on container
  const [containerSize, setContainerSize] = useState({ width: propWidth || DEFAULT_WIDTH, height: propHeight || DEFAULT_HEIGHT });

  // Measure container size
  useLayoutEffect(() => {
    if (!wrapperRef.current) return;

    const updateSize = () => {
      if (wrapperRef.current) {
        const rect = wrapperRef.current.getBoundingClientRect();
        setContainerSize({
          width: Math.floor(rect.width) || DEFAULT_WIDTH,
          height: Math.floor(rect.height) || DEFAULT_HEIGHT,
        });
      }
    };

    updateSize();

    // Observe resize
    const resizeObserver = new ResizeObserver(updateSize);
    resizeObserver.observe(wrapperRef.current);

    return () => resizeObserver.disconnect();
  }, []);

  // Canvas dimensions - fill container
  const canvasWidth = containerSize.width;
  const canvasHeight = containerSize.height;

  // Calculate scale based on view mode and zoom level
  // Field view: scale to fit full field width (sideline to sideline) within canvas
  // Game view: use fixed scale for zoomed-in view
  const baseScale = viewMode === 'field'
    ? (canvasWidth - FIELD_PADDING * 2) / FIELD_WIDTH_YARDS  // Fit full width
    : GAME_VIEW_CONFIG.scale;
  const scale = baseScale * zoomLevel;

  // Screen anchor point - where the camera's target yard line appears on screen
  // Positioned slightly above center so there's more view downfield
  const screenAnchorY = canvasHeight * 0.55;

  // Convert yard coordinates to WORLD coordinates (pixels in the world container)
  // World Y: 0 yards = bottom of world, 100 yards = top of world
  // Higher yard line = higher on field = lower Y in world (because screen Y increases downward)
  // X: 0 = center, positive = right
  const yardToWorld = useCallback((x: number, y: number): Vec2 => {
    return {
      x: canvasWidth / 2 + x * scale,
      y: -y * scale,  // Negative because higher yards = up on screen = negative Y
    };
  }, [canvasWidth, scale]);

  // Convert player coordinates to world coordinates
  // Player positions are relative to LOS (y=0 at LOS, positive = downfield)
  // We need to convert to absolute yard lines for world positioning
  const yardToScreen = useCallback((x: number, y: number): Vec2 => {
    const absoluteYardLine = currentLosYardLine + y;
    return yardToWorld(x, absoluteYardLine);
  }, [yardToWorld, currentLosYardLine]);

  // Playback state management
  usePlaybackState({
    frames,
    currentTick,
    isPlaying,
    playbackSpeed: 1,
    onTickChange,
    onComplete,
  });

  // Initialize PixiJS application (once)
  useEffect(() => {
    if (!containerRef.current || appRef.current) return;

    let mounted = true;

    const init = async () => {
      const app = new Application();
      await app.init({
        width: canvasWidth,
        height: canvasHeight,
        backgroundColor: COLORS.fieldGreen,
        antialias: true,
        resolution: Math.min(window.devicePixelRatio || 1, 2),
        autoDensity: true,
      });

      if (!mounted || !containerRef.current) {
        app.destroy(true);
        return;
      }

      containerRef.current.appendChild(app.canvas);
      appRef.current = app;

      // Create world container - this moves to implement camera
      // All game elements are children of this container
      const worldContainer = new Container();
      app.stage.addChild(worldContainer);
      worldContainerRef.current = worldContainer;

      // Create layer containers as children of world (back to front)
      const fieldContainer = new Container();
      worldContainer.addChild(fieldContainer);
      fieldContainerRef.current = fieldContainer;

      const routesContainer = new Container();
      worldContainer.addChild(routesContainer);
      routesContainerRef.current = routesContainer;

      const playersContainer = new Container();
      worldContainer.addChild(playersContainer);
      playersContainerRef.current = playersContainer;

      const ballContainer = new Container();
      worldContainer.addChild(ballContainer);
      ballContainerRef.current = ballContainer;

      // Signal that PixiJS is ready - this triggers field drawing
      setPixiReady(true);
    };

    init();

    return () => {
      mounted = false;
      if (appRef.current) {
        appRef.current.destroy(true);
        appRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Initialize only once

  // Handle canvas resize and draw field
  useEffect(() => {
    if (!pixiReady || !appRef.current || !fieldContainerRef.current) return;

    // Resize the renderer
    appRef.current.renderer.resize(canvasWidth, canvasHeight);

    // Determine which team is offense/defense based on possession
    const homeOnOffense = possessionHome ?? userControlsHome;
    const offenseTeam = homeOnOffense ? homeTeam : awayTeam;
    const defenseTeam = homeOnOffense ? awayTeam : homeTeam;

    // Draw the ENTIRE field in world coordinates
    // Field elements are positioned at their actual yard lines (0-100)
    // The world container's position handles the camera
    drawField(fieldContainerRef.current, {
      scale,
      canvasWidth,
      canvasHeight,
      // LOS position in world coordinates (actual yard line)
      losYardLine: currentLosYardLine,
      firstDownYardLine: currentFirstDownYardLine,
      homeTeam: homeTeam.abbr,
      awayTeam: awayTeam.abbr,
      homeTeamInfo: offenseTeam,
      awayTeamInfo: defenseTeam,
      fieldPosition,
      yardToWorld,  // Pass the coordinate converter
    });
  }, [pixiReady, canvasWidth, canvasHeight, scale, currentLosYardLine, currentFirstDownYardLine, homeTeam, awayTeam, fieldPosition, possessionHome, userControlsHome, yardToWorld]);

  // Update camera position (world container Y) based on cameraYardLine
  useEffect(() => {
    if (!worldContainerRef.current) return;

    // Position the world container so cameraYardLine appears at screenAnchorY
    // World Y for a yard line = -yardLine * scale (from yardToWorld)
    // We want that to appear at screenAnchorY on screen
    // So: worldContainer.y + worldY = screenAnchorY
    // worldContainer.y = screenAnchorY - worldY = screenAnchorY - (-yardLine * scale) = screenAnchorY + yardLine * scale
    worldContainerRef.current.y = screenAnchorY + cameraYardLine * scale;
  }, [cameraYardLine, scale, screenAnchorY]);

  // Render current frame
  const renderFrame = useCallback((frame: PlayFrame) => {
    if (!playersContainerRef.current || !routesContainerRef.current || !ballContainerRef.current) {
      return;
    }

    // Clear containers first
    routesContainerRef.current.removeChildren();
    playersContainerRef.current.removeChildren();
    ballContainerRef.current.removeChildren();

    // Don't draw players/routes during field transition
    if (!playersVisible) {
      return;
    }

    // Update position history for trails
    updatePositionHistory(frame.players);

    // Draw route traces (fog of war)
    drawRouteTraces(routesContainerRef.current, frame.players, yardToScreen, {
      scale,
      showOffenseRoutes,
      showDefenseCoverage,
    });

    // Draw waypoints for receivers with route info
    // Pass player ID so waypoints can be offset by their starting position
    frame.players.forEach(player => {
      if (player.route_name && frame.waypoints[player.id]) {
        drawWaypoints(
          routesContainerRef.current!,
          frame.waypoints[player.id],
          player.current_waypoint || 0,
          yardToScreen,
          { scale, showOffenseRoutes, showDefenseCoverage },
          player.id,  // For waypoint offset calculation
        );
      }
    });

    // Draw coverage lines
    drawCoverageLines(routesContainerRef.current, frame.players, yardToScreen, {
      scale,
      showOffenseRoutes,
      showDefenseCoverage,
    });

    // Draw players with shadow platforms for tilt effect
    const tiltAmount = viewMode === 'game' ? 20 : 0;
    drawAllPlayers(playersContainerRef.current, frame.players, yardToScreen, {
      scale,
      homeTeam,
      awayTeam,
      userControlsHome,
      possessionHome,
      tiltAmount,
    });

    // Draw ball - find carrier info if ball is held
    const showBall = shouldShowBall(frame.ball, viewMode);
    const ballScreen = yardToScreen(frame.ball.x, frame.ball.y);

    // Find ball carrier for held ball positioning
    let carrierInfo: { screenPos: { x: number; y: number }; facingX?: number; facingY?: number; vx?: number; vy?: number } | undefined;
    if (frame.ball.state === 'held' && frame.ball.carrier_id) {
      const carrier = frame.players.find(p => p.id === frame.ball.carrier_id || p.has_ball || p.is_ball_carrier);
      if (carrier) {
        const carrierScreen = yardToScreen(carrier.x, carrier.y);
        carrierInfo = {
          screenPos: carrierScreen,
          facingX: carrier.facing_x,
          facingY: carrier.facing_y,
          vx: carrier.vx,
          vy: carrier.vy,
        };
      }
    }

    // Always try to draw ball (handles held state internally)
    if (showBall || frame.ball.state === 'held') {
      drawBall(ballContainerRef.current, frame.ball, ballScreen, {
        scale,
        showBall: showBall,
      }, carrierInfo);
    }
  }, [yardToScreen, scale, viewMode, showOffenseRoutes, showDefenseCoverage, homeTeam, awayTeam, userControlsHome, playersVisible]);

  // Render when tick changes or players visibility changes
  useEffect(() => {
    if (frames.length === 0) return;

    const frameIndex = Math.min(currentTick, frames.length - 1);
    const frame = frames[frameIndex];

    if (frame) {
      renderFrame(frame);
    }
  }, [currentTick, frames, renderFrame, playersVisible]);

  // Clear position history and reset camera when frames change (new play)
  useEffect(() => {
    clearPositionHistory();
    clearBallHistory();
    // Reset camera to center on LOS at start of new play
    setCameraYardLine(currentLosYardLine);
    targetCameraYardRef.current = currentLosYardLine;
  }, [frames, currentLosYardLine]);

  // Smooth camera following during play
  useEffect(() => {
    if (frames.length === 0 || !isPlaying) return;

    const frameIndex = Math.min(currentTick, frames.length - 1);
    const frame = frames[frameIndex];
    if (!frame) return;

    // Find the ball carrier or ball position
    // Player Y is relative to LOS (0 = at LOS, positive = downfield)
    const ballCarrier = frame.players.find(p => p.has_ball || p.is_ball_carrier);
    const playerYardsBeyondLos = ballCarrier?.y ?? frame.ball.y;

    // Only follow if ball has moved significantly downfield
    if (playerYardsBeyondLos > 3) {
      // Camera leads slightly ahead of ball carrier for better visibility
      targetCameraYardRef.current = currentLosYardLine + playerYardsBeyondLos * 0.6;
    }

    // Smooth interpolation toward target
    const lerp = 0.08; // Lower = smoother but slower
    setCameraYardLine(prev => {
      const diff = targetCameraYardRef.current - prev;
      if (Math.abs(diff) < 0.1) return targetCameraYardRef.current;
      return prev + diff * lerp;
    });
  }, [currentTick, frames, isPlaying, currentLosYardLine]);

  // Smooth camera transition between plays (when LOS changes)
  useEffect(() => {
    const targetYard = fieldPosition?.yardLine ?? 25;
    const currentCamera = targetCameraYardRef.current;

    // If position changed significantly, start transition
    const positionChange = Math.abs(targetYard - currentCamera);
    if (positionChange > 2) {
      // Hide players during field transition
      setPlayersVisible(false);
      setIsFieldTransitioning(true);
    }

    // Update target
    targetCameraYardRef.current = targetYard;

    let settled = false;

    // Animate camera toward new target yard line
    const animate = () => {
      setCameraYardLine(prev => {
        const diff = targetCameraYardRef.current - prev;
        if (Math.abs(diff) < 0.5) {
          // Camera has settled
          if (!settled) {
            settled = true;
            // Wait a moment, then show players
            setTimeout(() => {
              setIsFieldTransitioning(false);
              setPlayersVisible(true);
            }, 300); // 300ms delay before showing players
          }
          return targetCameraYardRef.current;
        }
        // Ease toward target (faster when far, slower when close)
        const speed = Math.max(0.3, Math.abs(diff) * 0.12);
        return prev + Math.sign(diff) * speed;
      });
    };

    // Run animation frames
    const interval = setInterval(animate, 16); // ~60fps
    return () => clearInterval(interval);
  }, [fieldPosition?.yardLine]);

  // Apply tilt effect for game view using CSS transform on the canvas
  // Higher tilt gives more broadcast-style 3D feel
  const canvasStyle: React.CSSProperties = viewMode === 'game' ? {
    width: canvasWidth,
    height: canvasHeight,
    transform: 'perspective(800px) rotateX(20deg)',
    transformOrigin: 'center center',
  } : {
    width: canvasWidth,
    height: canvasHeight,
  };

  return (
    <div
      ref={wrapperRef}
      className={`broadcast-canvas broadcast-canvas--${viewMode}`}
    >
      <div
        ref={containerRef}
        className="broadcast-canvas__pixi"
        style={canvasStyle}
      />
    </div>
  );
}

export default BroadcastCanvas;
