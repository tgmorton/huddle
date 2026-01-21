/**
 * BallRenderer - Brown oval football with white laces
 *
 * Features:
 * - Oval shape (ellipse)
 * - Brown fill
 * - White laces detail
 * - 3D height lift effect (ball rises on screen based on height)
 * - Shadow on ground that grows with height
 * - Ball rotation based on movement direction (uses yard coords for accuracy)
 * - Held ball rendered at carrier's side with orientation
 * - Glow effect when in flight
 */

import { Graphics, Container } from 'pixi.js';
import type { BallFrame, Vec2 } from '../types';
import { COLORS, BALL_WIDTH, BALL_HEIGHT } from '../constants';

export interface BallConfig {
  scale: number;
  showBall: boolean;  // false in field view except during passes
}

// Track previous ball position in YARD coordinates for accurate direction
let previousYardPos: Vec2 | null = null;
let ballRotation = 0;  // Current ball rotation in radians

// Animation state for spin visualization
let spinAnimationAngle = 0;
let wobblePhase = 0;

export function clearBallHistory(): void {
  previousYardPos = null;
  ballRotation = 0;
  spinAnimationAngle = 0;
  wobblePhase = 0;
}

/**
 * Draw the ball - handles in-flight, loose, and held states
 */
export function drawBall(
  container: Container,
  ball: BallFrame,
  screenPos: Vec2,
  config: BallConfig,
  carrierInfo?: { screenPos: Vec2; facingX?: number; facingY?: number; vx?: number; vy?: number },
): void {
  container.removeChildren();

  const scaleFactor = config.scale / 12;
  const baseWidth = BALL_WIDTH * scaleFactor;
  const baseHeight = BALL_HEIGHT * scaleFactor;

  // Handle held ball - draw at carrier's side
  if (ball.state === 'held' && carrierInfo) {
    drawHeldBall(container, carrierInfo, baseWidth, baseHeight, scaleFactor);
    previousYardPos = null;  // Reset tracking when ball is held
    return;
  }

  // Don't draw if not showing and not in flight
  if (!config.showBall && ball.state !== 'in_flight') return;

  // Calculate size based on height (bigger when higher = further from camera)
  const heightBonus = Math.min(ball.height / 10, 1.5);
  const width = baseWidth * (1 + heightBonus * 0.3);
  const height = baseHeight * (1 + heightBonus * 0.3);

  // Calculate height offset for 3D effect (ball rises on screen)
  const heightOffset = ball.height * 4 * scaleFactor;

  // Calculate ball rotation based on physics orientation or movement direction
  const currentYardPos = { x: ball.x, y: ball.y };

  if (ball.state === 'in_flight') {
    // Use physics-based orientation if available
    if (ball.orientation) {
      // Calculate base rotation from orientation vector
      // orientation.y is downfield, orientation.x is lateral
      // On screen: +Y is down, so we negate Y for screen coords
      ballRotation = Math.atan2(-ball.orientation.y, ball.orientation.x);

      // Animate spin visualization (visual effect only)
      const spinRpm = ball.spin_rate ?? 500;
      // At 20 fps, each frame = 0.05s, so spin angle = rpm/60 * 0.05 * 2π
      spinAnimationAngle += (spinRpm / 60) * 0.05 * Math.PI * 2;

      // Add wobble for unstable passes
      if (ball.is_stable === false) {
        // Wobble at ~5Hz (assuming ~20fps, phase increment = 0.3)
        wobblePhase += 0.3;
        const wobble = Math.sin(wobblePhase) * 0.2;  // ±0.2 radians (~11 degrees)
        ballRotation += wobble;
      }
    } else if (previousYardPos) {
      // Fallback: calculate from movement direction
      const dx = currentYardPos.x - previousYardPos.x;
      const dy = currentYardPos.y - previousYardPos.y;
      const distance = Math.sqrt(dx * dx + dy * dy);

      if (distance > 0.1) {
        ballRotation = Math.atan2(-dy, dx);
      }
    }
  } else {
    // Reset when not in flight
    ballRotation = 0;
    spinAnimationAngle = 0;
    wobblePhase = 0;
  }

  // Store current yard position for next frame
  previousYardPos = { ...currentYardPos };

  // Ground position (where shadow goes)
  const groundY = screenPos.y;
  // Ball position (elevated based on height)
  const ballY = screenPos.y - heightOffset;

  const g = new Graphics();

  // Draw shadow at ground level
  const shadowSize = 1 + heightBonus * 0.5;  // Shadow grows with height
  const shadowAlpha = Math.max(0.1, 0.4 - heightBonus * 0.15);  // Shadow fades with height
  g.ellipse(screenPos.x, groundY + 2, width * shadowSize * 0.8, height * shadowSize * 0.3);
  g.fill({ color: 0x000000, alpha: shadowAlpha });

  // Glow effect for in-flight ball
  if (ball.state === 'in_flight') {
    // Orange tint for unstable/wobbly pass
    if (ball.is_stable === false) {
      g.circle(screenPos.x, ballY, width * 1.8);
      g.fill({ color: 0xcc6600, alpha: 0.25 });  // Orange warning glow
    }
    g.circle(screenPos.x, ballY, width * 1.5);
    g.fill({ color: COLORS.ballInFlight, alpha: 0.3 });
  }

  container.addChild(g);

  // Main ball shape (ellipse) - in a separate container for rotation
  const ballColor = ball.state === 'in_flight' ? COLORS.ballInFlight : COLORS.ball;

  // Create a container for the rotated ball
  const ballContainer = new Container();
  ballContainer.x = screenPos.x;
  ballContainer.y = ballY;
  ballContainer.rotation = ballRotation;

  // Draw ball centered at origin (container handles position/rotation)
  const ballG = new Graphics();
  ballG.ellipse(0, 0, width, height);
  ballG.fill({ color: ballColor });
  ballG.stroke({ color: 0xffffff, width: 1 });

  // White laces (also rotated with ball)
  if (config.scale >= 10) {  // Only draw laces when zoomed in enough
    const laceWidth = width * 0.5;
    const laceSpacing = height * 0.3;

    ballG.moveTo(-laceWidth / 2, 0);
    ballG.lineTo(laceWidth / 2, 0);
    ballG.stroke({ color: COLORS.ballLaces, width: 1.5 });

    // Small perpendicular laces
    for (let i = -1; i <= 1; i++) {
      const lx = i * laceSpacing;
      ballG.moveTo(lx, -2);
      ballG.lineTo(lx, 2);
      ballG.stroke({ color: COLORS.ballLaces, width: 1 });
    }
  }

  ballContainer.addChild(ballG);
  container.addChild(ballContainer);
}

