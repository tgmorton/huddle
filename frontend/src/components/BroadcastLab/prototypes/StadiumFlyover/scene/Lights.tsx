/**
 * Lights.tsx - Stadium light towers
 * Four corner towers with banks of lights that illuminate the field
 */

import { useMemo, useRef } from 'react';
import * as THREE from 'three';

interface LightsProps {
  weatherPreset: 'night' | 'sunset' | 'day' | 'overcast';
  intensity?: number;
}

// Light tower positions (corners of stadium)
const TOWER_POSITIONS: [number, number, number][] = [
  [-70, 0, -45],
  [70, 0, -45],
  [-70, 0, 45],
  [70, 0, 45],
];

const TOWER_HEIGHT = 50;
const LIGHT_COUNT = 12; // Per tower

function LightTower({ position, intensity }: { position: [number, number, number]; intensity: number }) {
  const lightsRef = useRef<THREE.Group>(null);

  // Calculate light target (center of field)
  const targetPosition = useMemo(() => new THREE.Vector3(0, 0, 0), []);

  return (
    <group position={position}>
      {/* Tower structure */}
      <mesh position={[0, TOWER_HEIGHT / 2, 0]}>
        <cylinderGeometry args={[1.5, 2, TOWER_HEIGHT, 8]} />
        <meshStandardMaterial color="#333333" metalness={0.5} roughness={0.5} />
      </mesh>

      {/* Cross beam at top */}
      <mesh position={[0, TOWER_HEIGHT - 2, 0]} rotation={[0, Math.atan2(position[2], position[0]), 0]}>
        <boxGeometry args={[16, 2, 3]} />
        <meshStandardMaterial color="#444444" metalness={0.5} roughness={0.5} />
      </mesh>

      {/* Light bank housing */}
      <group ref={lightsRef} position={[0, TOWER_HEIGHT - 1, 0]}>
        {Array.from({ length: LIGHT_COUNT }).map((_, i) => {
          const row = Math.floor(i / 4);
          const col = i % 4;
          const x = (col - 1.5) * 3;
          const y = (row - 1) * 1.5;

          return (
            <group key={i} position={[x, y, 0]}>
              {/* Light housing */}
              <mesh>
                <boxGeometry args={[2.5, 1.2, 1]} />
                <meshStandardMaterial color="#222222" metalness={0.6} roughness={0.4} />
              </mesh>

              {/* Light face (emissive) */}
              <mesh position={[0, 0, 0.5]}>
                <planeGeometry args={[2.2, 1]} />
                <meshStandardMaterial
                  color="#ffffff"
                  emissive="#ffffee"
                  emissiveIntensity={intensity * 2}
                />
              </mesh>
            </group>
          );
        })}
      </group>

      {/* SpotLight pointing at field */}
      <spotLight
        position={[0, TOWER_HEIGHT, 0]}
        target-position={targetPosition}
        intensity={intensity * 100}
        angle={Math.PI / 4}
        penumbra={0.5}
        decay={1.5}
        distance={200}
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-bias={-0.0001}
      />
    </group>
  );
}

export function Lights({ weatherPreset, intensity = 1 }: LightsProps) {
  // Adjust intensity based on weather
  const effectiveIntensity = useMemo(() => {
    switch (weatherPreset) {
      case 'night':
        return intensity * 1.5;
      case 'sunset':
        return intensity * 0.8;
      case 'overcast':
        return intensity * 0.6;
      case 'day':
      default:
        return intensity * 0.3;
    }
  }, [weatherPreset, intensity]);

  return (
    <group>
      {TOWER_POSITIONS.map((pos, i) => (
        <LightTower key={i} position={pos} intensity={effectiveIntensity} />
      ))}

      {/* Ambient light for base illumination */}
      <ambientLight
        intensity={weatherPreset === 'night' ? 0.1 : weatherPreset === 'day' ? 0.6 : 0.3}
      />

      {/* Directional light (sun/moon) */}
      <directionalLight
        position={[
          weatherPreset === 'sunset' ? -100 : 50,
          weatherPreset === 'sunset' ? 20 : 80,
          30,
        ]}
        intensity={weatherPreset === 'night' ? 0.1 : weatherPreset === 'sunset' ? 0.8 : 1}
        color={weatherPreset === 'sunset' ? '#ffaa55' : '#ffffff'}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-far={250}
        shadow-camera-left={-100}
        shadow-camera-right={100}
        shadow-camera-top={100}
        shadow-camera-bottom={-100}
      />
    </group>
  );
}
