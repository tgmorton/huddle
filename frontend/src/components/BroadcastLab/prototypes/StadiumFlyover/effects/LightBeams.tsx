/**
 * LightBeams.tsx - Volumetric stadium lights for night games
 * Creates visible light cones from stadium lights
 */

import { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import type { WeatherPreset } from './Atmosphere';

interface LightBeamsProps {
  preset: WeatherPreset;
  intensity?: number;
}

// Light tower positions (matching Lights.tsx)
const TOWER_POSITIONS: [number, number, number][] = [
  [-70, 50, -45],
  [70, 50, -45],
  [-70, 50, 45],
  [70, 50, 45],
];

function LightBeam({
  position,
  targetPosition,
  intensity,
}: {
  position: [number, number, number];
  targetPosition: [number, number, number];
  intensity: number;
}) {
  const meshRef = useRef<THREE.Mesh>(null);

  // Calculate beam direction and length
  const beamData = useMemo(() => {
    const start = new THREE.Vector3(...position);
    const end = new THREE.Vector3(...targetPosition);
    const direction = end.clone().sub(start);
    const length = direction.length();
    const midpoint = start.clone().add(direction.multiplyScalar(0.5));

    // Calculate rotation to point beam
    const quaternion = new THREE.Quaternion();
    const up = new THREE.Vector3(0, 1, 0);
    direction.normalize();
    quaternion.setFromUnitVectors(up, direction);

    return { midpoint, length, quaternion };
  }, [position, targetPosition]);

  // Animate beam opacity
  useFrame((state) => {
    if (!meshRef.current) return;

    const time = state.clock.elapsedTime;
    // Subtle flickering
    const flicker = 0.95 + Math.sin(time * 10) * 0.05;
    (meshRef.current.material as THREE.MeshBasicMaterial).opacity =
      intensity * 0.15 * flicker;
  });

  return (
    <mesh
      ref={meshRef}
      position={beamData.midpoint}
      quaternion={beamData.quaternion}
    >
      <coneGeometry args={[15, beamData.length, 16, 1, true]} />
      <meshBasicMaterial
        color="#ffffee"
        transparent
        opacity={intensity * 0.15}
        side={THREE.DoubleSide}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

export function LightBeams({ preset, intensity = 1 }: LightBeamsProps) {
  // Only show light beams at night
  if (preset !== 'night') return null;

  // Target center of field
  const targetPosition: [number, number, number] = [0, 0, 0];

  return (
    <group>
      {TOWER_POSITIONS.map((pos, i) => (
        <LightBeam
          key={i}
          position={pos}
          targetPosition={targetPosition}
          intensity={intensity}
        />
      ))}

      {/* Central glow on field from combined lights */}
      <mesh position={[0, 0.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[80, 32]} />
        <meshBasicMaterial
          color="#ffffdd"
          transparent
          opacity={0.05}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}