/**
 * Draw ball held by a carrier - positioned at their side with orientation
 */
function drawHeldBall(
  container: Container,
  carrierInfo: { screenPos: Vec2; facingX?: number; facingY?: number; vx?: number; vy?: number },
  baseWidth: number,
  baseHeight: number,
  scaleFactor: number,
): void {
  const { screenPos, facingX, facingY, vx, vy } = carrierInfo;

  // Determine which side to hold the ball based on facing/movement direction
  // Default to right side, switch to left if moving/facing left
  let holdSide = 1;  // 1 = right, -1 = left

  // Use facing direction if available, otherwise use velocity
  const dirX = facingX ?? vx ?? 0;
  if (dirX < -0.1) {
    holdSide = -1;  // Facing/moving left, hold on left side
  }

  // Calculate ball orientation based on carrier's facing direction
  // Ball should point in direction carrier is facing/moving
  const dirY = facingY ?? vy ?? 1;  // Default to facing downfield
  let heldRotation = Math.atan2(-dirY, dirX);  // Negate Y for screen coords

  // Offset ball to the side of the carrier
  const sideOffset = 8 * scaleFactor * holdSide;
  const ballX = screenPos.x + sideOffset;
  const ballY = screenPos.y;

  // Slightly smaller ball when held (tucked)
  const width = baseWidth * 0.85;
  const height = baseHeight * 0.85;

  // Create container for rotated ball
  const ballContainer = new Container();
  ballContainer.x = ballX;
  ballContainer.y = ballY;
  ballContainer.rotation = heldRotation;

  // Draw ball
  const ballG = new Graphics();
  ballG.ellipse(0, 0, width, height);
  ballG.fill({ color: COLORS.ball });
  ballG.stroke({ color: 0xffffff, width: 1 });

  // Draw laces
  const laceWidth = width * 0.5;
  const laceSpacing = height * 0.3;

  ballG.moveTo(-laceWidth / 2, 0);
  ballG.lineTo(laceWidth / 2, 0);
  ballG.stroke({ color: COLORS.ballLaces, width: 1.5 });

  for (let i = -1; i <= 1; i++) {
    const lx = i * laceSpacing;
    ballG.moveTo(lx, -2);
    ballG.lineTo(lx, 2);
    ballG.stroke({ color: COLORS.ballLaces, width: 1 });
  }

  ballContainer.addChild(ballG);
  container.addChild(ballContainer);
}

export function shouldShowBall(ball: BallFrame, viewMode: 'field' | 'game'): boolean {
  // Always show in game view
  if (viewMode === 'game') return true;

  // In field view, only show during passes
  return ball.state === 'in_flight';
}
