/**
 * Field.tsx - Football field with procedural yard lines, end zones, and team branding
 * Uses canvas texture for crisp graphics at any distance
 */

import { useMemo, useRef } from 'react';
import * as THREE from 'three';

interface TeamColors {
  primary: string;
  secondary: string;
  name: string;
  abbreviation: string;
}

interface FieldProps {
  homeTeam: TeamColors;
  awayTeam: TeamColors;
}

// Field dimensions in yards (scaled to Three.js units - 1 unit = 1 yard)
const FIELD_LENGTH = 120; // 100 yards + 2x10 yard end zones
const FIELD_WIDTH = 53.33;

function createFieldTexture(
  homeTeam: TeamColors,
  awayTeam: TeamColors
): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d')!;

  // High resolution for crisp lines
  const scale = 20;
  canvas.width = FIELD_LENGTH * scale;
  canvas.height = FIELD_WIDTH * scale;

  // Green field
  ctx.fillStyle = '#2d5016';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Add subtle grass stripes (alternating shades)
  for (let i = 0; i < 12; i++) {
    if (i % 2 === 0) {
      ctx.fillStyle = '#2a4a14';
      ctx.fillRect(i * 10 * scale, 0, 10 * scale, canvas.height);
    }
  }

  // End zones
  // Away team end zone (left, 0-10 yards)
  ctx.fillStyle = awayTeam.primary;
  ctx.fillRect(0, 0, 10 * scale, canvas.height);

  // Home team end zone (right, 110-120 yards)
  ctx.fillStyle = homeTeam.primary;
  ctx.fillRect(110 * scale, 0, 10 * scale, canvas.height);

  // White lines
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 0.15 * scale;

  // End zone lines (goal lines at 10 and 110)
  ctx.beginPath();
  ctx.moveTo(10 * scale, 0);
  ctx.lineTo(10 * scale, canvas.height);
  ctx.moveTo(110 * scale, 0);
  ctx.lineTo(110 * scale, canvas.height);
  ctx.stroke();

  // Yard lines every 5 yards
  for (let yard = 15; yard <= 105; yard += 5) {
    ctx.beginPath();
    ctx.moveTo(yard * scale, 0);
    ctx.lineTo(yard * scale, canvas.height);
    ctx.stroke();
  }

  // Hash marks (simplified - just the major ones)
  ctx.lineWidth = 0.1 * scale;
  const hashY1 = (FIELD_WIDTH / 2 - 9.25) * scale;
  const hashY2 = (FIELD_WIDTH / 2 + 9.25) * scale;

  for (let yard = 11; yard <= 109; yard++) {
    if (yard % 5 !== 0) {
      // Short hash marks
      ctx.beginPath();
      ctx.moveTo(yard * scale, hashY1 - 0.5 * scale);
      ctx.lineTo(yard * scale, hashY1 + 0.5 * scale);
      ctx.moveTo(yard * scale, hashY2 - 0.5 * scale);
      ctx.lineTo(yard * scale, hashY2 + 0.5 * scale);
      ctx.stroke();
    }
  }

  // Yard numbers
  ctx.fillStyle = '#ffffff';
  ctx.font = `bold ${4 * scale}px Arial`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  const numbers = [10, 20, 30, 40, 50, 40, 30, 20, 10];
  const positions = [20, 30, 40, 50, 60, 70, 80, 90, 100];

  positions.forEach((pos, i) => {
    const num = numbers[i].toString();
    // Top numbers (rotated)
    ctx.save();
    ctx.translate(pos * scale, 6 * scale);
    ctx.rotate(Math.PI);
    ctx.fillText(num, 0, 0);
    ctx.restore();

    // Bottom numbers
    ctx.fillText(num, pos * scale, (FIELD_WIDTH - 6) * scale);
  });

  // End zone text
  ctx.font = `bold ${6 * scale}px Arial`;
  ctx.fillStyle = awayTeam.secondary;
  ctx.save();
  ctx.translate(5 * scale, FIELD_WIDTH / 2 * scale);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(awayTeam.name.toUpperCase(), 0, 0);
  ctx.restore();

  ctx.fillStyle = homeTeam.secondary;
  ctx.save();
  ctx.translate(115 * scale, FIELD_WIDTH / 2 * scale);
  ctx.rotate(Math.PI / 2);
  ctx.fillText(homeTeam.name.toUpperCase(), 0, 0);
  ctx.restore();

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.anisotropy = 16;

  return texture;
}

export function Field({ homeTeam, awayTeam }: FieldProps) {
  const meshRef = useRef<THREE.Mesh>(null);

  const texture = useMemo(
    () => createFieldTexture(homeTeam, awayTeam),
    [homeTeam, awayTeam]
  );

  return (
    <mesh
      ref={meshRef}
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, 0, 0]}
      receiveShadow
    >
      <planeGeometry args={[FIELD_LENGTH, FIELD_WIDTH]} />
      <meshStandardMaterial
        map={texture}
        roughness={0.8}
        metalness={0.1}
      />
    </mesh>
  );
}

export type { TeamColors };
