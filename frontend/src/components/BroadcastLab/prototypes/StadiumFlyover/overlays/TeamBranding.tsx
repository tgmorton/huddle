/**
 * TeamBranding.tsx - 3D team logos that animate in
 * Displays team logos with GSAP-powered entrance animations
 */

import { useRef, useEffect } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Text } from '@react-three/drei';
import gsap from 'gsap';
import type { TeamColors } from '../scene/Field';

interface TeamBrandingProps {
  homeTeam: TeamColors;
  awayTeam: TeamColors;
  isVisible: boolean;
}

interface TeamLogoProps {
  team: TeamColors;
  position: [number, number, number];
  side: 'home' | 'away';
  isVisible: boolean;
}

function TeamLogo({ team, position, side, isVisible }: TeamLogoProps) {
  const groupRef = useRef<THREE.Group>(null);
  const materialRef = useRef<THREE.MeshStandardMaterial>(null);

  // Animate in/out
  useEffect(() => {
    if (!groupRef.current) return;

    if (isVisible) {
      // Animate in with back.out easing
      gsap.fromTo(
        groupRef.current.scale,
        { x: 0, y: 0, z: 0 },
        {
          x: 1,
          y: 1,
          z: 1,
          duration: 0.8,
          delay: side === 'home' ? 0.2 : 0,
          ease: 'back.out(1.7)',
        }
      );

      gsap.fromTo(
        groupRef.current.position,
        { y: position[1] - 10 },
        {
          y: position[1],
          duration: 0.8,
          delay: side === 'home' ? 0.2 : 0,
          ease: 'power2.out',
        }
      );
    } else {
      // Animate out
      gsap.to(groupRef.current.scale, {
        x: 0,
        y: 0,
        z: 0,
        duration: 0.3,
        ease: 'power2.in',
      });
    }
  }, [isVisible, position, side]);

  // Subtle floating animation
  useFrame((state) => {
    if (!groupRef.current || !isVisible) return;

    const time = state.clock.elapsedTime;
    groupRef.current.position.y =
      position[1] + Math.sin(time * 1.5 + (side === 'home' ? 0 : Math.PI)) * 0.5;
    groupRef.current.rotation.y = Math.sin(time * 0.5) * 0.1;
  });

  return (
    <group ref={groupRef} position={position} scale={0}>
      {/* Logo background (team-colored circle) */}
      <mesh>
        <circleGeometry args={[8, 32]} />
        <meshStandardMaterial
          ref={materialRef}
          color={team.primary}
          metalness={0.3}
          roughness={0.7}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Team abbreviation as 3D text */}
      <Text
        position={[0, 0, 0.5]}
        fontSize={5}
        color={team.secondary}
        anchorX="center"
        anchorY="middle"
        outlineWidth={0.2}
        outlineColor="#000000"
      >
        {team.abbreviation}
      </Text>

      {/* Glow effect */}
      <mesh position={[0, 0, -0.5]}>
        <circleGeometry args={[10, 32]} />
        <meshBasicMaterial
          color={team.primary}
          transparent
          opacity={0.3}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

export function TeamBranding({
  homeTeam,
  awayTeam,
  isVisible,
}: TeamBrandingProps) {
  return (
    <group>
      {/* Away team logo (left side) */}
      <TeamLogo
        team={awayTeam}
        position={[-30, 40, 0]}
        side="away"
        isVisible={isVisible}
      />

      {/* VS indicator */}
      {isVisible && (
        <group position={[0, 35, 0]}>
          <Text
            fontSize={4}
            color="#ffffff"
            anchorX="center"
            anchorY="middle"
            outlineWidth={0.15}
            outlineColor="#000000"
          >
            VS
          </Text>
        </group>
      )}

      {/* Home team logo (right side) */}
      <TeamLogo
        team={homeTeam}
        position={[30, 40, 0]}
        side="home"
        isVisible={isVisible}
      />
    </group>
  );
}
