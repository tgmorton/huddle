/**
 * FlyoverCamera.tsx - Animated camera following spline path
 * Uses GSAP for timeline-based animation orchestration
 */

import { useRef, useEffect, useCallback } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import gsap from 'gsap';
import {
  createFlyoverPath,
  createLookAtPath,
  getKeyframe,
  easeInOutCubic,
  getCurrentPhase,
} from './cameraPath';

interface FlyoverCameraProps {
  isPlaying: boolean;
  duration?: number; // Total animation duration in seconds
  onPhaseChange?: (phase: 'approach' | 'fieldReveal' | 'fieldSwoop' | 'branding') => void;
  onComplete?: () => void;
}

export function FlyoverCamera({
  isPlaying,
  duration = 10,
  onPhaseChange,
  onComplete,
}: FlyoverCameraProps) {
  const { camera } = useThree();
  const progressRef = useRef({ value: 0 });
  const timelineRef = useRef<gsap.core.Timeline | null>(null);
  const lastPhaseRef = useRef<string>('');

  // Create paths
  const positionPath = useRef(createFlyoverPath());
  const lookAtPath = useRef(createLookAtPath());

  // Update camera position based on progress
  const updateCamera = useCallback(
    (progress: number) => {
      const easedProgress = easeInOutCubic(progress);
      const keyframe = getKeyframe(
        positionPath.current,
        lookAtPath.current,
        easedProgress
      );

      camera.position.copy(keyframe.position);
      camera.lookAt(keyframe.lookAt);

      // Check for phase changes
      const currentPhase = getCurrentPhase(progress);
      if (currentPhase !== lastPhaseRef.current) {
        lastPhaseRef.current = currentPhase;
        onPhaseChange?.(currentPhase);
      }
    },
    [camera, onPhaseChange]
  );

  // Don't set initial position - let Canvas default handle it
  // The animation will set position when playback starts

  // Handle play/pause
  useEffect(() => {
    if (isPlaying) {
      // Reset progress
      progressRef.current.value = 0;
      lastPhaseRef.current = '';

      // Create GSAP timeline
      timelineRef.current = gsap.timeline({
        onComplete: () => {
          onComplete?.();
        },
      });

      timelineRef.current.to(progressRef.current, {
        value: 1,
        duration,
        ease: 'none', // We apply our own easing in updateCamera
        onUpdate: () => {
          updateCamera(progressRef.current.value);
        },
      });
    } else {
      // Pause/kill timeline
      if (timelineRef.current) {
        timelineRef.current.kill();
        timelineRef.current = null;
      }
    }

    return () => {
      if (timelineRef.current) {
        timelineRef.current.kill();
      }
    };
  }, [isPlaying, duration, updateCamera, onComplete]);

  // Optional: Add subtle camera shake for realism
  useFrame((state) => {
    if (!isPlaying) return;

    const time = state.clock.elapsedTime;
    const shake = 0.1;

    // Very subtle shake that decreases as we get closer
    const progress = progressRef.current.value;
    const shakeIntensity = Math.max(0, 1 - progress) * shake;

    camera.position.x += Math.sin(time * 10) * shakeIntensity;
    camera.position.y += Math.cos(time * 12) * shakeIntensity * 0.5;
  });

  return null; // Camera is manipulated via refs, no JSX needed
}

// Reset camera to starting position
export function useCameraReset() {
  const { camera } = useThree();

  return useCallback(() => {
    const positionPath = createFlyoverPath();
    const lookAtPath = createLookAtPath();
    const keyframe = getKeyframe(positionPath, lookAtPath, 0);

    gsap.to(camera.position, {
      x: keyframe.position.x,
      y: keyframe.position.y,
      z: keyframe.position.z,
      duration: 1,
      ease: 'power2.inOut',
    });

    // Also animate lookAt
    const target = keyframe.lookAt;
    camera.lookAt(target);
  }, [camera]);
}
