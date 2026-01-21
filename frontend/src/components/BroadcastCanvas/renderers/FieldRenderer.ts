/**
 * FieldRenderer - Draws the football field with AWS Next Gen Stats style
 *
 * Features:
 * - Grass stripes (alternating colors)
 * - Yard lines every 5 yards with accurate field numbers
 * - Hash marks
 * - End zones with team name
 * - Midfield logo
 * - Blue LOS line
 * - Yellow first down marker
 */

import { Graphics, Text, TextStyle, Container, Sprite, Texture, Assets } from 'pixi.js';
import {
  COLORS,
  FIELD_WIDTH_YARDS,
  YARD_LINE_WIDTH,
  LOS_LINE_WIDTH,
  FIRST_DOWN_LINE_WIDTH,
  HASH_MARK_WIDTH,
  HASH_OFFSET_YARDS,
  END_ZONE_DEPTH,
} from '../constants';
import type { FieldPosition, TeamInfo } from '../types';

export interface Vec2 {
  x: number;
  y: number;
}

export interface FieldConfig {
  scale: number;
  canvasWidth: number;
  canvasHeight: number;
  // Yard line positions (0-100)
  losYardLine: number;        // Line of scrimmage yard line
  firstDownYardLine: number;  // First down marker yard line
  // Coordinate converter: yard position -> world pixel position
  yardToWorld: (x: number, y: number) => Vec2;
  // Team info
  homeTeam?: string;
  awayTeam?: string;
  homeTeamInfo?: TeamInfo;
  awayTeamInfo?: TeamInfo;
  homeLogo?: string;
  showEndZones?: boolean;
  fieldPosition?: FieldPosition;
}

/**
 * Convert actual field yard line (0-100) to display number (50-0-50)
 * 0 = own goal line, 50 = midfield, 100 = opponent goal line
 */
function getDisplayYardNumber(actualYardLine: number): number {
  if (actualYardLine <= 50) {
    return actualYardLine;
  } else {
    return 100 - actualYardLine;
  }
}

/**
 * Parse a hex color string to a number
 */
function parseColor(color: string | undefined): number {
  if (!color) return 0x888888;
  if (color.startsWith('#')) {
    return parseInt(color.slice(1), 16);
  }
  return parseInt(color, 16) || 0x888888;
}

// Cache for loaded logo textures
const logoCache = new Map<string, Texture>();


/**
 * Load and display team logo at midfield
 */
async function loadMidfieldLogo(
  container: Container,
  logoFileName: string,
  x: number,
  y: number,
  scale: number
): Promise<void> {
  const logoUrl = `/logos/${logoFileName}`;

  try {
    let texture = logoCache.get(logoUrl);

    if (!texture) {
      texture = await Assets.load(logoUrl);
      if (!texture) return;  // Failed to load
      logoCache.set(logoUrl, texture);
    }

    // Check if container is still valid (might have been cleared)
    if (!container.parent) return;

    const sprite = new Sprite(texture);
    sprite.anchor.set(0.5);
    sprite.x = x;
    sprite.y = y;

    // Rotate 90 degrees so logo faces sideline (like real NFL fields)
    sprite.rotation = Math.PI / 2;

    // Scale logo to fit nicely (max 10 yards wide)
    const targetSize = 10 * scale;
    const logoScale = targetSize / Math.max(sprite.width, sprite.height);
    sprite.scale.set(logoScale);
    sprite.alpha = 0.35;  // Semi-transparent so it doesn't distract

    container.addChild(sprite);
  } catch (error) {
    // Logo failed to load, silently ignore
    console.debug('Failed to load team logo:', logoUrl);
  }
}

