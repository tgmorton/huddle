/**
 * Hook for managing PixiJS sprite animations.
 *
 * Loads sprite sheets and provides animation control for AnimatedSprite.
 */

import { useEffect, useRef, useCallback, useState } from "react";
import { AnimatedSprite, Assets, Spritesheet } from "pixi.js";
import type { SpriteSheetData } from "../types/sprites";

interface UseSpriteAnimationOptions {
  /** Path to the sprite sheet JSON file */
  sheetPath: string;
  /** Initial animation to play */
  initialAnimation?: string;
  /** Default animation speed (0-1, where 1 = 60fps) */
  animationSpeed?: number;
  /** Called when a non-looping animation completes */
  onComplete?: () => void;
}

interface UseSpriteAnimationResult {
  /** The AnimatedSprite instance (null until loaded) */
  sprite: AnimatedSprite | null;
  /** The loaded Spritesheet (null until loaded) */
  spritesheet: Spritesheet | null;
  /** Whether the sprite sheet is loaded */
  isLoaded: boolean;
  /** Any loading error */
  error: Error | null;
  /** Play a specific animation */
  playAnimation: (name: string, loop?: boolean) => void;
  /** Stop the current animation */
  stop: () => void;
  /** List of available animation names */
  availableAnimations: string[];
}

/**
 * Hook for loading and controlling sprite animations.
 *
 * @example
 * ```tsx
 * const { sprite, isLoaded, playAnimation } = useSpriteAnimation({
 *   sheetPath: '/sprites/player.json',
 *   initialAnimation: 'idle',
 * });
 *
 * // Later, in your PixiJS setup:
 * if (sprite) {
 *   app.stage.addChild(sprite);
 *   playAnimation('run', true);
 * }
 * ```
 */
export function useSpriteAnimation({
  sheetPath,
  initialAnimation,
  animationSpeed = 0.2,
  onComplete,
}: UseSpriteAnimationOptions): UseSpriteAnimationResult {
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [availableAnimations, setAvailableAnimations] = useState<string[]>([]);

  const spriteRef = useRef<AnimatedSprite | null>(null);
  const spritesheetRef = useRef<Spritesheet | null>(null);
  const sheetDataRef = useRef<SpriteSheetData | null>(null);

  // Load spritesheet
  useEffect(() => {
    let mounted = true;

    const loadSheet = async () => {
      try {
        // Load the JSON metadata
        const jsonResponse = await fetch(sheetPath);
        if (!jsonResponse.ok) {
          throw new Error(`Failed to load sprite sheet: ${sheetPath}`);
        }
        const data: SpriteSheetData = await jsonResponse.json();
        sheetDataRef.current = data;

        // Get the image path relative to the JSON
        const basePath = sheetPath.substring(0, sheetPath.lastIndexOf("/") + 1);
        const imagePath = basePath + data.meta.image;

        // Load the texture
        const texture = await Assets.load(imagePath);

        // Create spritesheet
        const sheet = new Spritesheet(texture, data);
        await sheet.parse();

        if (!mounted) return;

        spritesheetRef.current = sheet;

        // Get available animations
        const animations = Object.keys(data.animations);
        setAvailableAnimations(animations);

        // Create initial AnimatedSprite
        const firstAnimation = initialAnimation || animations[0];
        if (firstAnimation && sheet.animations[firstAnimation]) {
          const sprite = new AnimatedSprite(sheet.animations[firstAnimation]);
          sprite.animationSpeed = animationSpeed;
          sprite.anchor.set(0.5);

          // Set up completion callback
          sprite.onComplete = () => {
            onComplete?.();
          };

          spriteRef.current = sprite;
        }

        setIsLoaded(true);
        setError(null);
      } catch (err) {
        if (!mounted) return;
        setError(err instanceof Error ? err : new Error(String(err)));
        setIsLoaded(false);
      }
    };

    loadSheet();

    return () => {
      mounted = false;
    };
  }, [sheetPath, initialAnimation, animationSpeed, onComplete]);

  // Play animation
  const playAnimation = useCallback(
    (name: string, loop: boolean = true) => {
      const sprite = spriteRef.current;
      const sheet = spritesheetRef.current;
      const data = sheetDataRef.current;

      if (!sprite || !sheet || !data) return;

      const textures = sheet.animations[name];
      if (!textures) {
        console.warn(`Animation "${name}" not found in spritesheet`);
        return;
      }

      sprite.textures = textures;
      sprite.loop = loop;

      // Get animation-specific speed if available
      if (data.meta.animationData?.[name]) {
        const fps = data.meta.animationData[name].fps;
        sprite.animationSpeed = fps / 60; // Convert FPS to PixiJS speed
      }

      sprite.gotoAndPlay(0);
    },
    []
  );

  // Stop animation
  const stop = useCallback(() => {
    spriteRef.current?.stop();
  }, []);

  return {
    sprite: spriteRef.current,
    spritesheet: spritesheetRef.current,
    isLoaded,
    error,
    playAnimation,
    stop,
    availableAnimations,
  };
}

/**
 * Preload multiple sprite sheets for faster access later.
 *
 * @param sheetPaths - Array of sprite sheet JSON paths
 * @returns Promise that resolves when all sheets are loaded
 */
export async function preloadSpriteSheets(
  sheetPaths: string[]
): Promise<void> {
  await Promise.all(
    sheetPaths.map(async (path) => {
      const response = await fetch(path);
      const data: SpriteSheetData = await response.json();
      const basePath = path.substring(0, path.lastIndexOf("/") + 1);
      const imagePath = basePath + data.meta.image;
      await Assets.load(imagePath);
    })
  );
}
