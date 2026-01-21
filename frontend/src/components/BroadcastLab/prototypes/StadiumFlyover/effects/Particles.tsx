/**
 * Particles.tsx - Confetti and atmospheric particles
 * Team-colored confetti during reveal, plus ambient particles
 */

import { useRef, useMemo, useEffect } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import type { TeamColors } from '../scene/Field';

interface ParticlesProps {
  homeTeam: TeamColors;
  awayTeam: TeamColors;
  isActive: boolean;
  intensity?: number;
}

const CONFETTI_COUNT = 2000;
const AMBIENT_PARTICLE_COUNT = 500;

export function Particles({
  homeTeam,
  awayTeam,
  isActive,
  intensity = 1,
}: ParticlesProps) {
  const confettiRef = useRef<THREE.Points>(null);
  const ambientRef = useRef<THREE.Points>(null);

  // Create confetti geometry with team colors
  const confettiData = useMemo(() => {
    const count = Math.floor(CONFETTI_COUNT * intensity);
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const velocities = new Float32Array(count * 3);

    const homeColor = new THREE.Color(homeTeam.primary);
    const awayColor = new THREE.Color(awayTeam.primary);
    const goldColor = new THREE.Color('#ffd700');
    const silverColor = new THREE.Color('#c0c0c0');

    for (let i = 0; i < count; i++) {
      const i3 = i * 3;

      // Random position above the field
      positions[i3] = (Math.random() - 0.5) * 200;
      positions[i3 + 1] = 60 + Math.random() * 80;
      positions[i3 + 2] = (Math.random() - 0.5) * 100;

      // Random velocities for falling motion
      velocities[i3] = (Math.random() - 0.5) * 2;
      velocities[i3 + 1] = -5 - Math.random() * 10;
      velocities[i3 + 2] = (Math.random() - 0.5) * 2;

      // Color distribution: 35% home, 35% away, 15% gold, 15% silver
      const colorRoll = Math.random();
      let color: THREE.Color;
      if (colorRoll < 0.35) {
        color = homeColor;
      } else if (colorRoll < 0.7) {
        color = awayColor;
      } else if (colorRoll < 0.85) {
        color = goldColor;
      } else {
        color = silverColor;
      }

      colors[i3] = color.r;
      colors[i3 + 1] = color.g;
      colors[i3 + 2] = color.b;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    return { geometry, velocities, count };
  }, [homeTeam, awayTeam, intensity]);

  // Create ambient particle geometry (dust/atmosphere)
  const ambientGeometry = useMemo(() => {
    const positions = new Float32Array(AMBIENT_PARTICLE_COUNT * 3);
    const colors = new Float32Array(AMBIENT_PARTICLE_COUNT * 3);

    for (let i = 0; i < AMBIENT_PARTICLE_COUNT; i++) {
      const i3 = i * 3;

      positions[i3] = (Math.random() - 0.5) * 400;
      positions[i3 + 1] = Math.random() * 150;
      positions[i3 + 2] = (Math.random() - 0.5) * 300;

      const brightness = 0.5 + Math.random() * 0.5;
      colors[i3] = brightness;
      colors[i3 + 1] = brightness;
      colors[i3 + 2] = brightness;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    return geometry;
  }, []);

  // Assign geometry to refs when they mount
  useEffect(() => {
    if (confettiRef.current) {
      confettiRef.current.geometry = confettiData.geometry;
    }
  }, [confettiData.geometry]);

  useEffect(() => {
    if (ambientRef.current) {
      ambientRef.current.geometry = ambientGeometry;
    }
  }, [ambientGeometry]);

  // Animate confetti
  useFrame((state, delta) => {
    if (!confettiRef.current || !isActive) return;

    const positions = confettiRef.current.geometry.attributes.position
      .array as Float32Array;

    for (let i = 0; i < confettiData.count; i++) {
      const i3 = i * 3;

      positions[i3] += confettiData.velocities[i3] * delta * 10;
      positions[i3 + 1] += confettiData.velocities[i3 + 1] * delta * 10;
      positions[i3 + 2] += confettiData.velocities[i3 + 2] * delta * 10;

      positions[i3] += Math.sin(state.clock.elapsedTime * 2 + i) * delta * 2;
      positions[i3 + 2] += Math.cos(state.clock.elapsedTime * 2 + i) * delta * 2;

      if (positions[i3 + 1] < -10) {
        positions[i3 + 1] = 80 + Math.random() * 40;
        positions[i3] = (Math.random() - 0.5) * 200;
        positions[i3 + 2] = (Math.random() - 0.5) * 100;
      }
    }

    confettiRef.current.geometry.attributes.position.needsUpdate = true;
  });

  // Animate ambient particles (slow drift)
  useFrame((state) => {
    if (!ambientRef.current) return;

    const positions = ambientRef.current.geometry.attributes.position
      .array as Float32Array;
    const time = state.clock.elapsedTime;

    for (let i = 0; i < AMBIENT_PARTICLE_COUNT; i++) {
      const i3 = i * 3;

      positions[i3] += Math.sin(time * 0.1 + i * 0.1) * 0.01;
      positions[i3 + 1] += Math.cos(time * 0.15 + i * 0.1) * 0.005;
      positions[i3 + 2] += Math.sin(time * 0.12 + i * 0.1) * 0.01;
    }

    ambientRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <group>
      {/* Confetti (only when active) */}
      {isActive && (
        <points ref={confettiRef}>
          <bufferGeometry />
          <pointsMaterial
            size={1.5}
            vertexColors
            transparent
            opacity={0.9}
            sizeAttenuation
          />
        </points>
      )}

      {/* Ambient dust particles (always visible) */}
      <points ref={ambientRef}>
        <bufferGeometry />
        <pointsMaterial
          size={0.5}
          vertexColors
          transparent
          opacity={0.3}
          sizeAttenuation
        />
      </points>
    </group>
  );
}
