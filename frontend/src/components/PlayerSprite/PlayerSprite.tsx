/**
 * PlayerSprite - Animated sprite component for football players.
 *
 * This component manages a PixiJS AnimatedSprite for player visualization.
 * It handles loading sprite sheets, animation switching, and position updates.
 *
 * Note: This component is designed to be used with a PixiJS Application
 * that is managed separately (e.g., in SandboxCanvas).
 */

import { useEffect, useRef, useCallback } from "react";
import { AnimatedSprite, Application, Assets, Spritesheet } from "pixi.js";
import type {
  PlayerAnimationType,
  SpriteSheetData,
} from "../../types/sprites";

interface PlayerSpriteController {
  /** The AnimatedSprite instance */
  sprite: AnimatedSprite | null;
  /** Update sprite position */
  setPosition: (x: number, y: number) => void;
  /** Play an animation */
  playAnimation: (name: PlayerAnimationType, loop?: boolean) => void;
  /** Stop the current animation */
  stop: () => void;
  /** Set sprite scale */
  setScale: (scale: number) => void;
  /** Flip sprite horizontally */
  setFlipX: (flip: boolean) => void;
  /** Destroy the sprite and clean up */
  destroy: () => void;
}

/**
 * Create and manage a player sprite within a PixiJS application.
 *
 * @param app - The PixiJS Application instance
 * @param sheetPath - Path to the sprite sheet JSON
 * @param initialAnimation - Initial animation to play
 * @param onComplete - Called when non-looping animation finishes
 * @returns Controller object for the sprite
 *
 * @example
 * ```tsx
 * const app = new Application();
 * await app.init({ width: 800, height: 600 });
 *
 * const player = await createPlayerSprite(
 *   app,
 *   '/sprites/qb_animations.json',
 *   'idle'
 * );
 *
 * player.setPosition(400, 300);
 * player.playAnimation('throw', false);
 * ```
 */
export async function createPlayerSprite(
  app: Application,
  sheetPath: string,
  initialAnimation: PlayerAnimationType = "idle",
  onComplete?: () => void
): Promise<PlayerSpriteController> {
  // Load the sprite sheet JSON
  const response = await fetch(sheetPath);
  if (!response.ok) {
    throw new Error(`Failed to load sprite sheet: ${sheetPath}`);
  }
  const data: SpriteSheetData = await response.json();

  // Get image path
  const basePath = sheetPath.substring(0, sheetPath.lastIndexOf("/") + 1);
  const imagePath = basePath + data.meta.image;

  // Load texture
  const texture = await Assets.load(imagePath);

  // Create spritesheet
  const sheet = new Spritesheet(texture, data);
  await sheet.parse();

  // Create AnimatedSprite
  const animations = Object.keys(data.animations);
  const startAnimation = animations.includes(initialAnimation)
    ? initialAnimation
    : animations[0];

  const sprite = new AnimatedSprite(sheet.animations[startAnimation]);
  sprite.anchor.set(0.5);
  sprite.animationSpeed = 0.2;

  if (onComplete) {
    sprite.onComplete = onComplete;
  }

  // Add to stage
  app.stage.addChild(sprite);
  sprite.play();

  // Return controller
  return {
    sprite,

    setPosition(x: number, y: number) {
      sprite.x = x;
      sprite.y = y;
    },

    playAnimation(name: PlayerAnimationType, loop: boolean = true) {
      const textures = sheet.animations[name];
      if (!textures) {
        console.warn(`Animation "${name}" not found`);
        return;
      }

      sprite.textures = textures;
      sprite.loop = loop;

      // Set animation-specific speed
      if (data.meta.animationData?.[name]) {
        sprite.animationSpeed = data.meta.animationData[name].fps / 60;
      }

      sprite.gotoAndPlay(0);
    },

    stop() {
      sprite.stop();
    },

    setScale(scale: number) {
      sprite.scale.set(scale);
    },

    setFlipX(flip: boolean) {
      sprite.scale.x = Math.abs(sprite.scale.x) * (flip ? -1 : 1);
    },

    destroy() {
      sprite.stop();
      app.stage.removeChild(sprite);
      sprite.destroy();
    },
  };
}

/**
 * React hook for managing a player sprite within a PixiJS app.
 *
 * @example
 * ```tsx
 * function GameCanvas() {
 *   const appRef = useRef<Application>(null);
 *   const { sprite, setPosition, playAnimation } = usePlayerSprite({
 *     app: appRef.current,
 *     sheetPath: '/sprites/qb.json',
 *     initialAnimation: 'idle',
 *   });
 *
 *   useEffect(() => {
 *     if (sprite) {
 *       setPosition(100, 100);
 *     }
 *   }, [sprite]);
 *
 *   return <div id="canvas" />;
 * }
 * ```
 */
export function usePlayerSprite({
  app,
  sheetPath,
  initialAnimation = "idle",
  onComplete,
}: {
  app: Application | null;
  sheetPath: string;
  initialAnimation?: PlayerAnimationType;
  onComplete?: () => void;
}) {
  const controllerRef = useRef<PlayerSpriteController | null>(null);

  useEffect(() => {
    if (!app) return;

    let mounted = true;

    const init = async () => {
      try {
        const controller = await createPlayerSprite(
          app,
          sheetPath,
          initialAnimation,
          onComplete
        );

        if (!mounted) {
          controller.destroy();
          return;
        }

        controllerRef.current = controller;
      } catch (err) {
        console.error("Failed to create player sprite:", err);
      }
    };

    init();

    return () => {
      mounted = false;
      controllerRef.current?.destroy();
      controllerRef.current = null;
    };
  }, [app, sheetPath, initialAnimation, onComplete]);

  const setPosition = useCallback((x: number, y: number) => {
    controllerRef.current?.setPosition(x, y);
  }, []);

  const playAnimation = useCallback(
    (name: PlayerAnimationType, loop?: boolean) => {
      controllerRef.current?.playAnimation(name, loop);
    },
    []
  );

  const stop = useCallback(() => {
    controllerRef.current?.stop();
  }, []);

  const setScale = useCallback((scale: number) => {
    controllerRef.current?.setScale(scale);
  }, []);

  const setFlipX = useCallback((flip: boolean) => {
    controllerRef.current?.setFlipX(flip);
  }, []);

  return {
    sprite: controllerRef.current?.sprite ?? null,
    setPosition,
    playAnimation,
    stop,
    setScale,
    setFlipX,
  };
}
