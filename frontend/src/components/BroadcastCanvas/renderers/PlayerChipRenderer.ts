/**
 * PlayerChipRenderer - AWS Next Gen Stats style player chips
 *
 * Features:
 * - Different shapes indicate position group:
 *   - Circle: Skill positions (QB, RB, WR, TE, FB)
 *   - Rounded square: Offensive line (C, G, T)
 *   - Square: Defensive line (DE, DT, NT)
 *   - Diamond: Linebackers (LB, MLB, OLB, ILB)
 *   - Triangle: Defensive backs (CB, S, FS, SS)
 * - Jersey number inside (white text)
 * - Team colors for fill
 * - Ball carrier indicator (orange ring)
 */

import { Graphics, Text, TextStyle, Container } from 'pixi.js';
import type { PlayerFrame, TeamInfo, Vec2 } from '../types';
import {
  COLORS,
  CHIP_RADIUS,
  CHIP_BORDER_WIDTH,
  CHIP_FONT_SIZE,
} from '../constants';

// Position group for shape determination
type PositionGroup = 'skill' | 'ol' | 'dl' | 'lb' | 'db';

function getPositionGroup(player: PlayerFrame): PositionGroup {
  const pos = player.position?.toUpperCase() || '';
  const playerType = player.player_type;

  // Check player_type first
  if (playerType === 'qb' || playerType === 'rb' || playerType === 'fb' || playerType === 'receiver') {
    return 'skill';
  }
  if (playerType === 'ol') return 'ol';
  if (playerType === 'dl') return 'dl';

  // Check position string
  if (['QB', 'RB', 'HB', 'FB', 'WR', 'TE'].includes(pos)) return 'skill';
  if (['C', 'G', 'T', 'LG', 'RG', 'LT', 'RT', 'OL', 'OG', 'OT'].includes(pos)) return 'ol';
  if (['DE', 'DT', 'NT', 'DL', 'LE', 'RE'].includes(pos)) return 'dl';
  if (['LB', 'MLB', 'ILB', 'OLB', 'LOLB', 'ROLB', 'LILB', 'RILB', 'WLB', 'SLB'].includes(pos)) return 'lb';
  if (['CB', 'S', 'FS', 'SS', 'DB', 'CB1', 'CB2', 'NCB'].includes(pos)) return 'db';

  // Default based on team
  if (player.team === 'offense') return 'skill';
  return 'db'; // Default for unknown defense
}

export interface PlayerChipConfig {
  scale: number;
  homeTeam: TeamInfo;
  awayTeam: TeamInfo;
  userControlsHome: boolean;
  possessionHome?: boolean;  // Which team has the ball (true = home is offense)
  tiltAmount?: number;  // Tilt angle in degrees for shadow offset (0-30)
}

function parseColor(color: string | undefined): number {
  if (!color) return 0x888888;
  if (color.startsWith('#')) {
    return parseInt(color.slice(1), 16);
  }
  if (color.startsWith('0x')) {
    return parseInt(color, 16);
  }
  // Try to parse as hex
  const parsed = parseInt(color, 16);
  return isNaN(parsed) ? 0x888888 : parsed;
}

