/**
 * Pocket collapse simulation screen - 5 OL vs variable DL with QB
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { PocketCanvas } from './PocketCanvas';
import './PocketScreen.css';

const API_BASE_URL = 'http://localhost:8000/api/v1';

interface Vec2 {
  x: number;
  y: number;
}

interface Player {
  id: string;
  role: string;
  position: Vec2;
  is_free: boolean;
  is_down: boolean;
  animation: string;
  facing: Vec2;
}

interface Engagement {
  blocker_roles: string[];
  rusher_role: string;
  contact_point: Vec2;
  state: string;
  rush_move: string;
  is_double_team: boolean;
}

interface QBState {
  action: string;
  pressure_level: string;
  throw_timer: number;
  throw_target_tick: number;
  pressure_left: number;
  pressure_right: number;
  pressure_front: number;
}

interface BlockingScheme {
  name: string;
  assignments: {
    blocker_role: string;
    assignment_type: string;
    target_role: string | null;
  }[];
}

interface PocketState {
  qb: Player;
  blockers: Player[];
  rushers: Player[];
  engagements: Engagement[];
  blocking_scheme: BlockingScheme;
  defensive_front: string;
  tick: number;
  is_complete: boolean;
  result: string;
  qb_state: QBState | null;
}

export function PocketScreen() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<PocketState | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [tickStates, setTickStates] = useState<PocketState[]>([]);
  const [currentTick, setCurrentTick] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Settings
  const [qbDepth, setQbDepth] = useState(7);
  const [defensiveFront, setDefensiveFront] = useState('4_man');
  const [blockingScheme, setBlockingScheme] = useState('man');
  const [stunt, setStunt] = useState('none');

  const animationRef = useRef<number | null>(null);

  // Create session
  const createSession = useCallback(async () => {
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/pocket/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          qb_depth: qbDepth,
          defensive_front: defensiveFront,
          blocking_scheme: blockingScheme,
          stunt: stunt,
        }),
      });

      if (!response.ok) throw new Error('Failed to create session');

      const data = await response.json();
      setSessionId(data.session_id);
      setState(data.state);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [qbDepth, defensiveFront, blockingScheme, stunt]);

  // Run simulation
  const runSimulation = useCallback(async () => {
    if (!sessionId) return;

    setIsSimulating(true);
    setCurrentTick(0);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/pocket/sessions/${sessionId}/run-sync`,
        { method: 'POST' }
      );

      if (!response.ok) throw new Error('Failed to run simulation');

      const states: PocketState[] = await response.json();
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
        `${API_BASE_URL}/pocket/sessions/${sessionId}/reset`,
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
    sack: '#ef4444',
    pressure: '#f59e0b',
    clean_pocket: '#22c55e',
    throw: '#3b82f6',
    in_progress: '#888',
  }[state?.result || 'in_progress'];

  // Pressure level color
  const pressureColor = {
    clean: '#22c55e',
    light: '#84cc16',
    moderate: '#f59e0b',
    heavy: '#f97316',
    critical: '#ef4444',
  }[state?.qb_state?.pressure_level || 'clean'];

  if (!sessionId) {
    return (
      <div className="pocket-screen">
        <div className="pocket-header">
          <h1>Pocket Collapse Simulation</h1>
          <p>5 OL vs variable DL with stationary QB - blocking assignments</p>
        </div>

        <div className="pocket-setup">
          <div className="setup-option">
            <label>QB Depth (yards behind LOS):</label>
            <input
              type="range"
              min="4"
              max="10"
              value={qbDepth}
              onChange={(e) => setQbDepth(parseInt(e.target.value))}
            />
            <span>{qbDepth} yards</span>
          </div>

          <div className="setup-option">
            <label>Defensive Front:</label>
            <select
              value={defensiveFront}
              onChange={(e) => setDefensiveFront(e.target.value)}
            >
              <option value="3_man">3-Man (LE, NT, RE)</option>
              <option value="4_man">4-Man (LE, DT, DT, RE)</option>
              <option value="5_man">5-Man (+ Blitzer)</option>
            </select>
          </div>

          <div className="setup-option">
            <label>Blocking Scheme:</label>
            <select
              value={blockingScheme}
              onChange={(e) => setBlockingScheme(e.target.value)}
            >
              <option value="man">Man Protection</option>
              <option value="slide_left">Slide Left</option>
              <option value="slide_right">Slide Right</option>
              <option value="double">Double Team</option>
            </select>
          </div>

          {defensiveFront === '4_man' && (
            <div className="setup-option">
              <label>DL Stunt:</label>
              <select
                value={stunt}
                onChange={(e) => setStunt(e.target.value)}
              >
                <option value="none">None</option>
                <option value="et_left">E-T Left (LE crash, DT loop)</option>
                <option value="et_right">E-T Right (RE crash, DT loop)</option>
                <option value="te_left">T-E Left (DT crash, LE loop)</option>
                <option value="te_right">T-E Right (DT crash, RE loop)</option>
                <option value="tt_twist">T-T Twist (DTs exchange)</option>
              </select>
            </div>
          )}

          <button className="create-btn" onClick={createSession}>
            Create Simulation
          </button>

          {error && <div className="error">{error}</div>}
        </div>
      </div>
    );
  }

  return (
    <div className="pocket-screen">
      <div className="pocket-header">
        <h1>Pocket Collapse</h1>
        <span className="session-id">{sessionId}</span>
        <span className="scheme-badge">{state?.blocking_scheme.name}</span>
        <button className="end-btn" onClick={() => {
          setSessionId(null);
          setState(null);
        }}>
          End
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="pocket-content">
        <div className="pocket-main">
          {state && <PocketCanvas state={state} />}

          <div className="pocket-controls">
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

        <div className="pocket-sidebar">
          {state && (
            <>
              <div className="result-panel" style={{ borderColor: resultColor }}>
                <div className="result-label">Result</div>
                <div className="result-value" style={{ color: resultColor }}>
                  {state.result.replace('_', ' ').toUpperCase()}
                </div>
              </div>

              {state.qb_state && (
                <div className="qb-state-panel" style={{ borderColor: pressureColor }}>
                  <h3>QB Status</h3>
                  <div className="qb-action">
                    <span className="label">Action:</span>
                    <span className={`action-badge ${state.qb_state.action}`}>
                      {state.qb_state.action.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="qb-pressure">
                    <span className="label">Pressure:</span>
                    <span className="pressure-badge" style={{ background: pressureColor }}>
                      {state.qb_state.pressure_level.toUpperCase()}
                    </span>
                  </div>
                  <div className="pressure-directions">
                    <div className="pressure-bar">
                      <span className="direction">L</span>
                      <div className="bar-track">
                        <div
                          className="bar-fill left"
                          style={{ width: `${state.qb_state.pressure_left * 100}%` }}
                        />
                      </div>
                    </div>
                    <div className="pressure-bar">
                      <span className="direction">F</span>
                      <div className="bar-track">
                        <div
                          className="bar-fill front"
                          style={{ width: `${state.qb_state.pressure_front * 100}%` }}
                        />
                      </div>
                    </div>
                    <div className="pressure-bar">
                      <span className="direction">R</span>
                      <div className="bar-track">
                        <div
                          className="bar-fill right"
                          style={{ width: `${state.qb_state.pressure_right * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                  <div className="throw-timer">
                    <span className="label">Throw Timer:</span>
                    <div className="timer-track">
                      <div
                        className="timer-fill"
                        style={{
                          width: `${(state.tick / state.qb_state.throw_target_tick) * 100}%`,
                          background: state.tick >= state.qb_state.throw_target_tick ? '#3b82f6' : '#666'
                        }}
                      />
                    </div>
                    <span className="timer-text">
                      {state.tick}/{state.qb_state.throw_target_tick}
                    </span>
                  </div>
                </div>
              )}

              <div className="front-panel">
                <h3>Formation</h3>
                <div className="front-info">
                  <span>Front: {state.defensive_front.replace('_', '-')}</span>
                  <span>OL: {state.blockers.length}</span>
                  <span>DL: {state.rushers.length}</span>
                </div>
              </div>

              <div className="engagements-panel">
                <h3>Engagements ({state.engagements.length})</h3>
                {state.engagements.map((eng, i) => (
                  <div key={i} className={`engagement ${eng.state}`}>
                    <div className="engagement-matchup">
                      <span className="rusher-name">
                        {eng.rusher_role.toUpperCase()}
                      </span>
                      <span className="vs">vs</span>
                      <span className="blocker-name">
                        {eng.blocker_roles.map(r => r.toUpperCase()).join('+')}
                      </span>
                    </div>
                    <div className="engagement-details">
                      <span className={`state-badge ${eng.state}`}>{eng.state}</span>
                      {eng.is_double_team && (
                        <span className="double-team-badge">2x</span>
                      )}
                    </div>
                  </div>
                ))}

                {/* Show unblocked rushers */}
                {state.rushers.filter(r => r.is_free && !r.is_down).map((r, i) => (
                  <div key={`free-${i}`} className="engagement shed">
                    <div className="engagement-matchup">
                      <span className="rusher-name">{r.role.toUpperCase()}</span>
                      <span className="free-label">FREE</span>
                    </div>
                    <span className="state-badge shed">pursuing</span>
                  </div>
                ))}
              </div>

              <div className="legend">
                <h3>Legend</h3>
                <div className="legend-item">
                  <span className="dot qb"></span> QB
                </div>
                <div className="legend-item">
                  <span className="dot blocker"></span> OL (LT, LG, C, RG, RT)
                </div>
                <div className="legend-item">
                  <span className="dot rusher"></span> DL (LE, DT, NT, RE)
                </div>
                <div className="legend-item">
                  <span className="line engaged"></span> Engaged
                </div>
                <div className="legend-item">
                  <span className="line rusher-winning"></span> Rusher Winning
                </div>
                <div className="legend-item">
                  <span className="line blocker-winning"></span> Blocker Winning
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
