/**
 * V2 Simulation Visualizer Screen
 *
 * Shows route simulation with coverage - real-time WebSocket updates
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { V2SimCanvas } from './V2SimCanvas';
import './V2SimScreen.css';

const API_BASE = 'http://localhost:8000/api/v1/v2-sim';
const WS_BASE = 'ws://localhost:8000/api/v1/v2-sim/ws';

// Types
interface PlayerState {
  id: string;
  name: string;
  team: string;
  position: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  speed: number;
  facing_x?: number;
  facing_y?: number;
  player_type: 'receiver' | 'defender' | 'qb' | 'ol' | 'dl';
  has_ball?: boolean;
  goal_direction?: number;
  // Receiver fields
  route_name?: string;
  route_phase?: string;
  current_waypoint?: number;
  total_waypoints?: number;
  target_x?: number;
  target_y?: number;
  // Defender fields
  coverage_type?: string;
  coverage_phase?: string;
  man_target_id?: string;
  zone_type?: string;
  has_triggered?: boolean;
  has_reacted_to_break?: boolean;
  anticipated_x?: number;
  anticipated_y?: number;
  // DB recognition
  has_recognized_break?: boolean;
  recognition_timer?: number;
  recognition_delay?: number;
  // Pursuit
  pursuit_target_x?: number;
  pursuit_target_y?: number;
  // Blocking
  is_engaged?: boolean;
  engaged_with_id?: string;
  block_shed_progress?: number;
  // Ballcarrier
  current_move?: string;
  move_success?: boolean;
  // Common
  at_max_speed?: boolean;
  cut_occurred?: boolean;
  cut_angle?: number;
  reasoning?: string;
}

interface WaypointData {
  x: number;
  y: number;
  is_break: boolean;
  phase: string;
  look_for_ball: boolean;
}

interface ZoneBoundary {
  min_x: number;
  max_x: number;
  min_y: number;
  max_y: number;
  anchor_x: number;
  anchor_y: number;
  is_deep: boolean;
}

interface EventData {
  time: number;
  type: string;
  player_id: string | null;
  description: string;
}

// Unified player config matching backend PlayerConfig
interface PlayerConfig {
  name: string;
  position: string;  // QB, WR, RB, TE, OL, DL, LB, CB, S, etc.
  alignment_x: number;
  alignment_y?: number;
  // Route (for receivers)
  route_type?: string;
  read_order?: number;
  is_hot_route?: boolean;
  // Coverage (for DBs/LBs)
  coverage_type?: string;
  man_target?: string;
  zone_type?: string;
  // Attributes
  speed?: number;
  acceleration?: number;
  agility?: number;
  strength?: number;
  awareness?: number;
  throw_power?: number;
  throw_accuracy?: number;
  route_running?: number;
  catching?: number;
  elusiveness?: number;
  vision?: number;
  block_power?: number;
  block_finesse?: number;
  pass_rush?: number;
  man_coverage?: number;
  zone_coverage?: number;
  play_recognition?: number;
  press?: number;
  tackling?: number;
}

interface BallState {
  state: 'dead' | 'held' | 'in_flight' | 'loose';
  x: number;
  y: number;
  height: number;  // Height in yards (for 2.5D visualization)
  carrier_id: string | null;
  flight_origin_x?: number;
  flight_origin_y?: number;
  flight_target_x?: number;
  flight_target_y?: number;
  flight_progress?: number;
  intended_receiver_id?: string;
  throw_type?: 'bullet' | 'touch' | 'lob';
  peak_height?: number;
}

type PlayOutcome = 'in_progress' | 'complete' | 'incomplete' | 'interception' | 'tackled';

interface SimState {
  session_id: string;
  tick: number;
  time: number;
  is_running: boolean;
  is_paused: boolean;
  is_complete: boolean;
  play_outcome?: PlayOutcome;
  ball_carrier_id?: string | null;
  tackle_position?: { x: number; y: number } | null;
  players: PlayerState[];
  ball?: BallState;
  waypoints: Record<string, WaypointData[]>;
  zone_boundaries: Record<string, ZoneBoundary>;
  events: EventData[];
  config: {
    tick_rate_ms: number;
    max_time: number;
    offense: PlayerConfig[];
    defense: PlayerConfig[];
  };
}

interface RouteOption {
  type: string;
  name: string;
  break_depth: number;
  total_depth: number;
  route_side: string;
  is_quick: boolean;
}

interface ZoneOption {
  type: string;
  is_deep: boolean;
}

interface ConceptOption {
  name: string;
  display_name: string;
  description: string;
  formation: string;
  timing: string;
  coverage_beaters: string[];
  route_count: number;
}

interface SchemeOption {
  name: string;
  display_name: string;
  scheme_type: string;
  description: string;
  strengths: string[];
  weaknesses: string[];
}

// Quick preset matchups
const PRESET_MATCHUPS = [
  { concept: 'four_verts', scheme: 'cover_2', label: '4 Verts vs Cover 2', desc: 'Attack the deep middle seam' },
  { concept: 'mesh', scheme: 'cover_1', label: 'Mesh vs Man', desc: 'Rub routes create separation' },
  { concept: 'smash', scheme: 'cover_3', label: 'Smash vs Cover 3', desc: 'Corner/hitch combo attack' },
  { concept: 'slants', scheme: 'cover_2', label: 'Slants vs Cover 2', desc: 'Quick inside throws' },
  { concept: 'four_verts', scheme: 'cover_3', label: '4 Verts vs Cover 3', desc: 'Flood the deep zones' },
  { concept: 'mesh', scheme: 'cover_3', label: 'Mesh vs Zone', desc: 'Find the soft spots' },
];

// Default configs using new unified PlayerConfig format
const DEFAULT_OFFENSE: PlayerConfig[] = [
  { name: "QB", position: "QB", alignment_x: 0, alignment_y: -5, throw_power: 90, throw_accuracy: 88 },
  { name: "Tyreek Hill", position: "WR", alignment_x: 20, alignment_y: 0, route_type: "slant", read_order: 1, speed: 99, acceleration: 95, agility: 96, route_running: 92 },
  { name: "Davante Adams", position: "WR", alignment_x: -18, alignment_y: 0, route_type: "curl", read_order: 2, speed: 88, acceleration: 86, agility: 90, route_running: 98 },
];

const DEFAULT_DEFENSE: PlayerConfig[] = [
  { name: "Sauce Gardner", position: "CB", alignment_x: 20, alignment_y: 7, coverage_type: "man", man_target: "Tyreek Hill", speed: 92, acceleration: 90, agility: 92, man_coverage: 99, zone_coverage: 90, play_recognition: 88 },
  { name: "Jaire Alexander", position: "CB", alignment_x: -18, alignment_y: 7, coverage_type: "man", man_target: "Davante Adams", speed: 91, acceleration: 89, agility: 93, man_coverage: 95, zone_coverage: 88, play_recognition: 85 },
];

export function V2SimScreen() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [simState, setSimState] = useState<SimState | null>(null);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);
  const [routeOptions, setRouteOptions] = useState<RouteOption[]>([]);
  const [zoneOptions, setZoneOptions] = useState<ZoneOption[]>([]);
  const [conceptOptions, setConceptOptions] = useState<ConceptOption[]>([]);
  const [schemeOptions, setSchemeOptions] = useState<SchemeOption[]>([]);
  const [selectedConcept, setSelectedConcept] = useState<string>('four_verts');
  const [selectedScheme, setSelectedScheme] = useState<string>('cover_2');
  const [offense, setOffense] = useState<PlayerConfig[]>(DEFAULT_OFFENSE);
  const [defense, setDefense] = useState<PlayerConfig[]>(DEFAULT_DEFENSE);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [setupMode, setSetupMode] = useState<'matchup' | 'custom'>('matchup');

  const wsRef = useRef<WebSocket | null>(null);

  // Fetch available routes, zones, concepts, and schemes
  useEffect(() => {
    fetch(`${API_BASE}/routes`)
      .then(res => res.json())
      .then(setRouteOptions)
      .catch(err => console.error('Failed to fetch routes:', err));

    fetch(`${API_BASE}/zones`)
      .then(res => res.json())
      .then((zones: ZoneOption[]) => setZoneOptions(zones))
      .catch(err => console.error('Failed to fetch zones:', err));

    fetch(`${API_BASE}/concepts`)
      .then(res => res.json())
      .then(setConceptOptions)
      .catch(err => console.error('Failed to fetch concepts:', err));

    fetch(`${API_BASE}/schemes`)
      .then(res => res.json())
      .then(setSchemeOptions)
      .catch(err => console.error('Failed to fetch schemes:', err));
  }, []);

  // Helper to connect WebSocket after session is created
  const connectWebSocket = useCallback((sessionId: string) => {
    const ws = new WebSocket(`${WS_BASE}/${sessionId}`);

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === 'state_sync') {
        setSimState(msg.payload);
        if (msg.payload.players.length > 0) {
          setSelectedPlayerId(msg.payload.players[0].id);
        }
      } else if (msg.type === 'tick') {
        setSimState(prev => prev ? {
          ...prev,
          tick: msg.payload.tick,
          time: msg.payload.time,
          players: msg.payload.players,
          ball: msg.payload.ball,
          play_outcome: msg.payload.play_outcome,
          ball_carrier_id: msg.payload.ball_carrier_id,
          tackle_position: msg.payload.tackle_position,
          events: msg.payload.events ? [...prev.events, ...msg.payload.events] : prev.events,
        } : null);
      } else if (msg.type === 'complete') {
        setSimState(msg.payload);
      } else if (msg.type === 'error') {
        setError(msg.message);
      }
    };

    ws.onclose = () => setIsConnected(false);
    ws.onerror = () => {
      setError('WebSocket error');
      setIsConnected(false);
    };

    wsRef.current = ws;
  }, []);

  // Create matchup session
  const createMatchupSession = useCallback(async () => {
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/matchup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          concept: selectedConcept,
          scheme: selectedScheme,
          tick_rate_ms: 50,
          max_time: 6.0,
        }),
      });

      if (!res.ok) throw new Error('Failed to create matchup session');

      const session = await res.json();
      setSessionId(session.session_id);
      connectWebSocket(session.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [selectedConcept, selectedScheme, connectWebSocket]);

  // Create custom session with new offense[]/defense[] format
  const createSession = useCallback(async () => {
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          offense,
          defense,
          tick_rate_ms: 50,
          max_time: 6.0,
        }),
      });

      if (!res.ok) throw new Error('Failed to create session');

      const session = await res.json();
      setSessionId(session.session_id);
      connectWebSocket(session.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [offense, defense, connectWebSocket]);

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const sendCommand = (type: string, data?: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, ...data }));
    }
  };

  const start = () => sendCommand('start');
  const pause = () => sendCommand('pause');
  const resume = () => sendCommand('resume');
  const reset = () => sendCommand('reset');
  const step = () => sendCommand('step');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isConnected) return;
      switch (e.key) {
        case ' ':
          e.preventDefault();
          if (simState?.is_running && !simState?.is_paused) pause();
          else if (simState?.is_paused) resume();
          else start();
          break;
        case 's': step(); break;
        case 'r': reset(); break;
        case 'Tab':
          e.preventDefault();
          if (simState?.players) {
            const currentIdx = simState.players.findIndex(p => p.id === selectedPlayerId);
            const nextIdx = (currentIdx + 1) % simState.players.length;
            setSelectedPlayerId(simState.players[nextIdx].id);
          }
          break;
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isConnected, simState, selectedPlayerId]);

  const selectedPlayer = simState?.players.find(p => p.id === selectedPlayerId);
  const receivers = simState?.players.filter(p => p.player_type === 'receiver') || [];
  const defenderPlayers = simState?.players.filter(p => p.player_type === 'defender') || [];

  const currentConcept = conceptOptions.find(c => c.name === selectedConcept);
  const currentScheme = schemeOptions.find(s => s.name === selectedScheme);

  return (
    <div className="v2-sim-screen">
      <div className="v2-sim-main">
        {!sessionId ? (
          <div className="v2-sim-setup">
            <h2>V2 Route Simulation with Coverage</h2>

            {/* Mode selector tabs */}
            <div className="v2-mode-tabs">
              <button
                className={setupMode === 'matchup' ? 'active' : ''}
                onClick={() => setSetupMode('matchup')}
              >
                Play Matchups
              </button>
              <button
                className={setupMode === 'custom' ? 'active' : ''}
                onClick={() => setSetupMode('custom')}
              >
                Custom Setup
              </button>
            </div>

            {setupMode === 'matchup' ? (
              <div className="v2-matchup-setup">
                {/* Left side: Presets + Selectors */}
                <div className="v2-matchup-left">
                  {/* Quick Presets */}
                  <div className="v2-preset-section">
                    <h3>Quick Matchups</h3>
                    <div className="v2-preset-grid">
                      {PRESET_MATCHUPS.map((preset, i) => (
                        <div
                          key={i}
                          className={`v2-preset-card ${selectedConcept === preset.concept && selectedScheme === preset.scheme ? 'selected' : ''}`}
                          onClick={() => {
                            setSelectedConcept(preset.concept);
                            setSelectedScheme(preset.scheme);
                          }}
                        >
                          <div className="v2-preset-matchup">
                            <span className="v2-preset-offense">{preset.concept.replace('_', ' ')}</span>
                            <span className="v2-preset-vs">vs</span>
                            <span className="v2-preset-defense">{preset.scheme.replace('_', ' ')}</span>
                          </div>
                          <div className="v2-preset-desc">{preset.desc}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Custom Selection */}
                  <div className="v2-preset-section">
                    <h3>Custom Matchup</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                      <select
                        value={selectedConcept}
                        onChange={e => setSelectedConcept(e.target.value)}
                        className="v2-matchup-select"
                      >
                        {conceptOptions.map(c => (
                          <option key={c.name} value={c.name}>{c.display_name}</option>
                        ))}
                      </select>
                      <select
                        value={selectedScheme}
                        onChange={e => setSelectedScheme(e.target.value)}
                        className="v2-matchup-select"
                      >
                        {schemeOptions.map(s => (
                          <option key={s.name} value={s.name}>{s.display_name}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                {/* Right side: Formation Preview */}
                <div className="v2-formation-preview">
                  <div className="v2-formation-header">
                    <span className="v2-formation-title">Formation Preview</span>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <span className="v2-formation-badge offense">{currentConcept?.display_name || 'Offense'}</span>
                      <span className="v2-formation-badge defense">{currentScheme?.display_name || 'Defense'}</span>
                    </div>
                  </div>

                  <div className="v2-formation-canvas">
                    {/* Line of Scrimmage */}
                    <div className="v2-formation-los" />

                    {/* QB */}
                    <div
                      className="v2-formation-player qb"
                      style={{ left: '50%', bottom: '30px', transform: 'translateX(-50%)' }}
                    >
                      QB
                    </div>

                    {/* Receivers - ON or behind the LOS (LOS at bottom: 50px) */}
                    {currentConcept?.route_count && Array.from({ length: Math.min(currentConcept.route_count, 5) }).map((_, i) => {
                      const positions = [
                        { left: '12%', bottom: '48px' },   // Outside left - on LOS
                        { left: '88%', bottom: '48px' },   // Outside right - on LOS
                        { left: '30%', bottom: '45px' },   // Slot left - slightly back
                        { left: '70%', bottom: '45px' },   // Slot right - slightly back
                        { left: '50%', bottom: '38px' },   // TE/backfield
                      ];
                      const pos = positions[i] || positions[0];
                      return (
                        <div
                          key={i}
                          className="v2-formation-player receiver"
                          style={{ left: pos.left, bottom: pos.bottom, transform: 'translateX(-50%)' }}
                        >
                          {i + 1}
                        </div>
                      );
                    })}

                    {/* Defenders - across the LOS */}
                    {currentScheme && (
                      <>
                        {/* Deep safeties */}
                        {(currentScheme.name === 'cover_2' || currentScheme.name === 'cover_4') && (
                          <>
                            <div className="v2-formation-player defender" style={{ left: '30%', top: '15px', transform: 'translateX(-50%)' }}>S</div>
                            <div className="v2-formation-player defender" style={{ left: '70%', top: '15px', transform: 'translateX(-50%)' }}>S</div>
                          </>
                        )}
                        {currentScheme.name === 'cover_3' && (
                          <div className="v2-formation-player defender" style={{ left: '50%', top: '10px', transform: 'translateX(-50%)' }}>FS</div>
                        )}
                        {currentScheme.name === 'cover_1' && (
                          <div className="v2-formation-player defender" style={{ left: '50%', top: '25px', transform: 'translateX(-50%)' }}>FS</div>
                        )}

                        {/* Corners - press alignment across from WRs */}
                        <div className="v2-formation-player defender" style={{ left: '12%', bottom: '58px', transform: 'translateX(-50%)' }}>C</div>
                        <div className="v2-formation-player defender" style={{ left: '88%', bottom: '58px', transform: 'translateX(-50%)' }}>C</div>

                        {/* Linebackers - underneath */}
                        <div className="v2-formation-player defender" style={{ left: '35%', bottom: '85px', transform: 'translateX(-50%)' }}>L</div>
                        <div className="v2-formation-player defender" style={{ left: '65%', bottom: '85px', transform: 'translateX(-50%)' }}>L</div>
                      </>
                    )}
                  </div>

                  {/* Matchup Info Cards */}
                  <div className="v2-matchup-cards">
                    {currentConcept && (
                      <div className="v2-matchup-card offense">
                        <div className="v2-matchup-card-header">
                          <div className="v2-matchup-card-icon">🏈</div>
                          <span className="v2-matchup-card-title">{currentConcept.display_name}</span>
                        </div>
                        <div className="v2-matchup-card-meta">
                          <span>⏱ {currentConcept.timing}</span>
                          <span>📍 {currentConcept.formation}</span>
                        </div>
                        <div className="v2-matchup-card-desc">{currentConcept.description}</div>
                        <div className="v2-matchup-card-tags">
                          {currentConcept.coverage_beaters.map((beater, i) => (
                            <span key={i} className="v2-matchup-card-tag">Beats {beater}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {currentScheme && (
                      <div className="v2-matchup-card defense">
                        <div className="v2-matchup-card-header">
                          <div className="v2-matchup-card-icon">🛡️</div>
                          <span className="v2-matchup-card-title">{currentScheme.display_name}</span>
                        </div>
                        <div className="v2-matchup-card-meta">
                          <span>📋 {currentScheme.scheme_type}</span>
                        </div>
                        <div className="v2-matchup-card-desc">{currentScheme.description}</div>
                        <div className="v2-matchup-card-tags">
                          {currentScheme.strengths.slice(0, 2).map((str, i) => (
                            <span key={i} className="v2-matchup-card-tag">✓ {str}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  <button className="v2-run-matchup-btn" onClick={createMatchupSession}>
                    ▶ Run Simulation
                  </button>
                </div>
              </div>
            ) : (
              <>
                {/* Custom setup UI with unified PlayerConfig */}
                <div className="v2-config-section">
                  <h3>Offense</h3>
                  <div className="v2-route-config">
                    {offense.map((player, i) => (
                      <div key={i} className="v2-route-row">
                        <input type="text" value={player.name} onChange={e => {
                          const newOffense = [...offense];
                          newOffense[i] = { ...newOffense[i], name: e.target.value };
                          setOffense(newOffense);
                        }} placeholder="Name" style={{ width: 100 }} />
                        <select value={player.position} onChange={e => {
                          const newOffense = [...offense];
                          newOffense[i] = { ...newOffense[i], position: e.target.value };
                          setOffense(newOffense);
                        }} style={{ width: 60 }}>
                          <option value="QB">QB</option>
                          <option value="WR">WR</option>
                          <option value="RB">RB</option>
                          <option value="TE">TE</option>
                        </select>
                        {['WR', 'TE', 'RB'].includes(player.position) && (
                          <select value={player.route_type || ''} onChange={e => {
                            const newOffense = [...offense];
                            newOffense[i] = { ...newOffense[i], route_type: e.target.value };
                            setOffense(newOffense);
                          }}>
                            <option value="">Route...</option>
                            {routeOptions.map(opt => (
                              <option key={opt.type} value={opt.type}>{opt.name}</option>
                            ))}
                          </select>
                        )}
                        <input type="number" value={player.alignment_x} onChange={e => {
                          const newOffense = [...offense];
                          newOffense[i] = { ...newOffense[i], alignment_x: parseFloat(e.target.value) };
                          setOffense(newOffense);
                        }} style={{ width: 50 }} title="X" />
                        <input type="number" value={player.alignment_y ?? 0} onChange={e => {
                          const newOffense = [...offense];
                          newOffense[i] = { ...newOffense[i], alignment_y: parseFloat(e.target.value) };
                          setOffense(newOffense);
                        }} style={{ width: 50 }} title="Y" />
                        <button onClick={() => setOffense(offense.filter((_, j) => j !== i))}>×</button>
                      </div>
                    ))}
                    <button onClick={() => setOffense([...offense, {
                      name: "New WR", position: "WR", alignment_x: 15, alignment_y: 0,
                      route_type: "hitch", speed: 85, acceleration: 85, agility: 85, route_running: 80
                    }])}>+ Add Offensive Player</button>
                  </div>
                </div>

                <div className="v2-config-section">
                  <h3>Defense</h3>
                  <div className="v2-route-config">
                    {defense.map((player, i) => (
                      <div key={i} className="v2-route-row">
                        <input type="text" value={player.name} onChange={e => {
                          const newDefense = [...defense];
                          newDefense[i] = { ...newDefense[i], name: e.target.value };
                          setDefense(newDefense);
                        }} placeholder="Name" style={{ width: 100 }} />
                        <select value={player.position} onChange={e => {
                          const newDefense = [...defense];
                          newDefense[i] = { ...newDefense[i], position: e.target.value };
                          setDefense(newDefense);
                        }} style={{ width: 60 }}>
                          <option value="CB">CB</option>
                          <option value="FS">FS</option>
                          <option value="SS">SS</option>
                          <option value="MLB">MLB</option>
                          <option value="OLB">OLB</option>
                          <option value="DE">DE</option>
                          <option value="DT">DT</option>
                        </select>
                        <select value={player.coverage_type || ''} onChange={e => {
                          const newDefense = [...defense];
                          newDefense[i] = { ...newDefense[i], coverage_type: e.target.value };
                          setDefense(newDefense);
                        }}>
                          <option value="">Coverage...</option>
                          <option value="man">Man</option>
                          <option value="zone">Zone</option>
                        </select>
                        {player.coverage_type === 'man' ? (
                          <select value={player.man_target || ''} onChange={e => {
                            const newDefense = [...defense];
                            newDefense[i] = { ...newDefense[i], man_target: e.target.value };
                            setDefense(newDefense);
                          }}>
                            <option value="">Target...</option>
                            {offense.filter(p => p.position !== 'QB').map(p => (
                              <option key={p.name} value={p.name}>{p.name}</option>
                            ))}
                          </select>
                        ) : player.coverage_type === 'zone' && (
                          <select value={player.zone_type || ''} onChange={e => {
                            const newDefense = [...defense];
                            newDefense[i] = { ...newDefense[i], zone_type: e.target.value };
                            setDefense(newDefense);
                          }}>
                            <option value="">Zone...</option>
                            {zoneOptions.map(z => <option key={z.type} value={z.type}>{z.type}</option>)}
                          </select>
                        )}
                        <input type="number" value={player.alignment_x} onChange={e => {
                          const newDefense = [...defense];
                          newDefense[i] = { ...newDefense[i], alignment_x: parseFloat(e.target.value) };
                          setDefense(newDefense);
                        }} style={{ width: 50 }} title="X" />
                        <input type="number" value={player.alignment_y ?? 7} onChange={e => {
                          const newDefense = [...defense];
                          newDefense[i] = { ...newDefense[i], alignment_y: parseFloat(e.target.value) };
                          setDefense(newDefense);
                        }} style={{ width: 50 }} title="Depth" />
                        <button onClick={() => setDefense(defense.filter((_, j) => j !== i))}>×</button>
                      </div>
                    ))}
                    <button onClick={() => setDefense([...defense, {
                      name: "New DB", position: "CB", alignment_x: 15, alignment_y: 7,
                      coverage_type: "man", man_target: offense.find(p => p.position === 'WR')?.name,
                      speed: 88, acceleration: 86, agility: 88, man_coverage: 80, zone_coverage: 80, play_recognition: 75
                    }])}>+ Add Defensive Player</button>
                  </div>
                </div>

                <button className="v2-start-btn" onClick={createSession} disabled={offense.length === 0}>
                  Create Custom Session
                </button>
              </>
            )}

            {error && <div className="v2-error">{error}</div>}
          </div>
        ) : (
          /* ========== BROADCAST-STYLE GAMEPLAY VIEW ========== */
          <div className="broadcast-container">
            {/* Top Ticker Bar */}
            <div className="broadcast-ticker">
              <div className="ticker-left">
                <span className="ticker-label">PHASE</span>
                <span className="ticker-value phase">{simState?.is_complete ? 'COMPLETE' : simState?.is_paused ? 'PAUSED' : simState?.is_running ? 'LIVE' : 'READY'}</span>
              </div>
              <div className="ticker-center">
                <span className="ticker-time">{simState?.time.toFixed(2)}s</span>
                <span className="ticker-tick">TICK {simState?.tick}</span>
              </div>
              <div className="ticker-right">
                <span className={`ticker-connection ${isConnected ? 'live' : 'offline'}`}>
                  {isConnected ? '● LIVE' : '○ OFFLINE'}
                </span>
                <button className="ticker-exit" onClick={() => { wsRef.current?.close(); setSessionId(null); setSimState(null); }}>
                  ✕ EXIT
                </button>
              </div>
            </div>

            {/* Main Field Area */}
            <div className="broadcast-field">
              <V2SimCanvas
                simState={simState}
                selectedPlayerId={selectedPlayerId}
                onSelectPlayer={setSelectedPlayerId}
              />

              {/* Play Outcome Overlay */}
              {simState?.play_outcome && simState.play_outcome !== 'in_progress' && (
                <div className={`broadcast-outcome ${simState.play_outcome}`}>
                  <div className="outcome-label">
                    {simState.play_outcome === 'complete' && 'COMPLETE'}
                    {simState.play_outcome === 'incomplete' && 'INCOMPLETE'}
                    {simState.play_outcome === 'interception' && 'INTERCEPTED'}
                    {simState.play_outcome === 'tackled' && 'TACKLED'}
                  </div>
                </div>
              )}

              {/* Lower Third - Selected Player Info */}
              {selectedPlayer && (
                <div className="broadcast-lower-third">
                  <div className="lower-third-accent" />
                  <div className="lower-third-content">
                    <div className="lower-third-primary">
                      <span className={`player-type-badge ${selectedPlayer.player_type}`}>
                        {selectedPlayer.player_type.toUpperCase()}
                      </span>
                      <span className="player-name">{selectedPlayer.name}</span>
                    </div>
                    <div className="lower-third-stats">
                      <div className="stat">
                        <span className="stat-value">{selectedPlayer.speed.toFixed(1)}</span>
                        <span className="stat-label">YD/S</span>
                      </div>
                      <div className="stat">
                        <span className="stat-value">({selectedPlayer.x.toFixed(0)}, {selectedPlayer.y.toFixed(0)})</span>
                        <span className="stat-label">POS</span>
                      </div>
                      {selectedPlayer.player_type === 'receiver' && selectedPlayer.route_name && (
                        <div className="stat">
                          <span className="stat-value">{selectedPlayer.route_name.toUpperCase()}</span>
                          <span className="stat-label">ROUTE</span>
                        </div>
                      )}
                      {selectedPlayer.player_type === 'defender' && (
                        <div className="stat">
                          <span className="stat-value">{selectedPlayer.coverage_type?.toUpperCase() || '-'}</span>
                          <span className="stat-label">COVERAGE</span>
                        </div>
                      )}
                      {selectedPlayer.at_max_speed && (
                        <div className="stat highlight">
                          <span className="stat-value">MAX</span>
                          <span className="stat-label">SPEED</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Floating Controls */}
              <div className="broadcast-controls">
                <button className="ctrl-btn" onClick={reset} title="Reset (R)">
                  <span className="ctrl-icon">⏮</span>
                </button>
                <button className="ctrl-btn" onClick={step} title="Step (S)">
                  <span className="ctrl-icon">⏭</span>
                </button>
                {simState?.is_running && !simState?.is_paused ? (
                  <button className="ctrl-btn primary" onClick={pause} title="Pause (Space)">
                    <span className="ctrl-icon">⏸</span>
                  </button>
                ) : (
                  <button className="ctrl-btn primary" onClick={simState?.is_paused ? resume : start} title="Play (Space)">
                    <span className="ctrl-icon">▶</span>
                  </button>
                )}
              </div>

              {/* Player Roster Toggle */}
              <div className="broadcast-roster">
                <div className="roster-section offense">
                  <div className="roster-header">OFFENSE</div>
                  {receivers.slice(0, 5).map(player => (
                    <div
                      key={player.id}
                      className={`roster-player ${selectedPlayerId === player.id ? 'selected' : ''}`}
                      onClick={() => setSelectedPlayerId(player.id)}
                    >
                      <span className="roster-name">{player.name}</span>
                      <span className="roster-route">{player.route_name || '-'}</span>
                    </div>
                  ))}
                </div>
                <div className="roster-section defense">
                  <div className="roster-header">DEFENSE</div>
                  {defenderPlayers.slice(0, 5).map(player => (
                    <div
                      key={player.id}
                      className={`roster-player ${selectedPlayerId === player.id ? 'selected' : ''}`}
                      onClick={() => setSelectedPlayerId(player.id)}
                    >
                      <span className="roster-name">{player.name}</span>
                      <span className="roster-role">{player.coverage_type || '-'}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Keyboard Hints */}
            <div className="broadcast-hints">
              <span><kbd>SPACE</kbd> Play/Pause</span>
              <span><kbd>S</kbd> Step</span>
              <span><kbd>R</kbd> Reset</span>
              <span><kbd>TAB</kbd> Next Player</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
