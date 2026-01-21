/**
 * usePlaybackState - Animation state management for play visualization
 *
 * Handles:
 * - Animation loop (requestAnimationFrame)
 * - Playback speed control
 * - Tick advancement
 * - Play/pause state
 */

import { useRef, useCallback, useEffect } from 'react';
import { MS_PER_TICK } from '../constants';

export interface UsePlaybackStateOptions {
  frames: unknown[];
  currentTick: number;
  isPlaying: boolean;
  playbackSpeed: number;
  onTickChange: (tick: number) => void;
  onComplete?: () => void;
}

export function usePlaybackState({
  frames,
  currentTick,
  isPlaying,
  playbackSpeed,
  onTickChange,
  onComplete,
}: UsePlaybackStateOptions) {
  const animationRef = useRef<number | null>(null);
  const lastTickTimeRef = useRef<number>(0);

  // Stop animation
  const stopAnimation = useCallback(() => {
    if (animationRef.current !== null) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
  }, []);

  // Animation loop
  useEffect(() => {
    if (!isPlaying || frames.length === 0) {
      stopAnimation();
      return;
    }

    const msPerTick = MS_PER_TICK / playbackSpeed;
    lastTickTimeRef.current = performance.now();

    const animate = (timestamp: number) => {
      const elapsed = timestamp - lastTickTimeRef.current;

      if (elapsed >= msPerTick) {
        const newTick = currentTick + 1;

        if (newTick >= frames.length) {
          // Animation complete
          stopAnimation();
          onComplete?.();
          return;
        }

        onTickChange(newTick);
        lastTickTimeRef.current = timestamp;
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);

    return stopAnimation;
  }, [isPlaying, playbackSpeed, currentTick, frames.length, onTickChange, onComplete, stopAnimation]);

  // Cleanup on unmount
  useEffect(() => {
    return stopAnimation;
  }, [stopAnimation]);

  return {
    stopAnimation,
  };
}

export default usePlaybackState;
