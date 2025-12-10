/**
 * Team route running simulation screen - Multiple WRs vs DBs
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { TeamRoutesCanvas } from './TeamRoutesCanvas';
import './TeamRoutesScreen.css';

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

interface MatchupResult {
  receiver_id: string;
  defender_id: string;
  separation: number;
  max_separation: number;
  result: string;
}

interface TeamRouteSimState {
  receivers: TeamReceiver[];
  defenders: TeamDefender[];
  formation: string;
  coverage: string;
  concept: string;
  matchups: Record<string, MatchupResult>;
  tick: number;
  is_complete: boolean;
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

export function TeamRoutesScreen() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<TeamRouteSimState | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [tickStates, setTickStates] = useState<TeamRouteSimState[]>([]);
  const [currentTick, setCurrentTick] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Settings
  const [formation, setFormation] = useState('spread');
  const [coverage, setCoverage] = useState('cover_3');
  const [concept, setConcept] = useState('four_verts');

  const animationRef = useRef<number | null>(null);

  // Create session
  const createSession = useCallback(async () => {
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/team-routes/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          formation,
          coverage,
          concept,
        }),
      });

      if (!response.ok) throw new Error('Failed to create session');

      const data = await response.json();
      setSessionId(data.session_id);
      setState(data.state);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [formation, coverage, concept]);

  // Run simulation
  const runSimulation = useCallback(async () => {
    if (!sessionId) return;

    setIsSimulating(true);
    setCurrentTick(0);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/team-routes/sessions/${sessionId}/run-sync`,
        { method: 'POST' }
      );

      if (!response.ok) throw new Error('Failed to run simulation');

      const states: TeamRouteSimState[] = await response.json();
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
        `${API_BASE_URL}/team-routes/sessions/${sessionId}/reset`,
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
    switch (result) {
      case 'open':
        return '#22c55e';
      case 'contested':
        return '#f59e0b';
      case 'covered':
        return '#ef4444';
      default:
        return '#888';
    }
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
      <div className="team-routes-screen">
        <div className="team-routes-header">
          <h1>Team Route Simulation</h1>
          <p>Full receiver corps vs defensive backs - formations, coverages, concepts</p>
        </div>

        <div className="team-routes-setup">
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
    <div className="team-routes-screen">
      <div className="team-routes-header">
        <h1>Team Routes</h1>
        <span className="session-id">{sessionId}</span>
        <span className="badge formation">{FORMATION_NAMES[state?.formation || formation]}</span>
        <span className="badge coverage">{COVERAGE_NAMES[state?.coverage || coverage]}</span>
        <span className="badge concept">{CONCEPT_NAMES[state?.concept || concept]}</span>
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

      <div className="team-routes-content">
        <div className="team-routes-main">
          {state && <TeamRoutesCanvas state={state} />}

          <div className="team-routes-controls">
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

        <div className="team-routes-sidebar">
          {state && (
            <>
              {/* Summary Panel */}
              <div className="summary-panel">
                <h3>Results Summary</h3>
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
                <h3>Matchups</h3>
                {state.receivers.map((rcvr) => {
                  const matchup = state.matchups[rcvr.id];
                  return (
                    <div
                      key={rcvr.id}
                      className="matchup-card"
                      style={{ borderLeftColor: getResultColor(matchup?.result || 'in_progress') }}
                    >
                      <div className="matchup-header">
                        <span className="position">{POSITION_LABELS[rcvr.alignment] || rcvr.alignment}</span>
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

              {/* Defenders Panel */}
              <div className="defenders-panel">
                <h3>Defense</h3>
                {state.defenders.map((defender) => (
                  <div key={defender.id} className="defender-card">
                    <span className="position">{POSITION_LABELS[defender.alignment] || defender.alignment}</span>
                    <span className="assignment">
                      {defender.is_in_man ? 'Man' : defender.zone_assignment?.replace(/_/g, ' ') || 'Zone'}
                    </span>
                  </div>
                ))}
              </div>

              {/* Legend */}
              <div className="legend">
                <h3>Legend</h3>
                <div className="legend-item">
                  <span className="dot wr"></span> Receivers (circles)
                </div>
                <div className="legend-item">
                  <span className="dot db"></span> Defenders (squares)
                </div>
                <div className="legend-item">
                  <span className="line route"></span> Route paths
                </div>
                <div className="legend-item">
                  <span className="dot break"></span> Break points
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
