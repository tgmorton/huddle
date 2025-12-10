/**
 * Play simulation screen - QB + receivers + ball
 * Full passing play with read progression and ball physics
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { PlaySimCanvas } from './PlaySimCanvas';
import './PlaySimScreen.css';

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

interface PlaySimState {
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
  cover_2_man: 'Cover 2 Man',
};

const CONCEPT_NAMES: Record<string, string> = {
  four_verts: 'Four Verticals',
  mesh: 'Mesh',
  smash: 'Smash',
  flood: 'Flood',
  levels: 'Levels',
  slants: 'All Slants',
  curls: 'Curls',
  custom: 'Custom',
};

const POSITION_LABELS: Record<string, string> = {
  x: 'X (Split End)',
  z: 'Z (Flanker)',
  slot_l: 'Slot L',
  slot_r: 'Slot R',
  te: 'TE',
  cb1: 'CB1',
  cb2: 'CB2',
  nickel: 'Nickel',
  ss: 'SS',
  fs: 'FS',
};

const RESULT_COLORS: Record<string, string> = {
  complete: '#22c55e',
  incomplete: '#f97316',
  interception: '#ef4444',
  in_progress: '#888',
};

export function PlaySimScreen() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<PlaySimState | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [tickStates, setTickStates] = useState<PlaySimState[]>([]);
  const [currentTick, setCurrentTick] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Settings
  const [formation, setFormation] = useState('spread');
  const [coverage, setCoverage] = useState('cover_3');
  const [concept, setConcept] = useState('smash');
  const [varianceEnabled, setVarianceEnabled] = useState(true);

  const animationRef = useRef<number | null>(null);

  // Create session
  const createSession = useCallback(async () => {
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/play-sim/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          formation,
          coverage,
          concept,
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
  }, [formation, coverage, concept, varianceEnabled]);

  // Run simulation
  const runSimulation = useCallback(async () => {
    if (!sessionId) return;

    setIsSimulating(true);
    setCurrentTick(0);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/play-sim/sessions/${sessionId}/run-sync`,
        { method: 'POST' }
      );

      if (!response.ok) throw new Error('Failed to run simulation');

      const states: PlaySimState[] = await response.json();
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
        `${API_BASE_URL}/play-sim/sessions/${sessionId}/reset`,
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

  // Count results
  const countResults = () => {
    if (!state?.matchups) return { open: 0, contested: 0, covered: 0 };
    const results = Object.values(state.matchups);
    return {
      open: results.filter((m) => m.result === 'open').length,
      contested: results.filter((m) => m.result === 'contested').length,
      covered: results.filter((m) => m.result === 'covered').length,
    };
  };

  if (!sessionId) {
    return (
      <div className="play-sim-screen">
        <div className="play-sim-header">
          <h1>Play Simulation</h1>
          <p>QB reads, throws, and ball physics with stochastic variance</p>
        </div>

        <div className="play-sim-setup">
          <div className="setup-section">
            <h3>Formation</h3>
            <div className="setup-option">
              <select
                value={formation}
                onChange={(e) => setFormation(e.target.value)}
              >
                {Object.entries(FORMATION_NAMES).map(([key, name]) => (
                  <option key={key} value={key}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="setup-section">
            <h3>Coverage</h3>
            <div className="setup-option">
              <select
                value={coverage}
                onChange={(e) => setCoverage(e.target.value)}
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
            <h3>Route Concept</h3>
            <div className="setup-option">
              <select
                value={concept}
                onChange={(e) => setConcept(e.target.value)}
              >
                {Object.entries(CONCEPT_NAMES).map(([key, name]) => (
                  <option key={key} value={key}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="setup-section variance-section">
            <h3>Options</h3>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={varianceEnabled}
                onChange={(e) => setVarianceEnabled(e.target.checked)}
              />
              Enable Variance
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

  const results = countResults();

  return (
    <div className="play-sim-screen">
      <div className="play-sim-header">
        <h1>Play Sim</h1>
        <span className="session-id">{sessionId}</span>
        <span className="badge formation">{FORMATION_NAMES[state?.formation || formation]}</span>
        <span className="badge coverage">{COVERAGE_NAMES[state?.coverage || coverage]}</span>
        <span className="badge concept">{CONCEPT_NAMES[state?.concept || concept]}</span>
        {state?.play_result && state.play_result !== 'in_progress' && (
          <span className="badge play-result" style={{ background: getResultColor(state.play_result) }}>
            {state.play_result.toUpperCase()}
          </span>
        )}
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

      <div className="play-sim-content">
        <div className="play-sim-main">
          {state && <PlaySimCanvas state={state} />}

          <div className="play-sim-controls">
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

        <div className="play-sim-sidebar">
          {state && (
            <>
              {/* QB Panel */}
              <div className="qb-panel">
                <h3>Quarterback</h3>
                <div className="qb-info">
                  <div className="qb-stat">
                    <span className="label">Read</span>
                    <span className="value">#{state.qb.current_read_idx + 1}</span>
                  </div>
                  <div className="qb-stat">
                    <span className="label">Thrown</span>
                    <span className="value">{state.qb.has_thrown ? 'Yes' : 'No'}</span>
                  </div>
                  {state.qb.throw_tick && (
                    <div className="qb-stat">
                      <span className="label">Throw Tick</span>
                      <span className="value">{state.qb.throw_tick}</span>
                    </div>
                  )}
                </div>
                <div className="qb-attributes">
                  <div className="attr">ARM: {state.qb.attributes.arm_strength}</div>
                  <div className="attr">ACC: {state.qb.attributes.accuracy}</div>
                  <div className="attr">DEC: {state.qb.attributes.decision_making}</div>
                </div>
              </div>

              {/* Ball Panel */}
              <div className="ball-panel">
                <h3>Ball</h3>
                <div className="ball-info">
                  {!state.ball.is_thrown && (
                    <span className="ball-status">In QB's hands</span>
                  )}
                  {state.ball.is_thrown && !state.ball.is_caught && !state.ball.is_incomplete && (
                    <span className="ball-status in-flight">In flight</span>
                  )}
                  {state.ball.is_caught && (
                    <span className="ball-status caught">Caught!</span>
                  )}
                  {state.ball.is_incomplete && !state.ball.intercepted_by_id && (
                    <span className="ball-status incomplete">Incomplete</span>
                  )}
                  {state.ball.intercepted_by_id && (
                    <span className="ball-status interception">Intercepted!</span>
                  )}
                </div>
              </div>

              {/* Summary Panel */}
              <div className="summary-panel">
                <h3>Coverage Results</h3>
                <div className="result-counts">
                  <div className="result-count open">
                    <span className="count">{results.open}</span>
                    <span className="label">Open</span>
                  </div>
                  <div className="result-count contested">
                    <span className="count">{results.contested}</span>
                    <span className="label">Contested</span>
                  </div>
                  <div className="result-count covered">
                    <span className="count">{results.covered}</span>
                    <span className="label">Covered</span>
                  </div>
                </div>
              </div>

              {/* Matchups Panel */}
              <div className="matchups-panel">
                <h3>Receivers</h3>
                {state.receivers.map((rcvr) => {
                  const matchup = state.matchups[rcvr.id];
                  const isTarget = state.qb.target_receiver_id === rcvr.id;
                  const isCurrentRead = state.qb.read_order[state.qb.current_read_idx] === rcvr.id;
                  return (
                    <div
                      key={rcvr.id}
                      className={`matchup-card ${isTarget ? 'target' : ''} ${isCurrentRead ? 'current-read' : ''}`}
                      style={{ borderLeftColor: getResultColor(matchup?.result || 'in_progress') }}
                    >
                      <div className="matchup-header">
                        <span className="position">
                          {POSITION_LABELS[rcvr.alignment] || rcvr.alignment}
                          {isTarget && <span className="target-indicator"> (TARGET)</span>}
                          {isCurrentRead && !state.qb.has_thrown && <span className="read-indicator"> (READING)</span>}
                        </span>
                        <span
                          className="result-badge"
                          style={{ background: getResultColor(matchup?.result || 'in_progress') }}
                        >
                          {matchup?.result?.toUpperCase() || 'PENDING'}
                        </span>
                      </div>
                      <div className="matchup-details">
                        <span className="route-type">{rcvr.route_type}</span>
                        {matchup && (
                          <span className="separation">
                            {matchup.separation.toFixed(1)}yd (max: {matchup.max_separation.toFixed(1)})
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Legend */}
              <div className="legend">
                <h3>Legend</h3>
                <div className="legend-item">
                  <span className="dot qb"></span> Quarterback (blue)
                </div>
                <div className="legend-item">
                  <span className="dot wr"></span> Receivers (circles)
                </div>
                <div className="legend-item">
                  <span className="dot db"></span> Defenders (squares)
                </div>
                <div className="legend-item">
                  <span className="dot ball"></span> Football (white)
                </div>
                <div className="legend-item">
                  <span className="line route"></span> Route paths
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
