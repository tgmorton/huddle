/**
 * Atmosphere.tsx - Sky, fog, and lighting presets
 * Creates the mood for different weather conditions
 */

import { useMemo } from 'react';
import * as THREE from 'three';
import { Sky, Stars } from '@react-three/drei';

export type WeatherPreset = 'night' | 'sunset' | 'day' | 'overcast';

interface AtmosphereProps {
  preset: WeatherPreset;
}

interface PresetConfig {
  fogColor: string;
  fogNear: number;
  fogFar: number;
  skyParams?: {
    distance: number;
    sunPosition: [number, number, number];
    inclination: number;
    azimuth: number;
    turbidity: number;
    rayleigh: number;
  };
  showStars: boolean;
  backgroundColor: string;
}

const PRESETS: Record<WeatherPreset, PresetConfig> = {
  night: {
    fogColor: '#0a0a15',
    fogNear: 100,
    fogFar: 400,
    showStars: true,
    backgroundColor: '#050510',
  },
  sunset: {
    fogColor: '#4a2020',
    fogNear: 150,
    fogFar: 500,
    skyParams: {
      distance: 4500,
      sunPosition: [-100, 10, -50],
      inclination: 0.49,
      azimuth: 0.25,
      turbidity: 10,
      rayleigh: 3,
    },
    showStars: false,
    backgroundColor: '#2a1515',
  },
  day: {
    fogColor: '#87ceeb',
    fogNear: 200,
    fogFar: 600,
    skyParams: {
      distance: 4500,
      sunPosition: [50, 100, 30],
      inclination: 0.6,
      azimuth: 0.25,
      turbidity: 2,
      rayleigh: 1,
    },
    showStars: false,
    backgroundColor: '#87ceeb',
  },
  overcast: {
    fogColor: '#8899aa',
    fogNear: 80,
    fogFar: 350,
    showStars: false,
    backgroundColor: '#667788',
  },
};

export function Atmosphere({ preset }: AtmosphereProps) {
  const config = PRESETS[preset];

  // Create fog
  const fog = useMemo(() => {
    return new THREE.Fog(config.fogColor, config.fogNear, config.fogFar);
  }, [config.fogColor, config.fogNear, config.fogFar]);

  return (
    <>
      {/* Background color for non-sky presets */}
      <color attach="background" args={[config.backgroundColor]} />

      {/* Fog */}
      <primitive object={fog} attach="fog" />

      {/* Sky for day/sunset */}
      {config.skyParams && (
        <Sky
          distance={config.skyParams.distance}
          sunPosition={config.skyParams.sunPosition}
          inclination={config.skyParams.inclination}
          azimuth={config.skyParams.azimuth}
          turbidity={config.skyParams.turbidity}
          rayleigh={config.skyParams.rayleigh}
        />
      )}

      {/* Stars for night games */}
      {config.showStars && (
        <Stars
          radius={300}
          depth={100}
          count={3000}
          factor={6}
          saturation={0}
          fade
          speed={0.5}
        />
      )}

      {/* Hemisphere light for ambient fill */}
      <hemisphereLight
        color={preset === 'sunset' ? '#ffaa66' : '#ffffff'}
        groundColor={preset === 'night' ? '#111122' : '#444444'}
        intensity={preset === 'night' ? 0.2 : preset === 'sunset' ? 0.4 : 0.6}
      />
    </>
  );
}