export function drawField(container: Container, config: FieldConfig): void {
  const {
    scale,
    canvasWidth,
    losYardLine,
    firstDownYardLine,
    yardToWorld,
    homeTeamInfo,
    awayTeamInfo,
  } = config;

  container.removeChildren();

  const g = new Graphics();
  const fieldWidthPx = FIELD_WIDTH_YARDS * scale;
  const fieldLeft = (canvasWidth - fieldWidthPx) / 2;
  const fieldRight = fieldLeft + fieldWidthPx;

  // Draw the ENTIRE field in world coordinates (yards 0-100)
  // All positions use yardToWorld() to convert yard positions to world pixels

  // Draw grass stripes at 5-yard intervals (traditional field look)
  for (let yardLine = -10; yardLine <= 110; yardLine += 5) {
    const topPos = yardToWorld(0, yardLine + 5);
    const bottomPos = yardToWorld(0, yardLine);

    // Base color alternates every 5 yards
    const fiveYardSection = Math.floor(yardLine / 5);
    const baseColor = fiveYardSection % 2 === 0 ? COLORS.fieldGreen : COLORS.fieldGreenDark;

    g.rect(fieldLeft, topPos.y, fieldWidthPx, bottomPos.y - topPos.y);
    g.fill({ color: baseColor });
  }

  // Hash mark position constants (used later for hash marks too)
  const hashLeftX = canvasWidth / 2 - HASH_OFFSET_YARDS * scale;
  const hashRightX = canvasWidth / 2 + HASH_OFFSET_YARDS * scale;

  // Out of bounds areas (darker green) - extend beyond the field
  const topOfField = yardToWorld(0, 110);  // Above opponent end zone
  const bottomOfField = yardToWorld(0, -10);  // Below own end zone
  g.rect(0, topOfField.y, fieldLeft, bottomOfField.y - topOfField.y);
  g.fill({ color: 0x1a3a1a });
  g.rect(fieldRight, topOfField.y, canvasWidth - fieldRight, bottomOfField.y - topOfField.y);
  g.fill({ color: 0x1a3a1a });

  container.addChild(g);

  // Draw end zones
  const endZoneDepth = END_ZONE_DEPTH * scale;

  // Own end zone (yard line 0 to -10)
  const ownEndZoneTop = yardToWorld(0, 0);
  const endZoneG = new Graphics();
  const offenseTeam = homeTeamInfo;
  const ownEndZoneColor = offenseTeam?.primaryColor ? parseColor(offenseTeam.primaryColor) : COLORS.endZone;
  endZoneG.rect(fieldLeft, ownEndZoneTop.y, fieldWidthPx, endZoneDepth);
  endZoneG.fill({ color: ownEndZoneColor, alpha: 0.8 });
  container.addChild(endZoneG);

  // Own end zone text
  if (offenseTeam?.abbr) {
    const text = new Text({
      text: offenseTeam.abbr,
      style: new TextStyle({
        fontSize: Math.max(16, 24 * (scale / 10)),
        fill: 0xffffff,
        fontWeight: 'bold',
        fontFamily: 'Arial Black, sans-serif',
        letterSpacing: 4,
      }),
    });
    text.anchor.set(0.5);
    text.x = canvasWidth / 2;
    text.y = ownEndZoneTop.y + endZoneDepth / 2;
    text.alpha = 0.7;
    container.addChild(text);
  }

  // Opponent end zone (yard line 100 to 110)
  const oppEndZoneBottom = yardToWorld(0, 100);
  const oppEndZoneG = new Graphics();
  const defenseTeam = awayTeamInfo;
  const oppEndZoneColor = defenseTeam?.primaryColor ? parseColor(defenseTeam.primaryColor) : COLORS.endZone;
  oppEndZoneG.rect(fieldLeft, oppEndZoneBottom.y - endZoneDepth, fieldWidthPx, endZoneDepth);
  oppEndZoneG.fill({ color: oppEndZoneColor, alpha: 0.8 });
  container.addChild(oppEndZoneG);

  // Opponent end zone text
  if (defenseTeam?.abbr) {
    const text = new Text({
      text: defenseTeam.abbr,
      style: new TextStyle({
        fontSize: Math.max(16, 24 * (scale / 10)),
        fill: 0xffffff,
        fontWeight: 'bold',
        fontFamily: 'Arial Black, sans-serif',
        letterSpacing: 4,
      }),
    });
    text.anchor.set(0.5);
    text.x = canvasWidth / 2;
    text.y = oppEndZoneBottom.y - endZoneDepth / 2;
    text.alpha = 0.7;
    container.addChild(text);
  }

  // Yard lines every 5 yards with numbers
  const linesG = new Graphics();
  for (let yardLine = 5; yardLine <= 95; yardLine += 5) {
    const pos = yardToWorld(0, yardLine);

    // Draw yard line
    linesG.moveTo(fieldLeft, pos.y);
    linesG.lineTo(fieldRight, pos.y);
    linesG.stroke({ color: COLORS.fieldLines, width: YARD_LINE_WIDTH, alpha: 0.7 });

    // Yard numbers at 10-yard intervals
    if (yardLine % 10 === 0 && yardLine >= 10 && yardLine <= 90) {
      const displayNum = getDisplayYardNumber(yardLine);
      const yardText = displayNum.toString();

      const fontSize = Math.max(14, 20 * (scale / 10));
      const numberOffset = 6 * scale;

      // Left number - faces baseline to sideline (top points toward opponent end zone)
      const leftText = new Text({
        text: yardText,
        style: new TextStyle({
          fontSize,
          fill: COLORS.yardNumber,
          fontWeight: 'bold',
          fontFamily: 'Arial Black, sans-serif',
        }),
      });
      leftText.anchor.set(0.5);
      leftText.x = fieldLeft + numberOffset;
      leftText.y = pos.y;
      leftText.rotation = Math.PI / 2;  // Top points right (toward opponent end zone in our view)
      leftText.alpha = 0.6;
      container.addChild(leftText);

      // Right number - faces baseline to sideline (top points toward opponent end zone)
      const rightText = new Text({
        text: yardText,
        style: new TextStyle({
          fontSize,
          fill: COLORS.yardNumber,
          fontWeight: 'bold',
          fontFamily: 'Arial Black, sans-serif',
        }),
      });
      rightText.anchor.set(0.5);
      rightText.x = fieldRight - numberOffset;
      rightText.y = pos.y;
      rightText.rotation = -Math.PI / 2;  // Top points left (toward opponent end zone in our view)
      rightText.alpha = 0.6;
      container.addChild(rightText);
    }
  }
  container.addChild(linesG);

  // Midfield logo (at 50 yard line)
  const midfieldPos = yardToWorld(0, 50);
  const logoPath = homeTeamInfo?.logo;
  if (logoPath) {
    loadMidfieldLogo(container, logoPath, canvasWidth / 2, midfieldPos.y, scale);
  } else {
    const midfieldText = new Text({
      text: '50',
      style: new TextStyle({
        fontSize: Math.max(20, 32 * (scale / 10)),
        fill: COLORS.yardNumber,
        fontWeight: 'bold',
        fontFamily: 'Arial Black, sans-serif',
      }),
    });
    midfieldText.anchor.set(0.5);
    midfieldText.x = canvasWidth / 2;
    midfieldText.y = midfieldPos.y;
    midfieldText.alpha = 0.25;
    container.addChild(midfieldText);
  }

  // Hash marks for entire field
  const hashG = new Graphics();

  for (let yardLine = 1; yardLine <= 99; yardLine += 1) {
    const pos = yardToWorld(0, yardLine);
    const hashWidth = 3 * (scale / 10);

    // Left hash
    hashG.moveTo(hashLeftX - hashWidth, pos.y);
    hashG.lineTo(hashLeftX + hashWidth, pos.y);
    hashG.stroke({ color: COLORS.hashMarks, width: HASH_MARK_WIDTH, alpha: 0.4 });

    // Right hash
    hashG.moveTo(hashRightX - hashWidth, pos.y);
    hashG.lineTo(hashRightX + hashWidth, pos.y);
    hashG.stroke({ color: COLORS.hashMarks, width: HASH_MARK_WIDTH, alpha: 0.4 });
  }
  container.addChild(hashG);

  // Sidelines (extend beyond visible area)
  const sidelineG = new Graphics();
  sidelineG.moveTo(fieldLeft, topOfField.y);
  sidelineG.lineTo(fieldLeft, bottomOfField.y);
  sidelineG.stroke({ color: COLORS.sideline, width: 3 });

  sidelineG.moveTo(fieldRight, topOfField.y);
  sidelineG.lineTo(fieldRight, bottomOfField.y);
  sidelineG.stroke({ color: COLORS.sideline, width: 3 });
  container.addChild(sidelineG);

  // Goal lines (at 0 and 100)
  const ownGoalPos = yardToWorld(0, 0);
  const goalG = new Graphics();
  goalG.moveTo(fieldLeft, ownGoalPos.y);
  goalG.lineTo(fieldRight, ownGoalPos.y);
  goalG.stroke({ color: 0xffffff, width: 4 });

  const oppGoalPos = yardToWorld(0, 100);
  goalG.moveTo(fieldLeft, oppGoalPos.y);
  goalG.lineTo(fieldRight, oppGoalPos.y);
  goalG.stroke({ color: 0xffffff, width: 4 });
  container.addChild(goalG);

  // LOS line (blue) - at actual yard line position
  const losPos = yardToWorld(0, losYardLine);
  const losLine = new Graphics();
  losLine.moveTo(fieldLeft, losPos.y);
  losLine.lineTo(fieldRight, losPos.y);
  losLine.stroke({ color: COLORS.lineOfScrimmage, width: LOS_LINE_WIDTH });
  container.addChild(losLine);

  // First down line (yellow) - at actual yard line position
  if (firstDownYardLine > 0 && firstDownYardLine <= 100) {
    const firstDownPos = yardToWorld(0, firstDownYardLine);
    const firstDownLine = new Graphics();
    firstDownLine.moveTo(fieldLeft, firstDownPos.y);
    firstDownLine.lineTo(fieldRight, firstDownPos.y);
    firstDownLine.stroke({ color: COLORS.firstDownLine, width: FIRST_DOWN_LINE_WIDTH });
    container.addChild(firstDownLine);
  }
}

export function drawEndZone(
  container: Container,
  config: FieldConfig,
  isHome: boolean,
  teamColor: number,
  teamName: string,
): void {
  const { scale, canvasWidth } = config;
  const fieldWidthPx = FIELD_WIDTH_YARDS * scale;
  const fieldLeft = (canvasWidth - fieldWidthPx) / 2;
  const endZoneDepth = END_ZONE_DEPTH * scale;

  const g = new Graphics();

  // End zone rectangle
  const y = isHome ? 0 : container.parent?.height || 600 - endZoneDepth;
  g.rect(fieldLeft, y, fieldWidthPx, endZoneDepth);
  g.fill({ color: teamColor || COLORS.endZone, alpha: 0.9 });

  container.addChild(g);

  // Team name text
  const text = new Text({
    text: teamName.toUpperCase(),
    style: new TextStyle({
      fontSize: 24 * (scale / 10),
      fill: 0xffffff,
      fontWeight: 'bold',
      fontFamily: 'Arial Black, sans-serif',
      letterSpacing: 8,
    }),
  });
  text.anchor.set(0.5);
  text.x = canvasWidth / 2;
  text.y = y + endZoneDepth / 2;
  text.alpha = 0.7;
  container.addChild(text);
}
