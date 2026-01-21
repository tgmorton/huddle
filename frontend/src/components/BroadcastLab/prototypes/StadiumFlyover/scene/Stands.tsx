/**
 * Stands.tsx - Stadium seating bowl with instanced crowd
 * Uses InstancedMesh for 30k+ crowd members with team color distribution
 */

import { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import type { TeamColors } from './Field';

interface StandsProps {
  homeTeam: TeamColors;
  awayTeam: TeamColors;
  crowdDensity?: number; // 0-1, affects number of instances
}

// Stadium dimensions
const FIELD_LENGTH = 120;
const FIELD_WIDTH = 53.33;
const STAND_ROWS = 40;
const STAND_HEIGHT = 35;
const STAND_DEPTH = 60;

// Crowd simulation
const MAX_CROWD = 35000;

function createCrowdPositions(
  density: number,
  homeColor: THREE.Color,
  awayColor: THREE.Color
): { matrices: THREE.Matrix4[]; colors: THREE.Color[] } {
  const matrices: THREE.Matrix4[] = [];
  const colors: THREE.Color[] = [];
  const count = Math.floor(MAX_CROWD * density);

  const neutralColors = [
    new THREE.Color('#333333'),
    new THREE.Color('#555555'),
    new THREE.Color('#777777'),
  ];

  // Distribute crowd around the stadium bowl
  const sections = [
    // North sideline (long side)
    { start: [-55, 8, -35], end: [55, STAND_HEIGHT, -35 - STAND_DEPTH], weight: 0.3 },
    // South sideline (long side)
    { start: [-55, 8, 35], end: [55, STAND_HEIGHT, 35 + STAND_DEPTH], weight: 0.3 },
    // East end zone
    { start: [60, 8, -30], end: [60 + STAND_DEPTH, STAND_HEIGHT, 30], weight: 0.2 },
    // West end zone
    { start: [-60, 8, -30], end: [-60 - STAND_DEPTH, STAND_HEIGHT, 30], weight: 0.2 },
  ];

  let placed = 0;
  const matrix = new THREE.Matrix4();
  const position = new THREE.Vector3();
  const scale = new THREE.Vector3();
  const quaternion = new THREE.Quaternion();

  sections.forEach((section) => {
    const sectionCount = Math.floor(count * section.weight);

    for (let i = 0; i < sectionCount && placed < count; i++) {
      // Random position within section bounds
      const t = Math.random();
      const u = Math.random();

      position.x = THREE.MathUtils.lerp(section.start[0], section.end[0], t);
      position.z = THREE.MathUtils.lerp(section.start[2], section.end[2], u);

      // Height follows a slope from front to back
      const depthProgress =
        Math.abs(position.z) > 35
          ? u // Sidelines
          : t; // End zones
      position.y = THREE.MathUtils.lerp(section.start[1], section.end[1], depthProgress);

      // Random variations
      position.x += (Math.random() - 0.5) * 1.5;
      position.y += (Math.random() - 0.5) * 0.5;
      position.z += (Math.random() - 0.5) * 1.5;

      // Scale variation for natural look
      const s = 0.4 + Math.random() * 0.3;
      scale.set(s, s * (0.8 + Math.random() * 0.4), s);

      // Random rotation (slight variation)
      quaternion.setFromEuler(
        new THREE.Euler(0, Math.random() * Math.PI * 2, 0)
      );

      matrix.compose(position, quaternion, scale);
      matrices.push(matrix.clone());

      // Color distribution: 40% home, 30% away, 30% neutral
      const colorRoll = Math.random();
      if (colorRoll < 0.4) {
        colors.push(homeColor.clone());
      } else if (colorRoll < 0.7) {
        colors.push(awayColor.clone());
      } else {
        colors.push(neutralColors[Math.floor(Math.random() * neutralColors.length)].clone());
      }

      placed++;
    }
  });

  return { matrices, colors };
}

export function Stands({ homeTeam, awayTeam, crowdDensity = 0.8 }: StandsProps) {
  const crowdRef = useRef<THREE.InstancedMesh>(null);

  // Generate crowd data
  const { matrices, colors } = useMemo(() => {
    const homeColor = new THREE.Color(homeTeam.primary);
    const awayColor = new THREE.Color(awayTeam.primary);
    return createCrowdPositions(crowdDensity, homeColor, awayColor);
  }, [homeTeam, awayTeam, crowdDensity]);

  // Set up instanced mesh
  useMemo(() => {
    if (!crowdRef.current) return;

    matrices.forEach((matrix, i) => {
      crowdRef.current!.setMatrixAt(i, matrix);
      crowdRef.current!.setColorAt(i, colors[i]);
    });

    crowdRef.current.instanceMatrix.needsUpdate = true;
    if (crowdRef.current.instanceColor) {
      crowdRef.current.instanceColor.needsUpdate = true;
    }
  }, [matrices, colors]);

  // Subtle crowd animation (wave effect)
  useFrame((state) => {
    if (!crowdRef.current) return;

    const time = state.clock.elapsedTime;
    const matrix = new THREE.Matrix4();
    const position = new THREE.Vector3();
    const quaternion = new THREE.Quaternion();
    const scale = new THREE.Vector3();

    // Only animate a subset for performance
    const animateCount = Math.min(1000, matrices.length);
    for (let i = 0; i < animateCount; i++) {
      crowdRef.current.getMatrixAt(i, matrix);
      matrix.decompose(position, quaternion, scale);

      // Subtle bounce based on position (wave effect)
      const wave = Math.sin(time * 2 + position.x * 0.1 + position.z * 0.1) * 0.1;
      position.y += wave * 0.05;

      matrix.compose(position, quaternion, scale);
      crowdRef.current.setMatrixAt(i, matrix);
    }

    crowdRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <group>
      {/* Stadium structure - simplified bowl shape */}
      <StadiumBowl />

      {/* Instanced crowd */}
      <instancedMesh
        ref={crowdRef}
        args={[undefined, undefined, matrices.length]}
        castShadow
        receiveShadow
      >
        <capsuleGeometry args={[0.3, 0.8, 4, 8]} />
        <meshStandardMaterial roughness={0.9} metalness={0.1} />
      </instancedMesh>
    </group>
  );
}

function StadiumBowl() {
  // Build stadium from extruded shapes
  const bowlGeometry = useMemo(() => {
    const shape = new THREE.Shape();

    // Create a cross-section of stadium seating (stepped profile)
    shape.moveTo(0, 0);
    for (let i = 0; i < STAND_ROWS; i++) {
      const x = i * (STAND_DEPTH / STAND_ROWS);
      const y = i * (STAND_HEIGHT / STAND_ROWS);
      shape.lineTo(x, y);
      shape.lineTo(x + STAND_DEPTH / STAND_ROWS * 0.8, y);
    }
    shape.lineTo(STAND_DEPTH, STAND_HEIGHT);
    shape.lineTo(STAND_DEPTH, 0);
    shape.lineTo(0, 0);

    return shape;
  }, []);

  return (
    <group>
      {/* North stands */}
      <mesh position={[0, 0, -FIELD_WIDTH / 2 - 8]} rotation={[0, 0, 0]}>
        <extrudeGeometry
          args={[
            bowlGeometry,
            {
              depth: FIELD_LENGTH - 10,
              bevelEnabled: false,
            },
          ]}
        />
        <meshStandardMaterial color="#404040" roughness={0.9} />
      </mesh>

      {/* South stands */}
      <mesh position={[0, 0, FIELD_WIDTH / 2 + 8 + STAND_DEPTH]} rotation={[0, Math.PI, 0]}>
        <extrudeGeometry
          args={[
            bowlGeometry,
            {
              depth: FIELD_LENGTH - 10,
              bevelEnabled: false,
            },
          ]}
        />
        <meshStandardMaterial color="#404040" roughness={0.9} />
      </mesh>

      {/* East stands (curved end zone) */}
      <mesh position={[FIELD_LENGTH / 2 + 5, 0, 0]} rotation={[0, -Math.PI / 2, 0]}>
        <extrudeGeometry
          args={[
            bowlGeometry,
            {
              depth: FIELD_WIDTH + 16,
              bevelEnabled: false,
            },
          ]}
        />
        <meshStandardMaterial color="#383838" roughness={0.9} />
      </mesh>

      {/* West stands (curved end zone) */}
      <mesh position={[-FIELD_LENGTH / 2 - 5 - STAND_DEPTH, 0, 0]} rotation={[0, Math.PI / 2, 0]}>
        <extrudeGeometry
          args={[
            bowlGeometry,
            {
              depth: FIELD_WIDTH + 16,
              bevelEnabled: false,
            },
          ]}
        />
        <meshStandardMaterial color="#383838" roughness={0.9} />
      </mesh>

      {/* Concourse floor (ring around field) */}
      <mesh position={[0, 0.1, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[50, 55, 64]} />
        <meshStandardMaterial color="#555555" roughness={0.9} />
      </mesh>
    </group>
  );
}
