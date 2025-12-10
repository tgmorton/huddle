/**
 * Route running simulation screen - 1 WR vs 1 DB
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { RoutesCanvas } from './RoutesCanvas';
import './RoutesScreen.css';

const API_BASE_URL = 'http://localhost:8000/api/v1';

interface Vec2 {
  x: number;
  y: number;
}

interface RouteWaypoint {
  position: Vec2;
  arrival_tick: number;
  is_break: boolean;
}

interface Receiver {
  id: string;
  position: Vec2;
  route: RouteWaypoint[];
  current_waypoint_idx: number;
  animation: string;
  facing: Vec2;
}

interface DefensiveBack {
  id: string;
  position: Vec2;
  coverage_type: string;
  animation: string;
  facing: Vec2;
  reaction_delay: number;
}

interface RouteSimState {
  receiver: Receiver;
  defender: DefensiveBack;
  separation: number;
  max_separation: number;
  tick: number;
  is_complete: boolean;
  result: string;
  phase: string;
  route_type: string;
  release_result: string | null;
}

// Route type display names
const ROUTE_NAMES: Record<string, string> = {
  flat: 'Flat',
  slant: 'Slant',
  comeback: 'Comeback',
  curl: 'Curl',
  out: 'Out',
  in: 'In/Dig',
  corner: 'Corner',
  post: 'Post',
  go: 'Go/Streak',
  hitch: 'Hitch',
};

// Coverage type display names
const COVERAGE_NAMES: Record<string, string> = {
  man_press: 'Man Press',
  man_off: 'Man Off (5yd)',
  zone_flat: 'Zone Flat',
  zone_deep: 'Zone Deep',
};

export function RoutesScreen() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<RouteSimState | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [tickStates, setTickStates] = useState<RouteSimState[]>([]);
  const [currentTick, setCurrentTick] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Settings
  const [routeType, setRouteType] = useState('out');
  const [coverageType, setCoverageType] = useState('man_off');

  // WR Attributes
  const [wrSpeed, setWrSpeed] = useState(85);
  const [wrAccel, setWrAccel] = useState(85);
  const [wrRouteRunning, setWrRouteRunning] = useState(85);
  const [wrRelease, setWrRelease] = useState(80);

  // DB Attributes
  const [dbSpeed, setDbSpeed] = useState(88);
  const [dbAccel, setDbAccel] = useState(86);
  const [dbManCov, setDbManCov] = useState(85);
  const [dbZoneCov, setDbZoneCov] = useState(80);
  const [dbPlayRec, setDbPlayRec] = useState(75);
  const [dbPress, setDbPress] = useState(80);

  const animationRef = useRef<number | null>(null);

  // Create session
  const createSession = useCallback(async () => {
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/routes/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          route_type: routeType,
          coverage_type: coverageType,
          wr_attributes: {
            speed: wrSpeed,
            acceleration: wrAccel,
            route_running: wrRouteRunning,
            release: wrRelease,
          },
          db_attributes: {
            speed: dbSpeed,
            acceleration: dbAccel,
            man_coverage: dbManCov,
            zone_coverage: dbZoneCov,
            play_recognition: dbPlayRec,
            press: dbPress,
          },
        }),
      });

      if (!response.ok) throw new Error('Failed to create session');

      const data = await response.json();
      setSessionId(data.session_id);
      setState(data.state);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [
    routeType,
    coverageType,
    wrSpeed,
    wrAccel,
    wrRouteRunning,
    wrRelease,
    dbSpeed,
    dbAccel,
    dbManCov,
    dbZoneCov,
    dbPlayRec,
    dbPress,
  ]);

  // Run simulation
  const runSimulation = useCallback(async () => {
    if (!sessionId) return;

    setIsSimulating(true);
    setCurrentTick(0);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/routes/sessions/${sessionId}/run-sync`,
        { method: 'POST' }
      );

      if (!response.ok) throw new Error('Failed to run simulation');

      const states: RouteSimState[] = await response.json();
      setTickStates(states);

      // Animate through states
      let index = 0;
      const animate = () => {
        if (index >= states.length) {
          setIsSimulating(false);
          setState(states[states.length - 1]);
          return;
        }

        setState(states[index]);
        setCurrentTick(index + 1);
        index++;
        animationRef.current = window.setTimeout(animate, 100);
      };
      animate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setIsSimulating(false);
    }
  }, [sessionId]);

  // Reset
  const reset = useCallback(async () => {
    if (animationRef.current) {
      clearTimeout(animationRef.current);
    }
    setIsSimulating(false);
    setTickStates([]);
    setCurrentTick(0);

    if (!sessionId) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/routes/sessions/${sessionId}/reset`,
        { method: 'POST' }
      );
      if (response.ok) {
        const data = await response.json();
        setState(data.state);
      }
    } catch (err) {
      console.error('Reset failed:', err);
    }
  }, [sessionId]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (animationRef.current) clearTimeout(animationRef.current);
    };
  }, []);

  // Result color
  const resultColor = {
    open: '#22c55e',
    contested: '#f59e0b',
    covered: '#ef4444',
    in_progress: '#888',
  }[state?.result || 'in_progress'];

  // Release result display
  const releaseDisplay = {
    clean: { text: 'CLEAN RELEASE', color: '#22c55e' },
    slight_win: { text: 'SLIGHT WIN', color: '#84cc16' },
    contested: { text: 'CONTESTED', color: '#f59e0b' },
    rerouted: { text: 'REROUTED', color: '#f97316' },
    jammed: { text: 'JAMMED', color: '#ef4444' },
  }[state?.release_result || ''];

  // Phase display
  const phaseDisplay: Record<string, string> = {
    pre_snap: 'Pre-Snap',
    release: 'Release',
    stem: 'Stem',
    break: 'Break',
    post_break: 'Post-Break',
    complete: 'Complete',
  };

  if (!sessionId) {
    return (
      <div className="routes-screen">
        <div className="routes-header">
          <h1>Route Running Simulation</h1>
          <p>1 WR vs 1 DB - Route separation and coverage mechanics</p>
        </div>

        <div className="routes-setup">
          <div className="setup-section">
            <h3>Route & Coverage</h3>

            <div className="setup-option">
              <label>Route Type:</label>
              <select
                value={routeType}
                onChange={(e) => setRouteType(e.target.value)}
              >
                {Object.entries(ROUTE_NAMES).map(([key, name]) => (
                  <option key={key} value={key}>
                    {name}
                  </option>
                ))}
              </select>
            </div>

            <div className="setup-option">
              <label>Coverage Type:</label>
              <select
                value={coverageType}
                onChange={(e) => setCoverageType(e.target.value)}
              >
                {Object.entries(COVERAGE_NAMES).map(([key, name]) => (
                  <option key={key} value={key}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="setup-section">
            <h3>WR Attributes</h3>

            <div className="setup-option">
              <label>Speed: {wrSpeed}</label>
              <input
                type="range"
                min="40"
                max="99"
                value={wrSpeed}
                onChange={(e) => setWrSpeed(parseInt(e.target.value))}
              />
            </div>

            <div className="setup-option">
              <label>Acceleration: {wrAccel}</label>
              <input
                type="range"
                min="40"
                max="99"
                value={wrAccel}
                onChange={(e) => setWrAccel(parseInt(e.target.value))}
              />
            </div>

            <div className="setup-option">
              <label>Route Running: {wrRouteRunning}</label>
              <input
                type="range"
                min="40"
                max="99"
                value={wrRouteRunning}
                onChange={(e) => setWrRouteRunning(parseInt(e.target.value))}
              />
            </div>

            <div className="setup-option">
              <label>Release: {wrRelease}</label>
              <input
                type="range"
                min="40"
                max="99"
                value={wrRelease}
                onChange={(e) => setWrRelease(parseInt(e.target.value))}
              />
            </div>
          </div>

          <div className="setup-section">
            <h3>DB Attributes</h3>

            <div className="setup-option">
              <label>Speed: {dbSpeed}</label>
              <input
                type="range"
                min="40"
                max="99"
                value={dbSpeed}
                onChange={(e) => setDbSpeed(parseInt(e.target.value))}
              />
            </div>

            <div className="setup-option">
              <label>Acceleration: {dbAccel}</label>
              <input
                type="range"
                min="40"
                max="99"
                value={dbAccel}
                onChange={(e) => setDbAccel(parseInt(e.target.value))}
              />
            </div>

            <div className="setup-option">
              <label>Man Coverage: {dbManCov}</label>
              <input
                type="range"
                min="40"
                max="99"
                value={dbManCov}
                onChange={(e) => setDbManCov(parseInt(e.target.value))}
              />
            </div>

            <div className="setup-option">
              <label>Zone Coverage: {dbZoneCov}</label>
              <input
                type="range"
                min="40"
                max="99"
                value={dbZoneCov}
                onChange={(e) => setDbZoneCov(parseInt(e.target.value))}
              />
            </div>

            <div className="setup-option">
              <label>Play Recognition: {dbPlayRec}</label>
              <input
                type="range"
                min="40"
                max="99"
                value={dbPlayRec}
                onChange={(e) => setDbPlayRec(parseInt(e.target.value))}
              />
            </div>

            <div className="setup-option">
              <label>Press: {dbPress}</label>
              <input
                type="range"
                min="40"
                max="99"
                value={dbPress}
                onChange={(e) => setDbPress(parseInt(e.target.value))}
              />
            </div>
          </div>

          <button className="create-btn" onClick={createSession}>
            Create Simulation
          </button>

          {error && <div className="error">{error}</div>}
        </div>
      </div>
    );
  }

  return (
    <div className="routes-screen">
      <div className="routes-header">
        <h1>Route Running</h1>
        <span className="session-id">{sessionId}</span>
        <span className="route-badge">{ROUTE_NAMES[state?.route_type || routeType]}</span>
        <span className="coverage-badge">
          {COVERAGE_NAMES[state?.defender?.coverage_type || coverageType]}
        </span>
        <button
          className="end-btn"
          onClick={() => {
            setSessionId(null);
            setState(null);
          }}
        >
          End
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="routes-content">
        <div className="routes-main">
          {state && <RoutesCanvas state={state} />}

          <div className="routes-controls">
            <button
              className="control-btn start"
              onClick={runSimulation}
              disabled={isSimulating}
            >
              {isSimulating ? 'Running...' : 'Start Simulation'}
            </button>
            <button className="control-btn reset" onClick={reset}>
              Reset
            </button>
          </div>

          {tickStates.length > 0 && (
            <div className="tick-info">
              Tick {currentTick} / {tickStates.length}
            </div>
          )}
        </div>

        <div className="routes-sidebar">
          {state && (
            <>
              <div className="result-panel" style={{ borderColor: resultColor }}>
                <div className="result-label">Result</div>
                <div className="result-value" style={{ color: resultColor }}>
                  {state.result.toUpperCase()}
                </div>
              </div>

              <div className="separation-panel">
                <h3>Separation</h3>
                <div className="separation-current">
                  <span className="value">{state.separation.toFixed(1)}</span>
                  <span className="unit">yards</span>
                </div>
                <div className="separation-max">
                  Max: {state.max_separation.toFixed(1)} yards
                </div>
                <div className="separation-bar">
                  <div className="bar-track">
                    <div
                      className="bar-fill"
                      style={{
                        width: `${Math.min(state.separation / 5, 1) * 100}%`,
                        background:
                          state.separation > 3
                            ? '#22c55e'
                            : state.separation > 1
                            ? '#f59e0b'
                            : '#ef4444',
                      }}
                    />
                    <div className="marker open" style={{ left: '60%' }} />
                    <div className="marker contested" style={{ left: '20%' }} />
                  </div>
                  <div className="bar-labels">
                    <span>0</span>
                    <span>1</span>
                    <span>3</span>
                    <span>5+</span>
                  </div>
                </div>
              </div>

              <div className="phase-panel">
                <h3>Phase</h3>
                <div className="phase-value">
                  {phaseDisplay[state.phase] || state.phase}
                </div>
                {releaseDisplay && state.release_result && (
                  <div
                    className="release-result"
                    style={{ color: releaseDisplay.color }}
                  >
                    {releaseDisplay.text}
                  </div>
                )}
              </div>

              <div className="players-panel">
                <h3>Matchup</h3>
                <div className="player-card wr">
                  <div className="player-label">WR</div>
                  <div className="player-attrs">
                    <span>SPD: {wrSpeed}</span>
                    <span>RTE: {wrRouteRunning}</span>
                    <span>REL: {wrRelease}</span>
                  </div>
                </div>
                <div className="player-card db">
                  <div className="player-label">DB</div>
                  <div className="player-attrs">
                    <span>SPD: {dbSpeed}</span>
                    <span>MAN: {dbManCov}</span>
                    <span>PRS: {dbPress}</span>
                  </div>
                </div>
              </div>

              <div className="legend">
                <h3>Legend</h3>
                <div className="legend-item">
                  <span className="dot wr"></span> WR (Receiver)
                </div>
                <div className="legend-item">
                  <span className="dot db"></span> DB (Defender)
                </div>
                <div className="legend-item">
                  <span className="line route"></span> Route Path
                </div>
                <div className="legend-item">
                  <span className="line separation"></span> Separation
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
