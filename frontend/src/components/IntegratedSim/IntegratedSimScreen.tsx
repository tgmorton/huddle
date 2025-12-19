/**
 * Integrated simulation screen - combines pocket collapse + play simulation
 * Full passing play with blocking, pressure, routes, coverage, and QB decisions
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { IntegratedSimCanvas } from './IntegratedSimCanvas';
import './IntegratedSimScreen.css';

const API_BASE_URL = 'http://localhost:8000/api/v1';

interface Vec2 {
  x: number;
  y: number;
}

// Pocket simulation types
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
}

// Play simulation types
interface RouteWaypoint {
  position: Vec2;
  arrival_tick: number;
  is_break: boolean;
}

interface TeamReceiver {
  id: string;
  position: Vec2;
  alignment: string;
  route: RouteWaypoint[];
  route_type: string;
  animation: string;
  facing: Vec2;
}

interface TeamDefender {
  id: string;
  position: Vec2;
  alignment: string;
  zone_assignment: string | null;
  is_in_man: boolean;
  animation: string;
  facing: Vec2;
}

interface TeamQB {
  id: string;
  position: Vec2;
  attributes: {
    arm_strength: number;
    accuracy: number;
    decision_making: number;
    pocket_awareness: number;
  };
  read_order: string[];
  current_read_idx: number;
  ticks_on_read: number;
  target_receiver_id: string | null;
  throw_tick: number | null;
  has_thrown: boolean;
  animation: string;
  facing: Vec2;
}

interface Ball {
  position: Vec2;
  start_position: Vec2;
  target_position: Vec2;
  velocity: number;
  is_thrown: boolean;
  is_caught: boolean;
  is_incomplete: boolean;
  throw_tick: number;
  arrival_tick: number;
  target_receiver_id: string | null;
  intercepted_by_id: string | null;
}

interface MatchupResult {
  receiver_id: string;
  defender_id: string;
  separation: number;
  max_separation: number;
  result: string;
}

interface PlayState {
  receivers: TeamReceiver[];
  defenders: TeamDefender[];
  qb: TeamQB;
  ball: Ball;
  formation: string;
  coverage: string;
  concept: string;
  matchups: Record<string, MatchupResult>;
  tick: number;
  is_complete: boolean;
  play_result: string;
}

// Integrated simulation types
interface PressureState {
  total: number;
  level: string;
  eta_ticks: number | string;
  left: number;
  right: number;
  front: number;
  qb_moving: boolean;
  panic: boolean;
  free_rusher: boolean;
  qb_position: Vec2;
}

interface FieldContext {
  hash_position: string;
  yard_line: number;
  is_red_zone: boolean;
  distance_to_left_sideline: number;
  distance_to_right_sideline: number;
}

interface IntegratedState {
  tick: number;
  is_complete: boolean;
  result: string;
  pressure_state: PressureState | null;
  field_context: FieldContext;
  target_receiver: string | null;
  throw_tick: number | null;
  yards_gained: number | null;
  pocket_state: PocketState | null;
  play_state: PlayState | null;
}

// Display names
const FORMATION_NAMES: Record<string, string> = {
  trips_right: 'Trips Right',
  trips_left: 'Trips Left',
  spread: 'Spread',
  empty: 'Empty',
  doubles: 'Doubles',
};

const COVERAGE_NAMES: Record<string, string> = {
  cover_0: 'Cover 0 (Man Blitz)',
  cover_1: 'Cover 1 (Man + FS)',
  cover_2: 'Cover 2 (Zone)',
  cover_3: 'Cover 3 (Zone)',
  cover_4: 'Cover 4 (Quarters)',
};

const CONCEPT_NAMES: Record<string, string> = {
  four_verts: 'Four Verticals',
  mesh: 'Mesh',
  smash: 'Smash',
  flood: 'Flood',
  slants: 'All Slants',
};

const FRONT_NAMES: Record<string, string> = {
  '3_man': '3-Man Rush',
  '4_man': '4-Man Rush',
  '5_man': '5-Man Rush',
};

const DROPBACK_NAMES: Record<string, string> = {
  'shotgun': 'Shotgun',
  '3_step': '3-Step Drop',
  '5_step': '5-Step Drop',
  '7_step': '7-Step Drop',
};

const HASH_NAMES: Record<string, string> = {
  left: 'Left Hash',
  middle: 'Middle',
  right: 'Right Hash',
};

const RESULT_COLORS: Record<string, string> = {
  complete: '#22c55e',
  incomplete: '#f97316',
  interception: '#ef4444',
  sack: '#dc2626',
  scramble: '#8b5cf6',
  throwaway: '#6b7280',
  in_progress: '#888',
};

const PRESSURE_COLORS: Record<string, string> = {
  clean: '#22c55e',
  light: '#84cc16',
  moderate: '#f59e0b',
  heavy: '#f97316',
  critical: '#ef4444',
};

export function IntegratedSimScreen() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<IntegratedState | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [tickStates, setTickStates] = useState<IntegratedState[]>([]);
  const [currentTick, setCurrentTick] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Settings
  const [formation, setFormation] = useState('spread');
  const [coverage, setCoverage] = useState('cover_3');
  const [concept, setConcept] = useState('smash');
  const [dropbackType, setDropbackType] = useState('shotgun');
  const [defensiveFront, setDefensiveFront] = useState('4_man');
  const [hashPosition, setHashPosition] = useState('middle');
  const [yardLine, setYardLine] = useState(25);
  const [varianceEnabled, setVarianceEnabled] = useState(true);

  const animationRef = useRef<number | null>(null);

  // Create session
  const createSession = useCallback(async () => {
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/integrated-sim/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          formation,
          coverage,
          concept,
          dropback_type: dropbackType,
          defensive_front: defensiveFront,
          hash_position: hashPosition,
          yard_line: yardLine,
          variance_enabled: varianceEnabled,
        }),
      });

      if (!response.ok) throw new Error('Failed to create session');

      const data = await response.json();
      setSessionId(data.session_id);
      setState(data.state);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [formation, coverage, concept, dropbackType, defensiveFront, hashPosition, yardLine, varianceEnabled]);

  // Run simulation
  const runSimulation = useCallback(async () => {
    if (!sessionId) return;

    setIsSimulating(true);
    setCurrentTick(0);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/integrated-sim/sessions/${sessionId}/run-sync`,
        { method: 'POST' }
      );

      if (!response.ok) throw new Error('Failed to run simulation');

      const states: IntegratedState[] = await response.json();
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
        animationRef.current = window.setTimeout(animate, 80);
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
        `${API_BASE_URL}/integrated-sim/sessions/${sessionId}/reset`,
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

  // Get result color
  const getResultColor = (result: string) => {
    return RESULT_COLORS[result] || RESULT_COLORS.in_progress;
  };

  // Get pressure color
  const getPressureColor = (level: string) => {
    return PRESSURE_COLORS[level] || PRESSURE_COLORS.clean;
  };

  if (!sessionId) {
    return (
      <div className="integrated-sim-screen">
        <div className="integrated-sim-header">
          <h1>Integrated Play Simulation</h1>
          <p>Full passing play with pocket collapse, routes, coverage, and QB decisions</p>
        </div>

        <div className="integrated-sim-setup">
          <div className="setup-row">
            <div className="setup-section">
              <h3>Offense</h3>
              <div className="setup-option">
                <label>Formation</label>
                <select value={formation} onChange={(e) => setFormation(e.target.value)}>
                  {Object.entries(FORMATION_NAMES).map(([key, name]) => (
                    <option key={key} value={key}>{name}</option>
                  ))}
                </select>
              </div>
              <div className="setup-option">
                <label>Route Concept</label>
                <select value={concept} onChange={(e) => setConcept(e.target.value)}>
                  {Object.entries(CONCEPT_NAMES).map(([key, name]) => (
                    <option key={key} value={key}>{name}</option>
                  ))}
                </select>
              </div>
              <div className="setup-option">
                <label>QB Dropback</label>
                <select value={dropbackType} onChange={(e) => setDropbackType(e.target.value)}>
                  {Object.entries(DROPBACK_NAMES).map(([key, name]) => (
                    <option key={key} value={key}>{name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="setup-section">
              <h3>Defense</h3>
              <div className="setup-option">
                <label>Coverage</label>
                <select value={coverage} onChange={(e) => setCoverage(e.target.value)}>
                  {Object.entries(COVERAGE_NAMES).map(([key, name]) => (
                    <option key={key} value={key}>{name}</option>
                  ))}
                </select>
              </div>
              <div className="setup-option">
                <label>Pass Rush</label>
                <select value={defensiveFront} onChange={(e) => setDefensiveFront(e.target.value)}>
                  {Object.entries(FRONT_NAMES).map(([key, name]) => (
                    <option key={key} value={key}>{name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="setup-section">
              <h3>Field Position</h3>
              <div className="setup-option">
                <label>Yard Line (own {yardLine})</label>
                <input
                  type="range"
                  min="1"
                  max="99"
                  value={yardLine}
                  onChange={(e) => setYardLine(parseInt(e.target.value))}
                />
              </div>
              <div className="setup-option">
                <label>Hash Mark</label>
                <select value={hashPosition} onChange={(e) => setHashPosition(e.target.value)}>
                  {Object.entries(HASH_NAMES).map(([key, name]) => (
                    <option key={key} value={key}>{name}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="setup-options">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={varianceEnabled}
                onChange={(e) => setVarianceEnabled(e.target.checked)}
              />
              Enable Variance (stochastic outcomes)
            </label>
          </div>

          <button className="create-btn" onClick={createSession}>
            Create Simulation
          </button>

          {error && <div className="error">{error}</div>}
        </div>
      </div>
    );
  }

  const pressure = state?.pressure_state;
  const playState = state?.play_state;
  const pocketState = state?.pocket_state;

  return (
    <div className="integrated-sim-screen">
      <div className="integrated-sim-header">
        <h1>Integrated Sim</h1>
        <span className="session-id">{sessionId}</span>
        <span className="badge formation">{FORMATION_NAMES[formation]}</span>
        <span className="badge coverage">{COVERAGE_NAMES[coverage]}</span>
        <span className="badge concept">{CONCEPT_NAMES[concept]}</span>
        {state?.result && state.result !== 'in_progress' && (
          <span className="badge play-result" style={{ background: getResultColor(state.result) }}>
            {state.result.toUpperCase()}
          </span>
        )}
        <button className="end-btn" onClick={() => { setSessionId(null); setState(null); }}>
          End
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="integrated-sim-content">
        <div className="integrated-sim-main">
          {state && playState && pocketState && (
            <IntegratedSimCanvas
              playState={playState}
              pocketState={pocketState}
              pressureState={pressure ?? null}
            />
          )}

          <div className="integrated-sim-controls">
            <button
              className="control-btn start"
              onClick={runSimulation}
              disabled={isSimulating}
            >
              {isSimulating ? 'Running...' : 'Run Play'}
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

        <div className="integrated-sim-sidebar">
          {state && (
            <>
              {/* Pressure Panel */}
              {pressure && (
                <div className="pressure-panel" style={{ borderColor: getPressureColor(pressure.level) }}>
                  <h3>Pocket Pressure</h3>
                  <div className="pressure-level">
                    <span className="label">Level:</span>
                    <span className="pressure-badge" style={{ background: getPressureColor(pressure.level) }}>
                      {pressure.level.toUpperCase()}
                    </span>
                    {pressure.panic && <span className="panic-badge">PANIC!</span>}
                  </div>
                  <div className="pressure-meter">
                    <div className="meter-track">
                      <div
                        className="meter-fill"
                        style={{
                          width: `${pressure.total * 100}%`,
                          background: getPressureColor(pressure.level)
                        }}
                      />
                    </div>
                    <span className="meter-value">{(pressure.total * 100).toFixed(0)}%</span>
                  </div>
                  <div className="pressure-directions">
                    <div className="pressure-bar">
                      <span className="direction">L</span>
                      <div className="bar-track">
                        <div className="bar-fill left" style={{ width: `${pressure.left * 100}%` }} />
                      </div>
                    </div>
                    <div className="pressure-bar">
                      <span className="direction">F</span>
                      <div className="bar-track">
                        <div className="bar-fill front" style={{ width: `${pressure.front * 100}%` }} />
                      </div>
                    </div>
                    <div className="pressure-bar">
                      <span className="direction">R</span>
                      <div className="bar-track">
                        <div className="bar-fill right" style={{ width: `${pressure.right * 100}%` }} />
                      </div>
                    </div>
                  </div>
                  {pressure.eta_ticks !== 'inf' && (
                    <div className="eta">
                      ETA: {typeof pressure.eta_ticks === 'number' ? pressure.eta_ticks.toFixed(1) : pressure.eta_ticks} ticks
                    </div>
                  )}
                </div>
              )}

              {/* QB Panel */}
              {playState && (
                <div className="qb-panel">
                  <h3>Quarterback</h3>
                  <div className="qb-info">
                    <div className="qb-stat">
                      <span className="label">Read</span>
                      <span className="value">#{playState.qb.current_read_idx + 1}</span>
                    </div>
                    <div className="qb-stat">
                      <span className="label">Thrown</span>
                      <span className="value">{playState.qb.has_thrown ? 'Yes' : 'No'}</span>
                    </div>
                    {state.throw_tick && (
                      <div className="qb-stat">
                        <span className="label">Throw Tick</span>
                        <span className="value">{state.throw_tick}</span>
                      </div>
                    )}
                  </div>
                  <div className="qb-attributes">
                    <div className="attr">ARM: {playState.qb.attributes.arm_strength}</div>
                    <div className="attr">ACC: {playState.qb.attributes.accuracy}</div>
                    <div className="attr">DEC: {playState.qb.attributes.decision_making}</div>
                    <div className="attr">AWR: {playState.qb.attributes.pocket_awareness}</div>
                  </div>
                </div>
              )}

              {/* Result Panel */}
              <div className="result-panel" style={{ borderColor: getResultColor(state.result) }}>
                <div className="result-label">Result</div>
                <div className="result-value" style={{ color: getResultColor(state.result) }}>
                  {state.result.replace('_', ' ').toUpperCase()}
                </div>
                {state.yards_gained !== null && (
                  <div className="yards-gained">
                    {state.yards_gained.toFixed(1)} yards
                  </div>
                )}
              </div>

              {/* Engagements Panel */}
              {pocketState && (
                <div className="engagements-panel">
                  <h3>Blocking ({pocketState.engagements.length})</h3>
                  {pocketState.engagements.slice(0, 5).map((eng, i) => (
                    <div key={i} className={`engagement ${eng.state}`}>
                      <div className="engagement-matchup">
                        <span className="rusher-name">{eng.rusher_role.toUpperCase()}</span>
                        <span className="vs">vs</span>
                        <span className="blocker-name">
                          {eng.blocker_roles.map(r => r.toUpperCase()).join('+')}
                        </span>
                      </div>
                      <span className={`state-badge ${eng.state}`}>{eng.state}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Field Position */}
              <div className="field-panel">
                <h3>Field Position</h3>
                <div className="field-info">
                  <span>Own {state.field_context.yard_line}</span>
                  <span>{HASH_NAMES[state.field_context.hash_position] || state.field_context.hash_position}</span>
                  {state.field_context.is_red_zone && <span className="red-zone">RED ZONE</span>}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
