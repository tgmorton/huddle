/**
 * RouteTraceRenderer - Light blue route traces for receivers
 *
 * Features:
 * - Draws path history as curved line
 * - Light blue color
 * - Fog of war: only show user team's routes
 * - Break points highlighted
 */

import { Graphics, Container } from 'pixi.js';
import type { PlayerFrame, WaypointFrame, Vec2 } from '../types';
import {
  COLORS,
  ROUTE_LINE_WIDTH,
  MAX_TRAIL_LENGTH,
  TRAIL_OPACITY_START,
  TRAIL_OPACITY_END,
} from '../constants';

export interface RouteTraceConfig {
  scale: number;
  showOffenseRoutes: boolean;
  showDefenseCoverage: boolean;
}

// Store position history for each player
const positionHistory: Map<string, Vec2[]> = new Map();

// Store starting positions for each player (for waypoint offset)
// Waypoints are typically defined relative to receiver's starting position
const startingPositions: Map<string, Vec2> = new Map();

export function updatePositionHistory(players: PlayerFrame[]): void {
  for (const player of players) {
    let history = positionHistory.get(player.id);
    if (!history) {
      history = [];
      positionHistory.set(player.id, history);
      // Capture starting position on first update
      startingPositions.set(player.id, { x: player.x, y: player.y });
    }

    // Add current position
    history.push({ x: player.x, y: player.y });

    // Limit history length
    if (history.length > MAX_TRAIL_LENGTH) {
      history.shift();
    }
  }
}

export function clearPositionHistory(): void {
  positionHistory.clear();
  startingPositions.clear();
}

export function getStartingPosition(playerId: string): Vec2 | undefined {
  return startingPositions.get(playerId);
}

export function drawRouteTraces(
  container: Container,
  players: PlayerFrame[],
  yardToScreen: (x: number, y: number) => Vec2,
  config: RouteTraceConfig,
): void {
  container.removeChildren();

  const g = new Graphics();

  for (const player of players) {
    // Fog of war check
    const isOffense = player.team === 'offense';
    if (isOffense && !config.showOffenseRoutes) continue;
    if (!isOffense && !config.showDefenseCoverage) continue;

    // Only draw routes for players with actual route assignments (not ball carriers on run plays)
    if (isOffense) {
      // Skip if not a route-running position or no route assigned
      if (!['receiver'].includes(player.player_type)) continue;
      // Also skip if player is the ball carrier
      if (player.has_ball || player.is_ball_carrier) continue;
    }

    const history = positionHistory.get(player.id);
    if (!history || history.length < 2) continue;

    // Draw route trace
    const color = isOffense ? COLORS.routeTrace : COLORS.coverageLine;

    for (let i = 1; i < history.length; i++) {
      const from = yardToScreen(history[i - 1].x, history[i - 1].y);
      const to = yardToScreen(history[i].x, history[i].y);

      // Fade older positions
      const alpha = TRAIL_OPACITY_START - (TRAIL_OPACITY_START - TRAIL_OPACITY_END) * ((history.length - i) / history.length);

      g.moveTo(from.x, from.y);
      g.lineTo(to.x, to.y);
      g.stroke({
        color,
        width: ROUTE_LINE_WIDTH * (config.scale / 12),
        alpha,
      });
    }
  }

  container.addChild(g);
}

export function drawWaypoints(
  container: Container,
  waypoints: WaypointFrame[],
  currentWaypoint: number,
  yardToScreen: (x: number, y: number) => Vec2,
  config: RouteTraceConfig,
  playerId?: string,
): void {
  if (!config.showOffenseRoutes || waypoints.length === 0) return;

  // Get the player's starting position to offset waypoints
  // Waypoints are typically defined relative to where the receiver lines up
  const startPos = playerId ? startingPositions.get(playerId) : undefined;
  const offsetX = startPos?.x ?? 0;
  const offsetY = startPos?.y ?? 0;

  const g = new Graphics();
  const scaleFactor = config.scale / 12;

  // Draw waypoint path
  for (let i = 0; i < waypoints.length - 1; i++) {
    // Apply offset to convert from route-relative to field coordinates
    const from = yardToScreen(waypoints[i].x + offsetX, waypoints[i].y + offsetY);
    const to = yardToScreen(waypoints[i + 1].x + offsetX, waypoints[i + 1].y + offsetY);

    const isCompleted = i < currentWaypoint;
    const alpha = isCompleted ? 0.3 : 0.7;
    const color = waypoints[i + 1].is_break ? COLORS.routeBreak : COLORS.routeTrace;

    g.moveTo(from.x, from.y);
    g.lineTo(to.x, to.y);
    g.stroke({
      color,
      width: 2 * scaleFactor,
      alpha,
    });
  }

  // Draw waypoint markers
  for (let i = 0; i < waypoints.length; i++) {
    const wp = waypoints[i];
    // Apply offset to convert from route-relative to field coordinates
    const screen = yardToScreen(wp.x + offsetX, wp.y + offsetY);

    const isCurrent = i === currentWaypoint;
    const isBreak = wp.is_break;
    const isCompleted = i < currentWaypoint;

    const radius = isCurrent ? 5 : (isBreak ? 4 : 3);
    const color = isBreak ? COLORS.routeBreak : COLORS.routeTrace;
    const alpha = isCompleted ? 0.3 : (isCurrent ? 1 : 0.6);

    g.circle(screen.x, screen.y, radius * scaleFactor);
    g.fill({ color, alpha });

    if (isCurrent) {
      g.circle(screen.x, screen.y, (radius + 2) * scaleFactor);
      g.stroke({ color: 0xffffff, width: 1, alpha: 0.8 });
    }
  }

  container.addChild(g);
}

export function drawCoverageLines(
  container: Container,
  players: PlayerFrame[],
  yardToScreen: (x: number, y: number) => Vec2,
  config: RouteTraceConfig,
): void {
  if (!config.showDefenseCoverage) return;

  const g = new Graphics();

  // Find defenders with man assignments
  const defenders = players.filter(
    p => p.team === 'defense' && p.coverage_type === 'man' && p.man_target_id
  );

  for (const defender of defenders) {
    const receiver = players.find(p => p.id === defender.man_target_id);
    if (!receiver) continue;

    const defScreen = yardToScreen(defender.x, defender.y);
    const rcvScreen = yardToScreen(receiver.x, receiver.y);

    // Dashed line from defender to receiver
    g.moveTo(defScreen.x, defScreen.y);
    g.lineTo(rcvScreen.x, rcvScreen.y);
    g.stroke({
      color: COLORS.coverageLine,
      width: 1 * (config.scale / 12),
      alpha: 0.4,
    });
  }

  container.addChild(g);
}
