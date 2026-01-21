/**
 * Scoreboard.tsx - End zone scoreboards
 * Large video board displays at each end zone
 */

import { useRef } from 'react';
import * as THREE from 'three';
import { Html } from '@react-three/drei';
import type { TeamColors } from './Field';

interface ScoreboardProps {
  homeTeam: TeamColors;
  awayTeam: TeamColors;
  homeScore?: number;
  awayScore?: number;
  quarter?: number;
  timeRemaining?: string;
  position: 'east' | 'west';
}

const BOARD_WIDTH = 40;
const BOARD_HEIGHT = 20;
const BOARD_Y = 45;

export function Scoreboard({
  homeTeam,
  awayTeam,
  homeScore = 0,
  awayScore = 0,
  quarter = 1,
  timeRemaining = '15:00',
  position,
}: ScoreboardProps) {
  const groupRef = useRef<THREE.Group>(null);

  const xPos = position === 'east' ? 80 : -80;
  const rotation = position === 'east' ? Math.PI : 0;

  return (
    <group ref={groupRef} position={[xPos, BOARD_Y, 0]} rotation={[0, rotation, 0]}>
      {/* Scoreboard frame */}
      <mesh>
        <boxGeometry args={[BOARD_WIDTH + 4, BOARD_HEIGHT + 4, 3]} />
        <meshStandardMaterial color="#1a1a1a" metalness={0.5} roughness={0.5} />
      </mesh>

      {/* LED screen backing */}
      <mesh position={[0, 0, 1.6]}>
        <planeGeometry args={[BOARD_WIDTH, BOARD_HEIGHT]} />
        <meshStandardMaterial color="#000000" />
      </mesh>

      {/* Screen content using HTML overlay */}
      <Html
        position={[0, 0, 2]}
        transform
        occlude
        style={{
          width: `${BOARD_WIDTH * 10}px`,
          height: `${BOARD_HEIGHT * 10}px`,
          background: 'linear-gradient(180deg, #0a0a0a 0%, #1a1a1a 100%)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'Arial, sans-serif',
          color: 'white',
          padding: '20px',
          boxSizing: 'border-box',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-around',
            width: '100%',
            marginBottom: '20px',
          }}
        >
          {/* Away team */}
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                fontSize: '24px',
                fontWeight: 'bold',
                color: awayTeam.primary,
                textShadow: '2px 2px 4px rgba(0,0,0,0.5)',
              }}
            >
              {awayTeam.abbreviation}
            </div>
            <div
              style={{
                fontSize: '48px',
                fontWeight: 'bold',
                color: '#ffffff',
              }}
            >
              {awayScore}
            </div>
          </div>

          {/* Divider */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <div style={{ fontSize: '16px', color: '#888' }}>Q{quarter}</div>
            <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{timeRemaining}</div>
          </div>

          {/* Home team */}
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                fontSize: '24px',
                fontWeight: 'bold',
                color: homeTeam.primary,
                textShadow: '2px 2px 4px rgba(0,0,0,0.5)',
              }}
            >
              {homeTeam.abbreviation}
            </div>
            <div
              style={{
                fontSize: '48px',
                fontWeight: 'bold',
                color: '#ffffff',
              }}
            >
              {homeScore}
            </div>
          </div>
        </div>
      </Html>

      {/* Support structure */}
      <mesh position={[0, -BOARD_HEIGHT / 2 - 10, 0]}>
        <cylinderGeometry args={[2, 3, 20, 8]} />
        <meshStandardMaterial color="#333333" metalness={0.4} roughness={0.6} />
      </mesh>
    </group>
  );
}
