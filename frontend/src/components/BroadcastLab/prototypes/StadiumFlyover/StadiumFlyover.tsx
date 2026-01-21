/**
 * StadiumFlyover.tsx - Main orchestration component
 * Combines stadium, camera, effects, and UI controls into complete flyover experience
 */

import { useState, useCallback, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerformanceMonitor, AdaptiveDpr } from '@react-three/drei';
import { Stadium } from './scene/Stadium';
import type { TeamColors } from './scene/Field';
import { FlyoverCamera } from './camera/FlyoverCamera';
import { Atmosphere, type WeatherPreset } from './effects/Atmosphere';
import { Particles } from './effects/Particles';
import { PostProcessing } from './effects/PostProcessing';
import { LightBeams } from './effects/LightBeams';
import { TeamBranding } from './overlays/TeamBranding';
import { GameTitle, type NetworkStyle } from './overlays/GameTitle';
import './StadiumFlyover.css';

// All 32 NFL teams
const NFL_TEAMS: Record<string, TeamColors> = {
  cardinals: { primary: '#97233F', secondary: '#FFB612', name: 'Cardinals', abbreviation: 'ARI' },
  falcons: { primary: '#A71930', secondary: '#000000', name: 'Falcons', abbreviation: 'ATL' },
  ravens: { primary: '#241773', secondary: '#9E7C0C', name: 'Ravens', abbreviation: 'BAL' },
  bills: { primary: '#00338D', secondary: '#C60C30', name: 'Bills', abbreviation: 'BUF' },
  panthers: { primary: '#0085CA', secondary: '#101820', name: 'Panthers', abbreviation: 'CAR' },
  bears: { primary: '#0B162A', secondary: '#C83803', name: 'Bears', abbreviation: 'CHI' },
  bengals: { primary: '#FB4F14', secondary: '#000000', name: 'Bengals', abbreviation: 'CIN' },
  browns: { primary: '#311D00', secondary: '#FF3C00', name: 'Browns', abbreviation: 'CLE' },
  cowboys: { primary: '#003594', secondary: '#869397', name: 'Cowboys', abbreviation: 'DAL' },
  broncos: { primary: '#FB4F14', secondary: '#002244', name: 'Broncos', abbreviation: 'DEN' },
  lions: { primary: '#0076B6', secondary: '#B0B7BC', name: 'Lions', abbreviation: 'DET' },
  packers: { primary: '#203731', secondary: '#FFB612', name: 'Packers', abbreviation: 'GB' },
  texans: { primary: '#03202F', secondary: '#A71930', name: 'Texans', abbreviation: 'HOU' },
  colts: { primary: '#002C5F', secondary: '#A2AAAD', name: 'Colts', abbreviation: 'IND' },
  jaguars: { primary: '#006778', secondary: '#D7A22A', name: 'Jaguars', abbreviation: 'JAX' },
  chiefs: { primary: '#E31837', secondary: '#FFB81C', name: 'Chiefs', abbreviation: 'KC' },
  raiders: { primary: '#000000', secondary: '#A5ACAF', name: 'Raiders', abbreviation: 'LV' },
  chargers: { primary: '#0080C6', secondary: '#FFC20E', name: 'Chargers', abbreviation: 'LAC' },
  rams: { primary: '#003594', secondary: '#FFA300', name: 'Rams', abbreviation: 'LAR' },
  dolphins: { primary: '#008E97', secondary: '#FC4C02', name: 'Dolphins', abbreviation: 'MIA' },
  vikings: { primary: '#4F2683', secondary: '#FFC62F', name: 'Vikings', abbreviation: 'MIN' },
  patriots: { primary: '#002244', secondary: '#C60C30', name: 'Patriots', abbreviation: 'NE' },
  saints: { primary: '#D3BC8D', secondary: '#101820', name: 'Saints', abbreviation: 'NO' },
  giants: { primary: '#0B2265', secondary: '#A71930', name: 'Giants', abbreviation: 'NYG' },
  jets: { primary: '#125740', secondary: '#000000', name: 'Jets', abbreviation: 'NYJ' },
  eagles: { primary: '#004C54', secondary: '#A5ACAF', name: 'Eagles', abbreviation: 'PHI' },
  steelers: { primary: '#FFB612', secondary: '#101820', name: 'Steelers', abbreviation: 'PIT' },
  '49ers': { primary: '#AA0000', secondary: '#B3995D', name: '49ers', abbreviation: 'SF' },
  seahawks: { primary: '#002244', secondary: '#69BE28', name: 'Seahawks', abbreviation: 'SEA' },
  buccaneers: { primary: '#D50A0A', secondary: '#FF7900', name: 'Buccaneers', abbreviation: 'TB' },
  titans: { primary: '#0C2340', secondary: '#4B92DB', name: 'Titans', abbreviation: 'TEN' },
  commanders: { primary: '#5A1414', secondary: '#FFB612', name: 'Commanders', abbreviation: 'WAS' },
};

