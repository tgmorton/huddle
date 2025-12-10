/**
 * Types for sprite sheet and animation system.
 *
 * These types match the JSON output from the sprite-pipeline tool.
 */

/**
 * Single frame metadata in a sprite sheet.
 */
export interface SpriteFrame {
  frame: { x: number; y: number; w: number; h: number };
  rotated: boolean;
  trimmed: boolean;
  spriteSourceSize: { x: number; y: number; w: number; h: number };
  sourceSize: { w: number; h: number };
}

/**
 * Animation-specific metadata (fps, loop settings).
 */
export interface AnimationData {
  fps: number;
  loop: boolean;
}

/**
 * Full sprite sheet data structure.
 * Matches the JSON output from sprite-pipeline.
 */
export interface SpriteSheetData {
  frames: Record<string, SpriteFrame>;
  animations: Record<string, string[]>;
  meta: {
    app: string;
    version: string;
    image: string;
    format: string;
    size: { w: number; h: number };
    scale: string;
    fps?: number;
    loop?: boolean;
    animationData?: Record<string, AnimationData>;
  };
}

/**
 * Available player animation types.
 */
export type PlayerAnimationType =
  | "idle"
  | "run"
  | "block"
  | "tackle"
  | "throw"
  | "catch"
  | "celebrate";

/**
 * Player position types for sprite selection.
 */
export type PlayerPosition =
  | "QB"
  | "RB"
  | "WR"
  | "TE"
  | "OL"
  | "DL"
  | "LB"
  | "CB"
  | "S";

/**
 * Configuration for a player sprite.
 */
export interface PlayerSpriteConfig {
  position: PlayerPosition;
  team: "home" | "away";
  sheetPath: string;
  defaultAnimation: PlayerAnimationType;
}

/**
 * Current animation state.
 */
export interface AnimationState {
  currentAnimation: PlayerAnimationType;
  isPlaying: boolean;
  currentFrame: number;
  loop: boolean;
  speed: number;
}

/**
 * Props for the PlayerSprite component.
 */
export interface PlayerSpriteProps {
  sheetPath: string;
  x: number;
  y: number;
  animation: PlayerAnimationType;
  scale?: number;
  flipX?: boolean;
  onAnimationComplete?: () => void;
}