export function drawPlayerChip(
  container: Container,
  player: PlayerFrame,
  screenPos: Vec2,
  config: PlayerChipConfig,
): void {
  const g = new Graphics();
  // Scale chips proportionally but ensure minimum visibility
  // At scale 16 (field view), chips should be ~12px radius (visible but not huge)
  const scaleFactor = Math.max(config.scale / 8, 1.0);
  const size = CHIP_RADIUS * scaleFactor;

  // Determine team color based on possession
  const isOffense = player.team === 'offense';
  const homeOnOffense = config.possessionHome ?? config.userControlsHome;

  let teamInfo: TeamInfo;
  if (isOffense) {
    teamInfo = homeOnOffense ? config.homeTeam : config.awayTeam;
  } else {
    teamInfo = homeOnOffense ? config.awayTeam : config.homeTeam;
  }

  let chipColor: number;
  if (teamInfo?.primaryColor) {
    chipColor = parseColor(teamInfo.primaryColor);
  } else {
    chipColor = isOffense ? COLORS.offenseChip : COLORS.defenseChip;
  }

  // Get position group for shape
  const posGroup = getPositionGroup(player);

  // Get secondary color for shadow platform
  let shadowColor: number;
  if (teamInfo?.secondaryColor) {
    shadowColor = parseColor(teamInfo.secondaryColor);
  } else {
    // Darken primary color for shadow
    shadowColor = chipColor & 0x7f7f7f; // Simple darken
  }

  // Draw shadow platform matching player shape (adds depth for tilt effect)
  const tilt = config.tiltAmount ?? 0;
  if (tilt > 0) {
    const shadowG = new Graphics();
    // Shadow offset based on tilt (more tilt = more offset)
    const shadowOffsetY = (tilt / 20) * size * 0.8;
    // Shadow is flattened to show perspective
    const shadowScaleY = 0.4 + (tilt / 40);
    const shadowX = screenPos.x;
    const shadowY = screenPos.y + shadowOffsetY;
    const shadowSize = size * 1.1;

    // Draw shadow matching position group shape
    switch (posGroup) {
      case 'skill':
        // Ellipse for skill positions
        shadowG.ellipse(shadowX, shadowY, shadowSize, shadowSize * shadowScaleY);
        break;

      case 'ol':
        // Rounded rectangle for offensive line
        shadowG.roundRect(
          shadowX - shadowSize,
          shadowY - shadowSize * shadowScaleY,
          shadowSize * 2,
          shadowSize * 2 * shadowScaleY,
          shadowSize * 0.3
        );
        break;

      case 'dl':
        // Rectangle for defensive line
        shadowG.rect(
          shadowX - shadowSize,
          shadowY - shadowSize * shadowScaleY,
          shadowSize * 2,
          shadowSize * 2 * shadowScaleY
        );
        break;

      case 'lb':
        // Diamond for linebackers (flattened)
        shadowG.moveTo(shadowX, shadowY - shadowSize * shadowScaleY);
        shadowG.lineTo(shadowX + shadowSize, shadowY);
        shadowG.lineTo(shadowX, shadowY + shadowSize * shadowScaleY);
        shadowG.lineTo(shadowX - shadowSize, shadowY);
        shadowG.closePath();
        break;

      case 'db':
        // Triangle for defensive backs (flattened)
        shadowG.moveTo(shadowX - shadowSize, shadowY - shadowSize * 0.5 * shadowScaleY);
        shadowG.lineTo(shadowX + shadowSize, shadowY - shadowSize * 0.5 * shadowScaleY);
        shadowG.lineTo(shadowX, shadowY + shadowSize * shadowScaleY);
        shadowG.closePath();
        break;
    }

    shadowG.fill({ color: shadowColor, alpha: 0.5 });
    container.addChild(shadowG);
  }

  // Draw shape based on position group
  switch (posGroup) {
    case 'skill':
      // Circle for skill positions (QB, RB, WR, TE, FB)
      g.circle(screenPos.x, screenPos.y, size);
      break;

    case 'ol':
      // Rounded square for offensive line
      g.roundRect(
        screenPos.x - size,
        screenPos.y - size,
        size * 2,
        size * 2,
        size * 0.3
      );
      break;

    case 'dl':
      // Square for defensive line
      g.rect(
        screenPos.x - size,
        screenPos.y - size,
        size * 2,
        size * 2
      );
      break;

    case 'lb':
      // Diamond for linebackers (rotated square)
      g.moveTo(screenPos.x, screenPos.y - size * 1.1);
      g.lineTo(screenPos.x + size * 1.1, screenPos.y);
      g.lineTo(screenPos.x, screenPos.y + size * 1.1);
      g.lineTo(screenPos.x - size * 1.1, screenPos.y);
      g.closePath();
      break;

    case 'db':
      // Triangle for defensive backs (pointing down)
      g.moveTo(screenPos.x - size, screenPos.y - size * 0.7);
      g.lineTo(screenPos.x + size, screenPos.y - size * 0.7);
      g.lineTo(screenPos.x, screenPos.y + size);
      g.closePath();
      break;
  }

  g.fill({ color: chipColor });
  g.stroke({ color: 0xffffff, width: CHIP_BORDER_WIDTH });

  container.addChild(g);

  // Jersey number text - always show
  const jerseyNumber = extractJerseyNumber(player);
  const text = new Text({
    text: jerseyNumber,
    style: new TextStyle({
      fontSize: CHIP_FONT_SIZE * scaleFactor,
      fill: COLORS.chipText,
      fontWeight: 'bold',
      fontFamily: 'Arial, sans-serif',
    }),
  });
  text.anchor.set(0.5);
  text.x = screenPos.x;
  // Adjust text position slightly for triangle shape
  text.y = posGroup === 'db' ? screenPos.y - size * 0.1 : screenPos.y;
  container.addChild(text);
}

export function drawAllPlayers(
  container: Container,
  players: PlayerFrame[],
  yardToScreen: (x: number, y: number) => Vec2,
  config: PlayerChipConfig,
): void {
  container.removeChildren();

  // Sort players so ball carrier is drawn last (on top)
  const sortedPlayers = [...players].sort((a, b) => {
    if (a.has_ball || a.is_ball_carrier) return 1;
    if (b.has_ball || b.is_ball_carrier) return -1;
    return 0;
  });

  for (const player of sortedPlayers) {
    const screenPos = yardToScreen(player.x, player.y);
    drawPlayerChip(container, player, screenPos, config);
  }
}

function extractJerseyNumber(player: PlayerFrame): string {
  // Check for jersey_number field first (if backend provides it)
  const playerAny = player as PlayerFrame & { jersey_number?: number | string };
  if (playerAny.jersey_number !== undefined) {
    return String(playerAny.jersey_number);
  }

  // Try to extract jersey number from name (e.g., "Smith #12" or "J.Smith 12")
  const nameMatch = player.name.match(/#?(\d{1,2})$/);
  if (nameMatch) {
    return nameMatch[1];
  }

  // Try to extract any number from ID
  const idMatch = player.id.match(/(\d{1,2})/);
  if (idMatch) {
    return idMatch[1];
  }

  // Generate a consistent number based on position and player hash
  // This ensures the same player always gets the same number
  const hash = simpleHash(player.id + player.name);
  const posGroup = getPositionGroup(player);

  // NFL jersey number ranges by position
  switch (posGroup) {
    case 'skill': {
      const pos = player.position?.toUpperCase() || '';
      if (pos === 'QB') return String(1 + (hash % 19)); // 1-19
      if (pos === 'RB' || pos === 'FB' || pos === 'HB') return String(20 + (hash % 30)); // 20-49
      if (pos === 'WR') return String(10 + (hash % 10)); // 10-19 or 80-89
      if (pos === 'TE') return String(80 + (hash % 10)); // 80-89
      return String(1 + (hash % 49)); // 1-49
    }
    case 'ol':
      return String(50 + (hash % 29)); // 50-78
    case 'dl':
      return String(50 + (hash % 29)); // 50-78 or 90-99
    case 'lb':
      return String(40 + (hash % 20)); // 40-59 or 90-99
    case 'db':
      return String(20 + (hash % 30)); // 20-49
    default:
      return String(hash % 99 + 1);
  }
}

// Simple hash function for consistent number generation
function simpleHash(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash);
}