const WEATHER_OPTIONS: WeatherPreset[] = ['night', 'sunset', 'day', 'overcast'];
const NETWORK_OPTIONS: NetworkStyle[] = ['nbc', 'cbs', 'espn', 'fox'];

type AnimationPhase = 'approach' | 'fieldReveal' | 'fieldSwoop' | 'branding';

export function StadiumFlyover() {
  // State
  const [homeTeamKey, setHomeTeamKey] = useState<string>('chiefs');
  const [awayTeamKey, setAwayTeamKey] = useState<string>('bills');
  const [weather, setWeather] = useState<WeatherPreset>('night');
  const [network, setNetwork] = useState<NetworkStyle>('nbc');
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<AnimationPhase>('approach');
  const [showBranding, setShowBranding] = useState(false);
  const [confettiActive, setConfettiActive] = useState(false);
  const [quality, setQuality] = useState<'high' | 'medium' | 'low'>('high');

  const homeTeam = NFL_TEAMS[homeTeamKey];
  const awayTeam = NFL_TEAMS[awayTeamKey];

  // Handle phase changes from camera
  const handlePhaseChange = useCallback((phase: AnimationPhase) => {
    setCurrentPhase(phase);

    if (phase === 'fieldReveal') {
      setConfettiActive(true);
    }

    if (phase === 'branding') {
      setShowBranding(true);
    }
  }, []);

  // Handle animation complete
  const handleComplete = useCallback(() => {
    setIsPlaying(false);
    // Keep branding visible at end
  }, []);

  // Play button handler
  const handlePlay = useCallback(() => {
    setIsPlaying(true);
    setShowBranding(false);
    setConfettiActive(false);
    setCurrentPhase('approach');
  }, []);

  // Reset handler
  const handleReset = useCallback(() => {
    setIsPlaying(false);
    setShowBranding(false);
    setConfettiActive(false);
    setCurrentPhase('approach');
  }, []);

  // Performance monitoring
  const handleIncline = useCallback(() => {
    setQuality('high');
  }, []);

  const handleDecline = useCallback(() => {
    setQuality((prev) => (prev === 'high' ? 'medium' : 'low'));
  }, []);

  return (
    <div className="stadium-flyover">
      {/* 3D Canvas */}
      <div className="flyover-canvas">
        <Canvas
          shadows={quality !== 'low'}
          camera={{ fov: 45, near: 0.1, far: 1000, position: [0, 80, 120] }}
          dpr={quality === 'high' ? [1, 2] : quality === 'medium' ? [1, 1.5] : [0.75, 1]}
        >
          <Suspense fallback={null}>
            <PerformanceMonitor
              onIncline={handleIncline}
              onDecline={handleDecline}
              flipflops={3}
              factor={0.5}
            >
              <AdaptiveDpr pixelated />

              {/* Atmosphere (sky, fog, ambient lighting) */}
              <Atmosphere preset={weather} />

              {/* Stadium and all its parts */}
              <Stadium
                homeTeam={homeTeam}
                awayTeam={awayTeam}
                weatherPreset={weather}
              />

              {/* Volumetric light beams (night only) */}
              <LightBeams preset={weather} />

              {/* Particles (confetti + ambient) */}
              <Particles
                homeTeam={homeTeam}
                awayTeam={awayTeam}
                isActive={confettiActive}
                intensity={quality === 'low' ? 0.5 : 1}
              />

              {/* 3D team branding */}
              <TeamBranding
                homeTeam={homeTeam}
                awayTeam={awayTeam}
                isVisible={showBranding}
              />

              {/* Animated camera */}
              <FlyoverCamera
                isPlaying={isPlaying}
                duration={10}
                onPhaseChange={handlePhaseChange}
                onComplete={handleComplete}
              />

              {/* Manual orbit controls when not animating */}
              {!isPlaying && (
                <OrbitControls
                  target={[0, 0, 0]}
                  maxPolarAngle={Math.PI / 2.1}
                  minDistance={30}
                  maxDistance={400}
                />
              )}

              {/* Post-processing effects */}
              <PostProcessing
                preset={weather}
                phase={currentPhase}
                enabled={quality !== 'low'}
              />
            </PerformanceMonitor>
          </Suspense>
        </Canvas>

        {/* HTML overlay for game title */}
        <GameTitle
          homeTeam={homeTeam}
          awayTeam={awayTeam}
          network={network}
          gameTime="Sunday 4:25 PM ET"
          isVisible={showBranding}
        />
      </div>

      {/* Control Panel */}
      <div className="flyover-controls">
        <div className="control-section">
          <h3>Teams</h3>
          <div className="team-selectors">
            <div className="selector">
              <label>Away</label>
              <select
                value={awayTeamKey}
                onChange={(e) => setAwayTeamKey(e.target.value)}
                disabled={isPlaying}
              >
                {Object.entries(NFL_TEAMS).map(([key, team]) => (
                  <option key={key} value={key}>
                    {team.name}
                  </option>
                ))}
              </select>
            </div>
            <span className="at-symbol">@</span>
            <div className="selector">
              <label>Home</label>
              <select
                value={homeTeamKey}
                onChange={(e) => setHomeTeamKey(e.target.value)}
                disabled={isPlaying}
              >
                {Object.entries(NFL_TEAMS).map(([key, team]) => (
                  <option key={key} value={key}>
                    {team.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="control-section">
          <h3>Weather</h3>
          <div className="button-group">
            {WEATHER_OPTIONS.map((opt) => (
              <button
                key={opt}
                className={weather === opt ? 'active' : ''}
                onClick={() => setWeather(opt)}
                disabled={isPlaying}
              >
                {opt === 'night' && '🌙'}
                {opt === 'sunset' && '🌅'}
                {opt === 'day' && '☀️'}
                {opt === 'overcast' && '☁️'}
                {' '}{opt.charAt(0).toUpperCase() + opt.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="control-section">
          <h3>Network</h3>
          <div className="button-group">
            {NETWORK_OPTIONS.map((opt) => (
              <button
                key={opt}
                className={network === opt ? 'active' : ''}
                onClick={() => setNetwork(opt)}
                disabled={isPlaying}
              >
                {opt.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="control-section playback">
          <button
            className="play-button"
            onClick={isPlaying ? handleReset : handlePlay}
          >
            {isPlaying ? '⏹ Reset' : '▶ Play Flyover'}
          </button>

          <div className="phase-indicator">
            <span className={currentPhase === 'approach' ? 'active' : ''}>
              Approach
            </span>
            <span className={currentPhase === 'fieldReveal' ? 'active' : ''}>
              Reveal
            </span>
            <span className={currentPhase === 'fieldSwoop' ? 'active' : ''}>
              Swoop
            </span>
            <span className={currentPhase === 'branding' ? 'active' : ''}>
              Branding
            </span>
          </div>

          <div className="quality-indicator">
            Quality: {quality.charAt(0).toUpperCase() + quality.slice(1)}
          </div>
        </div>
      </div>
    </div>
  );
}
