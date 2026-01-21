/**
 * cameraPath.ts - Spline path definitions for camera flyover
 * Defines CatmullRomCurve3 paths for smooth camera movement
 */

import * as THREE from 'three';

export interface CameraKeyframe {
  position: THREE.Vector3;
  lookAt: THREE.Vector3;
}

// Main flyover path: approach from distance, swoop over stadium, settle to broadcast angle
export function createFlyoverPath(): THREE.CatmullRomCurve3 {
  return new THREE.CatmullRomCurve3([
    // Start: Far away, high altitude
    new THREE.Vector3(-400, 180, -200),
    // Approach: Coming in toward stadium
    new THREE.Vector3(-200, 120, -100),
    // Stadium edge: Clear the rim
    new THREE.Vector3(-80, 60, -40),
    // Field reveal: Above the 50-yard line
    new THREE.Vector3(0, 50, -20),
    // Low swoop: Across the field
    new THREE.Vector3(30, 25, 0),
    // Rising: Coming up from field level
    new THREE.Vector3(40, 40, 15),
    // Final: Broadcast camera position (sideline, elevated)
    new THREE.Vector3(0, 35, -60),
  ]);
}

// Look-at path: Where the camera should be looking at each point
export function createLookAtPath(): THREE.CatmullRomCurve3 {
  return new THREE.CatmullRomCurve3([
    // Look at stadium center from afar
    new THREE.Vector3(0, 0, 0),
    // Continue looking at center
    new THREE.Vector3(0, 0, 0),
    // Look at field as we approach
    new THREE.Vector3(0, 0, 0),
    // Look across field during reveal
    new THREE.Vector3(20, 0, 0),
    // Look down field during swoop
    new THREE.Vector3(60, 0, 0),
    // Look at midfield as we rise
    new THREE.Vector3(0, 0, 0),
    // Final broadcast view - center of field
    new THREE.Vector3(0, 0, 0),
  ]);
}

// Timing for each phase (cumulative, 0-1)
export const PHASE_TIMINGS = {
  approach: { start: 0, end: 0.4 },      // 0-4s: Approach through fog
  fieldReveal: { start: 0.4, end: 0.6 }, // 4-6s: Clear rim, see field
  fieldSwoop: { start: 0.6, end: 0.8 },  // 6-8s: Low sweep across
  branding: { start: 0.8, end: 1.0 },    // 8-10s: Rise, logos appear
};

// Alternative paths for variety
export function createHelicopterPath(): THREE.CatmullRomCurve3 {
  // Circular orbit around stadium
  const points: THREE.Vector3[] = [];
  const radius = 150;
  const height = 80;

  for (let i = 0; i <= 16; i++) {
    const angle = (i / 16) * Math.PI * 2 - Math.PI / 2;
    points.push(
      new THREE.Vector3(
        Math.cos(angle) * radius,
        height + Math.sin(i * 0.3) * 10,
        Math.sin(angle) * radius
      )
    );
  }

  return new THREE.CatmullRomCurve3(points);
}

export function createBlimp(): THREE.CatmullRomCurve3 {
  // High overhead view, slow drift
  return new THREE.CatmullRomCurve3([
    new THREE.Vector3(-100, 200, -50),
    new THREE.Vector3(-50, 210, 0),
    new THREE.Vector3(0, 220, 20),
    new THREE.Vector3(50, 210, 10),
    new THREE.Vector3(100, 200, -20),
  ]);
}

// Get keyframe at progress point (0-1)
export function getKeyframe(
  positionPath: THREE.CatmullRomCurve3,
  lookAtPath: THREE.CatmullRomCurve3,
  progress: number
): CameraKeyframe {
  return {
    position: positionPath.getPoint(progress),
    lookAt: lookAtPath.getPoint(progress),
  };
}

// Ease function for smoother animation
export function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

// Get current phase based on progress
export function getCurrentPhase(
  progress: number
): 'approach' | 'fieldReveal' | 'fieldSwoop' | 'branding' {
  if (progress < PHASE_TIMINGS.approach.end) return 'approach';
  if (progress < PHASE_TIMINGS.fieldReveal.end) return 'fieldReveal';
  if (progress < PHASE_TIMINGS.fieldSwoop.end) return 'fieldSwoop';
  return 'branding';
}
