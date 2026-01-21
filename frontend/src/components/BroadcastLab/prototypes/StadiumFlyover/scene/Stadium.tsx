/**
 * Stadium.tsx - Complete stadium composition
 * Combines field, stands, lights, and scoreboards into cohesive scene
 */

import { Field, type TeamColors } from './Field';
import { Stands } from './Stands';
import { Lights } from './Lights';
import { Scoreboard } from './Scoreboard';

export interface StadiumProps {
  homeTeam: TeamColors;
  awayTeam: TeamColors;
  weatherPreset: 'night' | 'sunset' | 'day' | 'overcast';
  homeScore?: number;
  awayScore?: number;
  quarter?: number;
  timeRemaining?: string;
}

export function Stadium({
  homeTeam,
  awayTeam,
  weatherPreset,
  homeScore = 0,
  awayScore = 0,
  quarter = 1,
  timeRemaining = '15:00',
}: StadiumProps) {
  return (
    <group>
      {/* Field with yard lines and team end zones */}
      <Field homeTeam={homeTeam} awayTeam={awayTeam} />

      {/* Seating bowl and crowd */}
      <Stands homeTeam={homeTeam} awayTeam={awayTeam} crowdDensity={0.8} />

      {/* Stadium lighting */}
      <Lights weatherPreset={weatherPreset} intensity={1} />

      {/* Scoreboards at each end */}
      <Scoreboard
        homeTeam={homeTeam}
        awayTeam={awayTeam}
        homeScore={homeScore}
        awayScore={awayScore}
        quarter={quarter}
        timeRemaining={timeRemaining}
        position="east"
      />
      <Scoreboard
        homeTeam={homeTeam}
        awayTeam={awayTeam}
        homeScore={homeScore}
        awayScore={awayScore}
        quarter={quarter}
        timeRemaining={timeRemaining}
        position="west"
      />

      {/* Ground plane (parking lot / surrounding area) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.5, 0]} receiveShadow>
        <planeGeometry args={[500, 500]} />
        <meshStandardMaterial color="#1a1a1a" roughness={0.95} />
      </mesh>
    </group>
  );
}

export type { TeamColors };
