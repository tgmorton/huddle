/**
 * SimAnalyzer - V2 Simulation Visualization with Analysis
 *
 * Two modes:
 * - Analysis Mode (default): Shows engine internals - traces, delays, pursuit lines
 * - View Mode: Clean broadcast-style visualization
 *
 * Uses ManagementV2 "ops center" design language:
 * - Berkeley Mono typography
 * - Sharp corners, amber accents
 * - Dark theme with corner brackets
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Eye, Activity, Play, Pause, RotateCcw, SkipForward, Zap, Map as MapIcon, LayoutGrid, ZoomIn, Terminal, Flag } from 'lucide-react';
import { SimCanvas } from './SimCanvas';
import { AnalysisPanel } from './AnalysisPanel';
import { SimWorkshopPanel, type LogEntry } from './SimWorkshopPanel';
import type {
  ViewMode,
  SimState,
  PlayerConfig,
  ConceptOption,
  SchemeOption,
  RouteOption,
  ZoneOption,
  CoverageAssignment,
  TraceEntry,
} from './types';
import './SimAnalyzer.css';

const API_BASE = 'http://localhost:8000/api/v1/v2-sim';
const WS_BASE = 'ws://localhost:8000/api/v1/v2-sim/ws';

// Run concept names (used to auto-detect run plays)
const RUN_CONCEPTS = [
  'inside_zone', 'inside_zone_left', 'inside_zone_right',
  'outside_zone', 'outside_zone_left', 'outside_zone_right',
  'power', 'power_left', 'power_right',
  'counter', 'counter_left', 'counter_right',
  'dive', 'dive_left', 'dive_right',
  'draw',
  'toss', 'toss_left', 'toss_right',
  'trap', 'trap_left', 'trap_right',
];

// Helper to detect if a concept is a run play
const isRunConcept = (concept: string): boolean => {
  return RUN_CONCEPTS.includes(concept.toLowerCase());
};

// Quick preset matchups for easy testing
const PRESET_MATCHUPS = [
  // Pass plays
  { concept: 'four_verts', scheme: 'cover_2', label: '4 Verts vs Cover 2', isRun: false },
  { concept: 'mesh', scheme: 'cover_1', label: 'Mesh vs Man', isRun: false },
  { concept: 'smash', scheme: 'cover_3', label: 'Smash vs Cover 3', isRun: false },
  { concept: 'slants', scheme: 'cover_2', label: 'Slants vs Cover 2', isRun: false },
  // Run plays
  { concept: 'inside_zone', scheme: 'cover_2', label: 'Inside Zone vs 4-3', isRun: true },
  { concept: 'outside_zone', scheme: 'cover_3', label: 'Outside Zone vs 3-4', isRun: true },
  { concept: 'power', scheme: 'cover_1', label: 'Power vs Cover 1', isRun: true },
  { concept: 'counter', scheme: 'cover_2', label: 'Counter vs Cover 2', isRun: true },
];

// Blocking scenario type
interface BlockingScenario {
  id: string;
  name: string;
  tier: number;
  description: string;
  expected: string;
  offense_count: number;
  defense_count: number;
  run_concept: string | null;
}

// Drive mode types
interface DrivePlayResult {
  concept: string;
  yards: number;
  outcome: string;
}

interface DriveState {
  down: number;
  distance: number;
  fieldPosition: number;
  plays: DrivePlayResult[];
}

type DrivePhase = 'setup' | 'selecting' | 'running' | 'result';

// Drive play options
const DRIVE_PLAYS = [
  { concept: 'slant_flat', label: 'Slant Flat', isRun: false },
  { concept: 'mesh', label: 'Mesh', isRun: false },
  { concept: 'four_verts', label: '4 Verts', isRun: false },
  { concept: 'smash', label: 'Smash', isRun: false },
  { concept: 'inside_zone', label: 'Inside Zone', isRun: true },
  { concept: 'outside_zone', label: 'Outside Zone', isRun: true },
  { concept: 'power', label: 'Power', isRun: true },
  { concept: 'draw', label: 'Draw', isRun: true },
];

// Helper functions for drive display
const getOrdinal = (n: number): string => {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return s[(v - 20) % 10] || s[v] || s[0];
};

const formatFieldPosition = (yardLine: number): string => {
  if (yardLine === 50) return 'MIDFIELD';
  if (yardLine < 50) return `OWN ${yardLine}`;
  return `OPP ${100 - yardLine}`;
};

const formatYards = (yards: number): string => {
  if (yards === 0) return 'NO GAIN';
  if (yards > 0) return `+${yards} YDS`;
  return `${yards} YDS`;
};

// Default player configurations
const DEFAULT_OFFENSE: PlayerConfig[] = [
  { name: "QB", position: "QB", alignment_x: 0, alignment_y: -5, throw_power: 90, throw_accuracy: 88 },
  { name: "Tyreek Hill", position: "WR", alignment_x: 20, alignment_y: 0, route_type: "slant", read_order: 1, speed: 99 },
  { name: "Davante Adams", position: "WR", alignment_x: -18, alignment_y: 0, route_type: "curl", read_order: 2, speed: 88 },
];

const DEFAULT_DEFENSE: PlayerConfig[] = [
  { name: "Sauce Gardner", position: "CB", alignment_x: 20, alignment_y: 7, coverage_type: "man", man_target: "Tyreek Hill", speed: 92, man_coverage: 99 },
  { name: "Jaire Alexander", position: "CB", alignment_x: -18, alignment_y: 7, coverage_type: "man", man_target: "Davante Adams", speed: 91, man_coverage: 95 },
];

export function SimAnalyzer() {
  // Mode state
  const [viewMode, setViewMode] = useState<ViewMode>('analysis');
  const [showZones, setShowZones] = useState(false);
  const [runZoom, setRunZoom] = useState(false);  // Zoomed view for run plays
  const [playbackSpeed, setPlaybackSpeed] = useState<1 | 0.5>(1);  // 1 = normal, 0.5 = half speed

  // Session state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [simState, setSimState] = useState<SimState | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Tick history for rewind/scrubbing
  const [tickHistory, setTickHistory] = useState<SimState[]>([]);
  const [viewingTick, setViewingTick] = useState<number | null>(null); // null = live

  // Selection state
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);

  // Setup state
  const [selectedConcept, setSelectedConcept] = useState('four_verts');
  const [selectedScheme, setSelectedScheme] = useState('cover_2');
  const [isRunPlay, setIsRunPlay] = useState(false);  // Track if selected play is a run
  const [conceptOptions, setConceptOptions] = useState<ConceptOption[]>([]);
  const [schemeOptions, setSchemeOptions] = useState<SchemeOption[]>([]);
  const [_routeOptions, setRouteOptions] = useState<RouteOption[]>([]);
  const [_zoneOptions, setZoneOptions] = useState<ZoneOption[]>([]);
  const [blockingScenarios, setBlockingScenarios] = useState<BlockingScenario[]>([]);
  const [selectedBlockingScenario, setSelectedBlockingScenario] = useState<string | null>(null);
  const [setupTab, setSetupTab] = useState<'matchups' | 'blocking' | 'drive'>('matchups');
  const [_offense] = useState<PlayerConfig[]>(DEFAULT_OFFENSE);
  const [_defense] = useState<PlayerConfig[]>(DEFAULT_DEFENSE);

  // Drive mode state
  const [driveState, setDriveState] = useState<DriveState | null>(null);
  const [drivePhase, setDrivePhase] = useState<DrivePhase>('setup');
  const [startingPosition, setStartingPosition] = useState(25);
  const [selectedDrivePlay, setSelectedDrivePlay] = useState('slants');
  const [lastPlayResult, setLastPlayResult] = useState<DrivePlayResult | null>(null);

  const wsRef = useRef<WebSocket | null>(null);

  // Timing diagnostics
  const lastTickTimeRef = useRef<number>(0);
  const tickIntervalsRef = useRef<number[]>([]);
  const [avgTickRate, setAvgTickRate] = useState<number | null>(null);

  // Workshop panel state
  const [workshopOpen, setWorkshopOpen] = useState(false);
  const [workshopLogs, setWorkshopLogs] = useState<LogEntry[]>([]);

  // Per-player trace accumulator (player_id -> traces)
  const [playerTraces, setPlayerTraces] = useState<Map<string, TraceEntry[]>>(new Map());

  // Helper to add log entries
  const addLog = useCallback((message: string, type: LogEntry['type'] = 'info') => {
    setWorkshopLogs(prev => [...prev, {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      timestamp: new Date(),
      message,
      type,
    }]);
  }, []);

  const clearLogs = useCallback(() => {
    setWorkshopLogs([]);
  }, []);

  // Fetch options on mount
  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/concepts`).then(r => r.json()),
      fetch(`${API_BASE}/run-concepts`).then(r => r.json()),
      fetch(`${API_BASE}/schemes`).then(r => r.json()),
      fetch(`${API_BASE}/routes`).then(r => r.json()),
      fetch(`${API_BASE}/zones`).then(r => r.json()),
      fetch(`${API_BASE}/blocking-scenarios`).then(r => r.ok ? r.json() : []),
    ]).then(([passConcepts, runConcepts, schemes, routes, zones, blockingScens]) => {
      // Combine pass and run concepts, marking run concepts
      const allConcepts = [
        ...passConcepts,
        ...runConcepts.map((rc: { name: string; display_name: string }) => ({
          ...rc,
          display_name: `[RUN] ${rc.display_name}`,
          isRun: true,
        })),
      ];
      setConceptOptions(allConcepts);
      setSchemeOptions(schemes);
      setRouteOptions(routes);
      setZoneOptions(zones);
      // Ensure blockingScens is an array
      const scenarios = Array.isArray(blockingScens) ? blockingScens : [];
      setBlockingScenarios(scenarios);
      // Default to first blocking scenario if available
      if (scenarios.length > 0) {
        setSelectedBlockingScenario(scenarios[0].id);
      }
    }).catch(err => console.error('Failed to fetch options:', err));
  }, []);

  // WebSocket connection
  const connectWebSocket = useCallback((sessionId: string) => {
    const ws = new WebSocket(`${WS_BASE}/${sessionId}`);
    addLog(`Connecting to session ${sessionId.slice(0, 8)}...`, 'ws');

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
      addLog('WebSocket connected', 'success');
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === 'state_sync') {
        setSimState(msg.payload);
        // Initialize tick history with initial state
        setTickHistory([msg.payload]);
        setViewingTick(null); // Start in live mode
        // Reset timing diagnostics
        lastTickTimeRef.current = 0;
        tickIntervalsRef.current = [];
        setAvgTickRate(null);
        // Select QB by default
        const qb = msg.payload.players.find((p: { player_type: string }) => p.player_type === 'qb');
        if (qb) setSelectedPlayerId(qb.id);
        addLog(`State sync: ${msg.payload.players?.length || 0} players`, 'ws');
      } else if (msg.type === 'tick') {
        // Measure tick timing
        const now = performance.now();
        if (lastTickTimeRef.current > 0) {
          const interval = now - lastTickTimeRef.current;
          tickIntervalsRef.current.push(interval);
          // Keep last 20 intervals for rolling average
          if (tickIntervalsRef.current.length > 20) {
            tickIntervalsRef.current.shift();
          }
          // Calculate average every 10 ticks
          if (msg.payload.tick % 10 === 0 && tickIntervalsRef.current.length > 0) {
            const avg = tickIntervalsRef.current.reduce((a, b) => a + b, 0) / tickIntervalsRef.current.length;
            setAvgTickRate(Math.round(avg));
          }
        }
        lastTickTimeRef.current = now;

        // Log new events
        if (msg.payload.events?.length > 0) {
          msg.payload.events.forEach((evt: { type: string; description: string }) => {
            addLog(`${evt.type}: ${evt.description}`, 'event');
          });
        }
        // Accumulate player traces from this tick
        const newTraces: TraceEntry[] = msg.payload.player_traces || [];
        if (newTraces.length > 0) {
          setPlayerTraces(prev => {
            const updated = new Map(prev);
            for (const trace of newTraces) {
              const existing = updated.get(trace.player_id) || [];
              // Limit per-player traces to last 200 entries
              const combined = [...existing, trace];
              updated.set(trace.player_id, combined.length > 200 ? combined.slice(-200) : combined);
            }
            return updated;
          });
        }
        setSimState(prev => {
          if (!prev) return null;
          const newState = {
            ...prev,
            tick: msg.payload.tick,
            time: msg.payload.time,
            phase: msg.payload.phase,
            players: msg.payload.players,
            ball: msg.payload.ball,
            play_outcome: msg.payload.play_outcome,
            ball_carrier_id: msg.payload.ball_carrier_id,
            tackle_position: msg.payload.tackle_position,
            tackler_id: msg.payload.tackler_id,
            events: msg.payload.events ? [...prev.events, ...msg.payload.events] : prev.events,
            qb_state: msg.payload.qb_state,
            qb_trace: msg.payload.qb_trace,
            // Update running state from tick so controls stay in sync
            is_running: msg.payload.is_running,
            is_paused: msg.payload.is_paused,
            is_complete: msg.payload.is_complete,
            // Run game state
            is_run_play: msg.payload.is_run_play ?? prev.is_run_play,
            run_concept: msg.payload.run_concept ?? prev.run_concept,
            designed_gap: msg.payload.designed_gap ?? prev.designed_gap,
          };
          // Append to tick history (limit to last 500 ticks to prevent memory issues)
          setTickHistory(history => {
            const updated = [...history, newState];
            return updated.length > 500 ? updated.slice(-500) : updated;
          });
          return newState;
        });
      } else if (msg.type === 'complete') {
        setSimState(msg.payload);
        addLog(`Play complete: ${msg.payload.play_outcome}`, 'success');
      } else if (msg.type === 'error') {
        setError(msg.message);
        addLog(`Error: ${msg.message}`, 'error');
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      addLog('WebSocket disconnected', 'warning');
    };
    ws.onerror = () => {
      setError('WebSocket connection failed');
      setIsConnected(false);
      addLog('WebSocket connection failed', 'error');
    };

    wsRef.current = ws;
  }, [addLog]);

  // Create matchup session
  const createSession = useCallback(async () => {
    setError(null);
    // Clear traces and history for new session
    setPlayerTraces(new Map());
    setTickHistory([]);
    setViewingTick(null);

    // Auto-detect run play from concept name as a safety check
    const detectedRunPlay = isRunConcept(selectedConcept);
    const finalIsRunPlay = isRunPlay || detectedRunPlay;

    addLog(`Creating session: ${selectedConcept} vs ${selectedScheme} (run=${finalIsRunPlay})`, 'info');

    try {
      const res = await fetch(`${API_BASE}/matchup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          concept: selectedConcept,
          scheme: selectedScheme,
          tick_rate_ms: playbackSpeed === 0.5 ? 100 : 50,
          max_time: 6.0,
          is_run_play: finalIsRunPlay,
        }),
      });

      if (!res.ok) throw new Error('Failed to create session');

      const session = await res.json();
      setSessionId(session.session_id);

      // Update isRunPlay state if we detected it
      if (detectedRunPlay && !isRunPlay) {
        setIsRunPlay(true);
        setRunZoom(true);
      }

      connectWebSocket(session.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      addLog(`Session creation failed: ${err}`, 'error');
    }
  }, [selectedConcept, selectedScheme, isRunPlay, connectWebSocket, addLog]);

  // Create blocking scenario session
  const createBlockingSession = useCallback(async () => {
    if (!selectedBlockingScenario) return;

    setError(null);
    const scenario = blockingScenarios.find(s => s.id === selectedBlockingScenario);
    addLog(`Creating blocking scenario: ${scenario?.name || selectedBlockingScenario}`, 'info');

    try {
      const res = await fetch(`${API_BASE}/blocking-scenario`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario_id: selectedBlockingScenario,
          tick_rate_ms: playbackSpeed === 0.5 ? 100 : 50,
          max_time: 4.0,
        }),
      });

      if (!res.ok) throw new Error('Failed to create blocking scenario session');

      const session = await res.json();
      setSessionId(session.session_id);

      // Enable run zoom for blocking scenarios (they're close-range)
      setRunZoom(true);

      connectWebSocket(session.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      addLog(`Blocking session creation failed: ${err}`, 'error');
    }
  }, [selectedBlockingScenario, blockingScenarios, connectWebSocket, addLog]);

  // Drive mode handlers
  const startDrive = useCallback(() => {
    setDriveState({
      down: 1,
      distance: 10,
      fieldPosition: startingPosition,
      plays: [],
    });
    setDrivePhase('selecting');
    setLastPlayResult(null);
    addLog(`Starting drive from ${formatFieldPosition(startingPosition)}`, 'info');
  }, [startingPosition, addLog]);

  const snapBall = useCallback(async () => {
    if (!driveState) return;
    setDrivePhase('running');
    setError(null);
    setPlayerTraces(new Map());
    setTickHistory([]);
    setViewingTick(null);

    const schemes = ['cover_2', 'cover_3', 'cover_1'];
    const randomScheme = schemes[Math.floor(Math.random() * schemes.length)];
    const playInfo = DRIVE_PLAYS.find(p => p.concept === selectedDrivePlay);

    addLog(`Snap: ${selectedDrivePlay} vs ${randomScheme}`, 'info');

    try {
      const res = await fetch(`${API_BASE}/matchup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          concept: selectedDrivePlay,
          scheme: randomScheme,
          tick_rate_ms: playbackSpeed === 0.5 ? 100 : 50,
          max_time: 6.0,
          is_run_play: playInfo?.isRun ?? false,
        }),
      });

      if (!res.ok) throw new Error('Failed to create play session');

      const session = await res.json();
      setSessionId(session.session_id);
      if (playInfo?.isRun) setRunZoom(true);
      connectWebSocket(session.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setDrivePhase('selecting');
      addLog(`Play failed: ${err}`, 'error');
    }
  }, [driveState, selectedDrivePlay, connectWebSocket, addLog]);

  const handlePlayComplete = useCallback((outcome: string, yardage: number) => {
    if (!driveState) return;

    const result: DrivePlayResult = {
      concept: selectedDrivePlay,
      yards: yardage,
      outcome,
    };
    setLastPlayResult(result);
    addLog(`Play complete: ${formatYards(yardage)} (${outcome})`, 'success');

    setDriveState(prev => {
      if (!prev) return null;

      const newFieldPos = Math.min(100, Math.max(0, prev.fieldPosition + yardage));
      const newDistance = prev.distance - yardage;

      if (newFieldPos >= 100) {
        addLog('TOUCHDOWN!', 'success');
        return { ...prev, fieldPosition: 100, plays: [...prev.plays, result] };
      }

      if (newDistance <= 0) {
        addLog('First down!', 'info');
        return { ...prev, down: 1, distance: 10, fieldPosition: newFieldPos, plays: [...prev.plays, result] };
      }

      if (prev.down >= 4) {
        addLog('Turnover on downs', 'warning');
        return { ...prev, down: 5, fieldPosition: newFieldPos, plays: [...prev.plays, result] };
      }

      return {
        ...prev,
        down: prev.down + 1,
        distance: newDistance,
        fieldPosition: newFieldPos,
        plays: [...prev.plays, result],
      };
    });

    setDrivePhase('result');
  }, [driveState, selectedDrivePlay, addLog]);

  const nextPlay = useCallback(() => {
    if (wsRef.current) wsRef.current.close();
    setSessionId(null);
    setSimState(null);
    setRunZoom(false);  // Reset zoom for next play
    setDrivePhase('selecting');
  }, []);

  const endDrive = useCallback(() => {
    if (wsRef.current) wsRef.current.close();
    setSessionId(null);
    setSimState(null);
    setDriveState(null);
    setDrivePhase('setup');
    setLastPlayResult(null);
    addLog('Drive ended', 'info');
  }, [addLog]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // Send command to WebSocket
  const sendCommand = (type: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type }));
    }
  };

  const start = () => {
    setViewingTick(null); // Return to live mode when starting
    sendCommand('start');
  };
  const pause = () => sendCommand('pause');
  const resume = () => {
    setViewingTick(null); // Return to live mode when resuming
    sendCommand('resume');
  };
  const reset = () => {
    setTickHistory([]);
    setViewingTick(null);
    setPlayerTraces(new Map()); // Clear accumulated traces
    sendCommand('reset');
  };
  const step = () => {
    setViewingTick(null); // Return to live mode when stepping
    sendCommand('step');
  };

  // Computed display state - either live or historical based on viewingTick
  const displayState = viewingTick !== null
    ? tickHistory.find(s => s.tick === viewingTick) ?? simState
    : simState;

  // Jump to a specific tick in history
  const jumpToTick = (tick: number) => {
    if (tickHistory.some(s => s.tick === tick)) {
      setViewingTick(tick);
      // Pause the simulation when scrubbing
      pause();
    }
  };

  // Return to live mode
  const goLive = () => setViewingTick(null);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Tab toggles mode
      if (e.key === 'Tab' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        setViewMode(v => v === 'analysis' ? 'view' : 'analysis');
        return;
      }

      if (!isConnected) return;

      switch (e.key) {
        case ' ':
          e.preventDefault();
          if (simState?.is_running && !simState?.is_paused) pause();
          else if (simState?.is_paused) resume();
          else start();
          break;
        case 's':
          step();
          break;
        case 'r':
          reset();
          break;
        case 'ArrowRight':
        case 'ArrowLeft':
          // Cycle through players
          if (simState?.players) {
            const currentIdx = simState.players.findIndex(p => p.id === selectedPlayerId);
            const dir = e.key === 'ArrowRight' ? 1 : -1;
            const nextIdx = (currentIdx + dir + simState.players.length) % simState.players.length;
            setSelectedPlayerId(simState.players[nextIdx].id);
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isConnected, simState, selectedPlayerId]);

  // Watch for play completion in drive mode
  useEffect(() => {
    if (drivePhase === 'running' && simState?.is_complete && simState?.play_outcome) {
      let yards = 0;
      const outcome = simState.play_outcome;

      // Calculate yards based on outcome
      if (outcome === 'tackled' && simState.tackle_position) {
        yards = Math.round(simState.tackle_position.y);
      } else if (outcome === 'complete' && simState.tackle_position) {
        // Pass complete with RAC - use tackle position
        yards = Math.round(simState.tackle_position.y);
      } else if (outcome === 'complete') {
        // Pass complete, no tackle yet - find catcher position
        const catcher = simState.players.find(p => p.has_ball && p.player_type === 'receiver');
        if (catcher) yards = Math.round(catcher.y);
      } else if (outcome === 'incomplete' || outcome === 'interception') {
        yards = 0;
      } else if (outcome === 'sack') {
        // Sack - negative yards, find QB position
        const qb = simState.players.find(p => p.player_type === 'qb');
        if (qb) yards = Math.round(qb.y);  // Will be negative
      } else if (outcome === 'touchdown') {
        // TD - use endzone
        yards = 100 - (simState.tackle_position?.y ?? 0);
      }

      handlePlayComplete(outcome, yards);
    }
  }, [drivePhase, simState?.is_complete, simState?.play_outcome, simState?.tackle_position, simState?.players, handlePlayComplete]);

  // Derive coverage assignments for analysis panel
  const coverageAssignments: CoverageAssignment[] = simState?.players
    .filter(p => p.player_type === 'defender')
    .map(defender => {
      const target = defender.man_target_id
        ? simState.players.find(p => p.id === defender.man_target_id)
        : null;

      // Calculate separation if man coverage
      let separation: number | undefined;
      if (target) {
        const dx = target.x - defender.x;
        const dy = target.y - defender.y;
        separation = Math.sqrt(dx * dx + dy * dy);
      }

      return {
        defender_id: defender.id,
        defender_name: defender.name,
        coverage_type: defender.coverage_type || 'man',
        target_id: defender.man_target_id,
        target_name: target?.name,
        separation,
        zone_type: defender.zone_type,
        is_triggered: defender.has_triggered,
        phase: defender.coverage_phase,
        has_recognized_break: defender.has_recognized_break,
        recognition_progress: defender.recognition_delay && defender.recognition_timer
          ? defender.recognition_timer / defender.recognition_delay
          : undefined,
      };
    }) || [];

  const selectedPlayer = simState?.players.find(p => p.id === selectedPlayerId);

  // Debug: log trace state changes
  useEffect(() => {
    console.log('[TRACES] playerTraces changed, size:', playerTraces.size,
      'selectedPlayer:', selectedPlayer?.name,
      'traces for selected:', selectedPlayer ? playerTraces.get(selectedPlayer.id)?.length : 'n/a');
  }, [playerTraces, selectedPlayer]);

  // Exit session
  const exitSession = () => {
    wsRef.current?.close();
    setSessionId(null);
    setSimState(null);
    setIsConnected(false);
  };

  return (
    <div className={`sim-analyzer ${viewMode === 'analysis' ? 'analysis-mode' : 'view-mode'} ${workshopOpen ? 'sim-analyzer--workshop-open' : ''}`}>
      {/* Header */}
      <header className="sim-analyzer__header">
        <div className="sim-analyzer__header-left">
          <Link to="/manage-v2" className="sim-analyzer__nav-link" title="Go to ManagementV2">
            <LayoutGrid size={16} />
          </Link>
          <span className="sim-analyzer__title">SIM ANALYZER</span>
          {sessionId && (
            <span className="sim-analyzer__session">
              {isConnected ? (
                <span className="status-dot status-dot--live" />
              ) : (
                <span className="status-dot status-dot--offline" />
              )}
              {simState?.phase || 'READY'}
            </span>
          )}
        </div>

        <div className="sim-analyzer__header-center">
          {simState && (
            <>
              <span className="sim-analyzer__time">{simState.time.toFixed(2)}s</span>
              <span className="sim-analyzer__tick">T{simState.tick}</span>
            </>
          )}
        </div>

        <div className="sim-analyzer__header-right">
          {/* Run zoom toggle (only in analysis mode) */}
          {sessionId && viewMode === 'analysis' && (
            <button
              className={`sim-analyzer__toggle-btn ${runZoom ? 'active' : ''}`}
              onClick={() => setRunZoom(z => !z)}
              title="Zoom in on line for run game analysis"
            >
              <ZoomIn size={14} />
              <span>RUN</span>
            </button>
          )}

          {/* Zone toggle (only in analysis mode) */}
          {sessionId && viewMode === 'analysis' && (
            <button
              className={`sim-analyzer__toggle-btn ${showZones ? 'active' : ''}`}
              onClick={() => setShowZones(z => !z)}
              title="Toggle zone boundaries"
            >
              <MapIcon size={14} />
              <span>ZONES</span>
            </button>
          )}

          {/* Workshop toggle (engine debug panel) */}
          {sessionId && (
            <button
              className={`sim-analyzer__workshop-toggle ${workshopOpen ? 'active' : ''}`}
              onClick={() => setWorkshopOpen(w => !w)}
              title="Toggle engine debug panel"
            >
              <Terminal size={14} />
              <span>ENGINE</span>
            </button>
          )}

          {sessionId && (
            <button className="sim-analyzer__exit-btn" onClick={exitSession}>
              EXIT
            </button>
          )}
          <div className="mode-toggle">
            <button
              className={`mode-toggle__btn ${viewMode === 'view' ? 'active' : ''}`}
              onClick={() => setViewMode('view')}
              title="Clean broadcast view"
            >
              <Eye size={14} />
              <span>VIEW</span>
            </button>
            <button
              className={`mode-toggle__btn ${viewMode === 'analysis' ? 'active' : ''}`}
              onClick={() => setViewMode('analysis')}
              title="Analysis mode with engine internals"
            >
              <Activity size={14} />
              <span>ANALYSIS</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="sim-analyzer__body">
        {/* Drive Mode - Play Selection Screen */}
        {driveState && drivePhase === 'selecting' && !sessionId ? (
          <div className="sim-analyzer__drive-select">
            <div className="drive-scoreboard bracketed">
              <div className="drive-scoreboard__situation">
                {driveState.down}{getOrdinal(driveState.down)} & {driveState.distance}
              </div>
              <div className="drive-scoreboard__position">{formatFieldPosition(driveState.fieldPosition)}</div>
            </div>

            <div className="drive-playcall bracketed">
              <div className="drive-playcall__header">CALL YOUR PLAY</div>
              <div className="drive-playcall__grid">
                {DRIVE_PLAYS.map(play => (
                  <button
                    key={play.concept}
                    className={`drive-play-btn ${play.isRun ? 'run' : 'pass'} ${selectedDrivePlay === play.concept ? 'active' : ''}`}
                    onClick={() => setSelectedDrivePlay(play.concept)}
                  >
                    <span className="drive-play-btn__type">{play.isRun ? 'RUN' : 'PASS'}</span>
                    <span className="drive-play-btn__name">{play.label}</span>
                  </button>
                ))}
              </div>
              <button className="drive-snap-btn" onClick={snapBall}>
                <Play size={16} />
                SNAP
              </button>
            </div>

            {driveState.plays.length > 0 && (
              <div className="drive-history bracketed">
                <div className="drive-history__header">DRIVE SUMMARY</div>
                <div className="drive-history__list">
                  {driveState.plays.map((play, i) => (
                    <div key={i} className={`drive-history__item ${play.yards > 0 ? 'gain' : play.yards < 0 ? 'loss' : ''}`}>
                      <span className="drive-history__num">{i + 1}</span>
                      <span className="drive-history__name">{play.concept.replace(/_/g, ' ')}</span>
                      <span className="drive-history__yards">{formatYards(play.yards)}</span>
                    </div>
                  ))}
                </div>
                <div className="drive-history__total">
                  {driveState.plays.reduce((sum, p) => sum + p.yards, 0)} total yards
                </div>
              </div>
            )}

            <button className="drive-end-btn" onClick={endDrive}>
              END DRIVE
            </button>
          </div>
        ) : !sessionId ? (
          // Setup View
          <div className="sim-analyzer__setup">
            <div className="setup-panel bracketed">
              {/* Tab selector */}
              <div className="setup-panel__tabs">
                <button
                  className={`setup-panel__tab ${setupTab === 'matchups' ? 'active' : ''}`}
                  onClick={() => setSetupTab('matchups')}
                >
                  <Zap size={14} />
                  MATCHUPS
                </button>
                <button
                  className={`setup-panel__tab ${setupTab === 'blocking' ? 'active' : ''}`}
                  onClick={() => setSetupTab('blocking')}
                >
                  <Activity size={14} />
                  BLOCKING TESTS
                </button>
                <button
                  className={`setup-panel__tab ${setupTab === 'drive' ? 'active' : ''}`}
                  onClick={() => setSetupTab('drive')}
                >
                  <Flag size={14} />
                  DRIVE MODE
                </button>
              </div>

              {setupTab === 'matchups' ? (
                <>
                  <div className="setup-panel__section">
                    <div className="setup-panel__label">QUICK PRESETS</div>
                    <div className="preset-grid">
                      {PRESET_MATCHUPS.map((preset, i) => (
                        <button
                          key={i}
                          className={`preset-btn ${preset.isRun ? 'preset-btn--run' : ''} ${
                            selectedConcept === preset.concept && selectedScheme === preset.scheme
                              ? 'active'
                              : ''
                          }`}
                          onClick={() => {
                            setSelectedConcept(preset.concept);
                            setSelectedScheme(preset.scheme);
                            setIsRunPlay(preset.isRun);
                            // Auto-enable run zoom for run plays
                            if (preset.isRun) {
                              setRunZoom(true);
                            }
                          }}
                        >
                          {preset.isRun && <span className="preset-tag">RUN</span>}
                          {preset.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="setup-panel__section">
                    <div className="setup-panel__label">CUSTOM MATCHUP</div>
                    <div className="setup-panel__row">
                      <label>Offense</label>
                      <select
                        value={selectedConcept}
                        onChange={e => {
                          const concept = e.target.value;
                          setSelectedConcept(concept);
                          // Check if selected concept has isRun flag or detect from name
                          const selectedOption = conceptOptions.find(c => c.name === concept);
                          const isRun = selectedOption?.isRun || isRunConcept(concept);
                          setIsRunPlay(isRun);
                          if (isRun) {
                            setRunZoom(true);
                          }
                        }}
                      >
                        {conceptOptions.map(c => (
                          <option key={c.name} value={c.name}>{c.display_name}</option>
                        ))}
                      </select>
                    </div>
                    <div className="setup-panel__row">
                      <label>Defense</label>
                      <select
                        value={selectedScheme}
                        onChange={e => setSelectedScheme(e.target.value)}
                      >
                        {schemeOptions.map(s => (
                          <option key={s.name} value={s.name}>{s.display_name}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <button className="setup-panel__run-btn" onClick={createSession}>
                    <Play size={16} />
                    RUN SIMULATION
                  </button>
                </>
              ) : setupTab === 'blocking' ? (
                <>
                  <div className="setup-panel__section">
                    <div className="setup-panel__label">BLOCKING BEHAVIOR TESTS</div>
                    <p className="setup-panel__desc">
                      Isolated scenarios to test OL/DL blocking mechanics
                    </p>
                  </div>

                  {/* All scenarios in a single grid */}
                  <div className="blocking-grid">
                    {blockingScenarios.map(scenario => (
                      <button
                        key={scenario.id}
                        className={`blocking-btn ${selectedBlockingScenario === scenario.id ? 'active' : ''}`}
                        onClick={() => setSelectedBlockingScenario(scenario.id)}
                        title={scenario.description}
                      >
                        <div className="blocking-btn__header">
                          <span className="blocking-btn__name">{scenario.name}</span>
                          <span className="blocking-btn__count">
                            {scenario.offense_count}v{scenario.defense_count}
                          </span>
                        </div>
                        {scenario.run_concept && (
                          <span className="blocking-btn__concept">
                            {scenario.run_concept.replace(/_/g, ' ')}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>

                  <button
                    className="setup-panel__run-btn"
                    onClick={createBlockingSession}
                    disabled={!selectedBlockingScenario}
                  >
                    <Play size={16} />
                    RUN BLOCKING TEST
                  </button>
                </>
              ) : (
                /* Drive Mode Setup */
                <>
                  <div className="setup-panel__section">
                    <div className="setup-panel__label">DRIVE SIMULATOR</div>
                    <p className="setup-panel__desc">
                      Run a full drive with down & distance tracking
                    </p>
                  </div>

                  <div className="setup-panel__section">
                    <div className="setup-panel__label">STARTING POSITION</div>
                    <div className="drive-position-grid">
                      {[
                        { value: 25, label: 'OWN 25' },
                        { value: 50, label: 'MIDFIELD' },
                        { value: 75, label: 'OPP 25' },
                        { value: 90, label: 'GOAL LINE' },
                      ].map(pos => (
                        <button
                          key={pos.value}
                          className={`drive-position-btn ${startingPosition === pos.value ? 'active' : ''}`}
                          onClick={() => setStartingPosition(pos.value)}
                        >
                          {pos.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="drive-info-row">
                    <div className="drive-info-item">
                      <span className="drive-info-label">PLAYS</span>
                      <span className="drive-info-value">{DRIVE_PLAYS.length}</span>
                    </div>
                    <div className="drive-info-item">
                      <span className="drive-info-label">DEFENSE</span>
                      <span className="drive-info-value">AUTO</span>
                    </div>
                  </div>

                  <button className="setup-panel__run-btn" onClick={startDrive}>
                    <Flag size={16} />
                    START DRIVE
                  </button>
                </>
              )}

              {error && <div className="setup-panel__error">{error}</div>}
            </div>
          </div>
        ) : (
          // Simulation View
          <>
            <div className="sim-analyzer__canvas-container">
              <SimCanvas
                simState={displayState}
                analysisMode={viewMode === 'analysis'}
                showZones={showZones}
                runZoom={runZoom}
                selectedPlayerId={selectedPlayerId}
                onSelectPlayer={setSelectedPlayerId}
                tacklerId={displayState?.tackler_id}
              />

              {/* Play outcome badge (non-blocking, corner position) - hide in drive mode */}
              {simState?.play_outcome && simState.play_outcome !== 'in_progress' && !driveState && (
                <div className={`outcome-badge outcome-badge--${simState.play_outcome}`}>
                  {simState.play_outcome.toUpperCase().replace('_', ' ')}
                </div>
              )}

              {/* Drive Mode - Scoreboard overlay */}
              {driveState && (
                <div className="drive-scoreboard-overlay bracketed">
                  <div className="drive-scoreboard-overlay__down">
                    {driveState.fieldPosition >= 100 ? (
                      <span className="td">TOUCHDOWN</span>
                    ) : driveState.down > 4 ? (
                      <span className="turnover">TURNOVER</span>
                    ) : (
                      <>{driveState.down}{getOrdinal(driveState.down)} & {driveState.distance}</>
                    )}
                  </div>
                  <div className="drive-scoreboard-overlay__pos">{formatFieldPosition(driveState.fieldPosition)}</div>
                </div>
              )}

              {/* Drive Mode - Result overlay */}
              {driveState && drivePhase === 'result' && lastPlayResult && (
                <div className="drive-result-overlay bracketed">
                  <div className="drive-result-overlay__yards">{formatYards(lastPlayResult.yards)}</div>
                  <div className="drive-result-overlay__outcome">{lastPlayResult.outcome.toUpperCase()}</div>
                  {driveState.fieldPosition >= 100 ? (
                    <button className="drive-result-overlay__btn td" onClick={endDrive}>NEW DRIVE</button>
                  ) : driveState.down > 4 ? (
                    <button className="drive-result-overlay__btn turnover" onClick={endDrive}>END DRIVE</button>
                  ) : (
                    <button className="drive-result-overlay__btn" onClick={nextPlay}>NEXT PLAY</button>
                  )}
                </div>
              )}
            </div>

            {/* Analysis Panel (only in analysis mode) */}
            {viewMode === 'analysis' && (
              <AnalysisPanel
                simState={displayState}
                selectedPlayer={selectedPlayer || null}
                coverageAssignments={coverageAssignments}
                onSelectPlayer={setSelectedPlayerId}
                playerTraces={playerTraces}
              />
            )}
          </>
        )}
      </div>

      {/* Controls Footer */}
      {sessionId && (
        <footer className="sim-analyzer__controls">
          <div className="controls-group">
            <button className="ctrl-btn" onClick={reset} title="Reset (R)">
              <RotateCcw size={16} />
            </button>
            <button className="ctrl-btn" onClick={step} title="Step (S)">
              <SkipForward size={16} />
            </button>
            {simState?.is_running && !simState?.is_paused ? (
              <button className="ctrl-btn ctrl-btn--primary" onClick={pause} title="Pause (Space)">
                <Pause size={16} />
              </button>
            ) : (
              <button
                className="ctrl-btn ctrl-btn--primary"
                onClick={simState?.is_paused ? resume : start}
                title="Play (Space)"
              >
                <Play size={16} />
              </button>
            )}
            <button
              className={`ctrl-btn ${playbackSpeed === 0.5 ? 'ctrl-btn--active' : ''}`}
              onClick={() => setPlaybackSpeed(prev => prev === 1 ? 0.5 : 1)}
              title="Toggle Half Speed"
            >
              {playbackSpeed === 0.5 ? '0.5×' : '1×'}
            </button>
            {avgTickRate !== null && (
              <span
                className={`tick-rate-indicator ${avgTickRate > (playbackSpeed === 0.5 ? 110 : 60) ? 'slow' : ''}`}
                title={`Actual tick rate: ${avgTickRate}ms (expected: ${playbackSpeed === 0.5 ? 100 : 50}ms)`}
              >
                {avgTickRate}ms
              </span>
            )}
          </div>

          {/* Timeline Scrubber */}
          {tickHistory.length > 1 && (
            <div className="controls-timeline">
              <input
                type="range"
                min={tickHistory[0]?.tick ?? 0}
                max={tickHistory[tickHistory.length - 1]?.tick ?? 0}
                value={viewingTick ?? simState?.tick ?? 0}
                onChange={(e) => jumpToTick(Number(e.target.value))}
                className="timeline-slider"
              />
              <span className="timeline-tick">
                {viewingTick !== null ? (
                  <>
                    Tick {viewingTick} ({displayState?.time?.toFixed(2)}s)
                    <button className="timeline-live-btn" onClick={goLive}>
                      LIVE
                    </button>
                  </>
                ) : (
                  <>
                    Tick {simState?.tick ?? 0} ({simState?.time?.toFixed(2) ?? '0.00'}s)
                    <span className="timeline-live-indicator">LIVE</span>
                  </>
                )}
              </span>
            </div>
          )}

          <div className="controls-info">
            <span className="controls-hint">
              <kbd>Space</kbd> Play/Pause
            </span>
            <span className="controls-hint">
              <kbd>Tab</kbd> Toggle Mode
            </span>
            <span className="controls-hint">
              <kbd>←</kbd><kbd>→</kbd> Select Player
            </span>
          </div>
        </footer>
      )}

      {/* Engine Workshop Panel */}
      <SimWorkshopPanel
        isOpen={workshopOpen}
        onClose={() => setWorkshopOpen(false)}
        simState={displayState}
        isConnected={isConnected}
        logs={workshopLogs}
        onClearLogs={clearLogs}
      />
    </div>
  );
}
