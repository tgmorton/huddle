/**
 * Sim3D - Three.js 3D Football Simulation Visualizer
 *
 * A 3D broadcast-style view of the simulation with:
 * - Camera presets (Broadcast, Overhead)
 * - Toggleable analysis overlays
 * - Same setup UI as SimAnalyzer
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Terminal } from 'lucide-react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type {
  SimState,
  PlayerState,
  ConceptOption,
  SchemeOption,
} from '../SimAnalyzer/types';
import './Sim3D.css';

const API_BASE = 'http://localhost:8000/api/v1/v2-sim';
const WS_BASE = 'ws://localhost:8000/api/v1/v2-sim/ws';

// Run concept detection
const RUN_CONCEPTS = [
  'inside_zone', 'inside_zone_left', 'inside_zone_right',
  'outside_zone', 'outside_zone_left', 'outside_zone_right',
  'power', 'power_left', 'power_right',
  'counter', 'counter_left', 'counter_right',
  'dive', 'dive_left', 'dive_right',
  'draw', 'toss', 'toss_left', 'toss_right',
];

const isRunConcept = (concept: string): boolean => {
  return RUN_CONCEPTS.includes(concept.toLowerCase());
};

// Preset matchups for quick selection
const PRESET_MATCHUPS = [
  { concept: 'four_verts', scheme: 'cover_2', label: '4V vs C2' },
  { concept: 'mesh', scheme: 'cover_1', label: 'Mesh vs Man' },
  { concept: 'slants', scheme: 'cover_3', label: 'Slants vs C3' },
  { concept: 'inside_zone', scheme: 'cover_2', label: 'IZ Run' },
  { concept: 'power', scheme: 'cover_1', label: 'Power Run' },
];

// Camera presets
const CAMERA_PRESETS = {
  broadcast: { position: [35, 25, 45], target: [0, 0, 10], label: 'Broadcast' },
  overhead: { position: [0, 60, 10], target: [0, 0, 10], label: 'Overhead' },
};

// Player colors
const PLAYER_COLORS = {
  offense: 0xf59e0b,
  offenseLight: 0xfbbf24,
  defense: 0xef4444,
  defenseLight: 0xf87171,
  qb: 0xfbbf24,
  rb: 0x60a5fa,
  ol: 0xd1d5db,
  dl: 0xb91c1c,
};

export function Sim3D() {
  // Refs for Three.js objects
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const playerMeshesRef = useRef<Map<string, THREE.Group>>(new Map());
  const ballMeshRef = useRef<THREE.Mesh | null>(null);
  const animationFrameRef = useRef<number>(0);
  const wsRef = useRef<WebSocket | null>(null);

  // State
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [simState, setSimState] = useState<SimState | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Setup state
  const [selectedConcept, setSelectedConcept] = useState('four_verts');
  const [selectedScheme, setSelectedScheme] = useState('cover_2');
  const [conceptOptions, setConceptOptions] = useState<ConceptOption[]>([]);
  const [schemeOptions, setSchemeOptions] = useState<SchemeOption[]>([]);

  // View state
  const [currentCamera, setCurrentCamera] = useState<'broadcast' | 'overhead'>('overhead');
  const [showEngine, setShowEngine] = useState(false);

  // Fetch options on mount
  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/concepts`).then(r => r.json()),
      fetch(`${API_BASE}/run-concepts`).then(r => r.json()),
      fetch(`${API_BASE}/schemes`).then(r => r.json()),
    ]).then(([passConcepts, runConcepts, schemes]) => {
      const allConcepts = [
        ...passConcepts,
        ...runConcepts.map((rc: ConceptOption) => ({
          ...rc,
          display_name: `[RUN] ${rc.display_name}`,
          isRun: true,
        })),
      ];
      setConceptOptions(allConcepts);
      setSchemeOptions(schemes);
    }).catch(err => console.error('Failed to fetch options:', err));
  }, []);

  // Initialize Three.js scene
  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a1628);
    scene.fog = new THREE.Fog(0x0a1628, 80, 200);
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
    const preset = CAMERA_PRESETS.overhead;
    camera.position.set(...(preset.position as [number, number, number]));
    cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.1;
    controls.minDistance = 15;
    controls.maxDistance = 120;
    controls.target.set(...(preset.target as [number, number, number]));
    controlsRef.current = controls;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xffffff, 0.8);
    sunLight.position.set(30, 50, 30);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 150;
    sunLight.shadow.camera.left = -60;
    sunLight.shadow.camera.right = 60;
    sunLight.shadow.camera.top = 60;
    sunLight.shadow.camera.bottom = -60;
    scene.add(sunLight);

    // Stadium lights
    const light1 = new THREE.PointLight(0xffffee, 0.5, 100);
    light1.position.set(-30, 40, -20);
    scene.add(light1);
    const light2 = new THREE.PointLight(0xffffee, 0.5, 100);
    light2.position.set(30, 40, -20);
    scene.add(light2);

    // Field
    createField(scene);

    // Ball (initially hidden)
    const ballGeom = new THREE.SphereGeometry(0.3, 16, 16);
    ballGeom.scale(1, 0.6, 0.6);
    const ballMat = new THREE.MeshStandardMaterial({ color: 0x8b4513, roughness: 0.4 });
    const ball = new THREE.Mesh(ballGeom, ballMat);
    ball.castShadow = true;
    ball.visible = false;
    scene.add(ball);
    ballMeshRef.current = ball;

    // Animation loop
    const animate = () => {
      animationFrameRef.current = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Handle resize
    const handleResize = () => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameRef.current);
      renderer.dispose();
      container.removeChild(renderer.domElement);
    };
  }, []);

  // Create static field elements
  const createField = (scene: THREE.Scene) => {
    // Field plane
    const fieldGeom = new THREE.PlaneGeometry(53.33, 100);
    const fieldMat = new THREE.MeshStandardMaterial({ color: 0x1a5c2e, roughness: 0.8 });
    const field = new THREE.Mesh(fieldGeom, fieldMat);
    field.rotation.x = -Math.PI / 2;
    field.receiveShadow = true;
    scene.add(field);

    // Yard lines
    const lineMat = new THREE.LineBasicMaterial({ color: 0xffffff, opacity: 0.5, transparent: true });
    const losMat = new THREE.LineBasicMaterial({ color: 0xf59e0b, linewidth: 2 });

    for (let z = -40; z <= 40; z += 5) {
      const points = [
        new THREE.Vector3(-26.5, 0.02, z),
        new THREE.Vector3(26.5, 0.02, z),
      ];
      const geom = new THREE.BufferGeometry().setFromPoints(points);
      const line = new THREE.Line(geom, z === 0 ? losMat : lineMat);
      scene.add(line);
    }

    // End zones
    const ezGeom = new THREE.PlaneGeometry(53.33, 10);
    const ezMat1 = new THREE.MeshStandardMaterial({ color: 0x8b0000, roughness: 0.8 });
    const ez1 = new THREE.Mesh(ezGeom, ezMat1);
    ez1.rotation.x = -Math.PI / 2;
    ez1.position.set(0, 0.001, -55);
    scene.add(ez1);

    const ezMat2 = new THREE.MeshStandardMaterial({ color: 0x00008b, roughness: 0.8 });
    const ez2 = new THREE.Mesh(ezGeom, ezMat2);
    ez2.rotation.x = -Math.PI / 2;
    ez2.position.set(0, 0.001, 55);
    scene.add(ez2);
  };

  // Create player mesh
  const createPlayerMesh = (player: PlayerState): THREE.Group => {
    const group = new THREE.Group();
    const isOffense = player.team === 'offense';

    // Get color based on player type
    let color = isOffense ? PLAYER_COLORS.offense : PLAYER_COLORS.defense;
    if (player.player_type === 'qb') color = PLAYER_COLORS.qb;
    else if (player.player_type === 'rb' || player.player_type === 'fb') color = PLAYER_COLORS.rb;
    else if (player.player_type === 'ol') color = PLAYER_COLORS.ol;
    else if (player.player_type === 'dl') color = PLAYER_COLORS.dl;

    // Body
    const bodyGeom = new THREE.CapsuleGeometry(0.6, 1.2, 8, 16);
    const bodyMat = new THREE.MeshStandardMaterial({ color, roughness: 0.5, metalness: 0.1 });
    const body = new THREE.Mesh(bodyGeom, bodyMat);
    body.castShadow = true;
    group.add(body);

    // Helmet
    const helmetGeom = new THREE.SphereGeometry(0.5, 16, 16);
    const helmetColor = isOffense ? PLAYER_COLORS.offenseLight : PLAYER_COLORS.defenseLight;
    const helmetMat = new THREE.MeshStandardMaterial({ color: helmetColor, roughness: 0.3, metalness: 0.2 });
    const helmet = new THREE.Mesh(helmetGeom, helmetMat);
    helmet.position.y = 1.3;
    helmet.castShadow = true;
    group.add(helmet);

    // Direction indicator
    const coneGeom = new THREE.ConeGeometry(0.3, 0.8, 8);
    const coneMat = new THREE.MeshStandardMaterial({ color: 0xffffff, opacity: 0.7, transparent: true });
    const cone = new THREE.Mesh(coneGeom, coneMat);
    cone.rotation.x = Math.PI / 2;
    cone.position.set(0, 0.5, 1);
    group.add(cone);

    // Position (field y -> Three.js z)
    group.position.set(player.x, 1.2, player.y);

    return group;
  };

  // Update player positions
  const updatePlayers = useCallback((players: PlayerState[]) => {
    const scene = sceneRef.current;
    if (!scene) return;

    const existingIds = new Set(playerMeshesRef.current.keys());
    const currentIds = new Set(players.map(p => p.id));

    // Remove old players
    existingIds.forEach(id => {
      if (!currentIds.has(id)) {
        const mesh = playerMeshesRef.current.get(id);
        if (mesh) {
          scene.remove(mesh);
          playerMeshesRef.current.delete(id);
        }
      }
    });

    // Update or create players
    players.forEach(player => {
      let mesh = playerMeshesRef.current.get(player.id);
      if (!mesh) {
        mesh = createPlayerMesh(player);
        scene.add(mesh);
        playerMeshesRef.current.set(player.id, mesh);
      }

      // Update position
      mesh.position.x = player.x;
      mesh.position.z = player.y;

      // Update rotation based on facing direction
      if (player.facing_x !== undefined && player.facing_y !== undefined) {
        const angle = Math.atan2(player.facing_x, player.facing_y);
        mesh.rotation.y = angle;
      } else if (player.vx !== undefined && player.vy !== undefined) {
        const speed = Math.sqrt(player.vx * player.vx + player.vy * player.vy);
        if (speed > 0.1) {
          const angle = Math.atan2(player.vx, player.vy);
          mesh.rotation.y = angle;
        }
      }
    });
  }, []);

  // Update ball position
  const updateBall = useCallback((simState: SimState) => {
    const ball = ballMeshRef.current;
    if (!ball || !simState.ball) return;

    ball.visible = true;
    ball.position.x = simState.ball.x;
    ball.position.z = simState.ball.y;
    ball.position.y = simState.ball.height || 1;
  }, []);

  // WebSocket connection
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
        updatePlayers(msg.payload.players);
        updateBall(msg.payload);
      } else if (msg.type === 'tick') {
        setSimState(prev => {
          if (!prev) return msg.payload;
          const newState = {
            ...prev,
            tick: msg.payload.tick,
            time: msg.payload.time,
            phase: msg.payload.phase,
            players: msg.payload.players,
            ball: msg.payload.ball,
            play_outcome: msg.payload.play_outcome,
            is_running: msg.payload.is_running,
            is_paused: msg.payload.is_paused,
            is_complete: msg.payload.is_complete,
          };
          updatePlayers(newState.players);
          updateBall(newState);
          return newState;
        });
      } else if (msg.type === 'complete') {
        setSimState(msg.payload);
      } else if (msg.type === 'error') {
        setError(msg.message);
      }
    };

    ws.onclose = () => setIsConnected(false);
    ws.onerror = () => {
      setError('WebSocket connection failed');
      setIsConnected(false);
    };

    wsRef.current = ws;
  }, [updatePlayers, updateBall]);

  // Create session
  const createSession = useCallback(async () => {
    setError(null);

    const detectedRunPlay = isRunConcept(selectedConcept);
    const finalIsRunPlay = detectedRunPlay;

    try {
      const res = await fetch(`${API_BASE}/matchup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          concept: selectedConcept,
          scheme: selectedScheme,
          tick_rate_ms: 50,
          max_time: 6.0,
          is_run_play: finalIsRunPlay,
        }),
      });

      if (!res.ok) throw new Error('Failed to create session');

      const session = await res.json();
      setSessionId(session.session_id);
      connectWebSocket(session.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [selectedConcept, selectedScheme, connectWebSocket]);

  // Cleanup WebSocket on unmount
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

  const start = () => sendCommand('start');
  const pause = () => sendCommand('pause');
  const resume = () => sendCommand('resume');
  const reset = () => sendCommand('reset');
  const step = () => sendCommand('step');

  // Camera preset change
  const setCamera = (preset: 'broadcast' | 'overhead') => {
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    if (!camera || !controls) return;

    const { position, target } = CAMERA_PRESETS[preset];

    // Animate camera transition
    const startPos = camera.position.clone();
    const startTarget = controls.target.clone();
    const endPos = new THREE.Vector3(...(position as [number, number, number]));
    const endTarget = new THREE.Vector3(...(target as [number, number, number]));
    const duration = 1000;
    const startTime = Date.now();

    const animateCamera = () => {
      const elapsed = Date.now() - startTime;
      const t = Math.min(elapsed / duration, 1);
      const ease = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

      camera.position.lerpVectors(startPos, endPos, ease);
      controls.target.lerpVectors(startTarget, endTarget, ease);

      if (t < 1) requestAnimationFrame(animateCamera);
    };
    animateCamera();

    setCurrentCamera(preset);
  };

  // Keyboard shortcuts
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
        case 's':
          step();
          break;
        case 'r':
          reset();
          break;
        case '1':
          setCamera('broadcast');
          break;
        case '2':
          setCamera('overhead');
          break;
        case 'e':
          setShowEngine(prev => !prev);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isConnected, simState]);

  return (
    <div className="sim3d">
      {/* Canvas container */}
      <div className="sim3d__canvas" ref={containerRef} />

      {/* Header overlay */}
      <div className="sim3d__header">
        <div className="sim3d__camera-buttons">
          {Object.entries(CAMERA_PRESETS).map(([key, preset]) => (
            <button
              key={key}
              className={`sim3d__camera-btn ${currentCamera === key ? 'active' : ''}`}
              onClick={() => setCamera(key as 'broadcast' | 'overhead')}
            >
              {preset.label}
            </button>
          ))}
        </div>
        {sessionId && (
          <button
            className={`sim3d__engine-btn ${showEngine ? 'active' : ''}`}
            onClick={() => setShowEngine(prev => !prev)}
          >
            <Terminal size={14} />
            ENGINE
          </button>
        )}
        <Link to="/sim-analyzer" className="sim3d__back-btn">
          ← 2D View
        </Link>
      </div>

      {/* Setup panel (when no session) */}
      {!sessionId && (
        <div className="sim3d__setup">
          <h1 className="sim3d__title">SIM 3D</h1>
          <p className="sim3d__subtitle">3D Football Simulation Viewer</p>

          <div className="sim3d__presets">
            {PRESET_MATCHUPS.map((preset, i) => (
              <button
                key={i}
                className={`sim3d__preset ${
                  selectedConcept === preset.concept && selectedScheme === preset.scheme
                    ? 'active'
                    : ''
                }`}
                onClick={() => {
                  setSelectedConcept(preset.concept);
                  setSelectedScheme(preset.scheme);
                }}
              >
                {preset.label}
              </button>
            ))}
          </div>

          <div className="sim3d__selectors">
            <div className="sim3d__select-group">
              <label>Offense</label>
              <select
                value={selectedConcept}
                onChange={e => setSelectedConcept(e.target.value)}
              >
                {conceptOptions.map(c => (
                  <option key={c.name} value={c.name}>{c.display_name}</option>
                ))}
              </select>
            </div>
            <div className="sim3d__select-group">
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

          <button className="sim3d__run-btn" onClick={createSession}>
            RUN SIMULATION
          </button>

          {error && <div className="sim3d__error">{error}</div>}
        </div>
      )}

      {/* Controls overlay (when session active) */}
      {sessionId && (
        <div className="sim3d__controls">
          <div className="sim3d__control-buttons">
            {simState?.is_running && !simState?.is_paused ? (
              <button onClick={pause}>Pause</button>
            ) : simState?.is_paused ? (
              <button onClick={resume}>Resume</button>
            ) : (
              <button onClick={start}>Play</button>
            )}
            <button onClick={reset}>Reset</button>
            <button onClick={step}>Step</button>
          </div>
          <div className="sim3d__info">
            <span>Time: {simState?.time?.toFixed(1) || '0.0'}s</span>
            <span>Phase: {simState?.phase || 'pre_snap'}</span>
            {simState?.play_outcome && simState.play_outcome !== 'in_progress' && (
              <span className="sim3d__outcome">{simState.play_outcome.toUpperCase()}</span>
            )}
          </div>
        </div>
      )}

      {/* Keyboard hints */}
      {sessionId && (
        <div className="sim3d__hints">
          Space: Play/Pause | S: Step | R: Reset | 1: Broadcast | 2: Overhead | E: Engine
        </div>
      )}

      {/* ENGINE Panel */}
      {showEngine && simState && (
        <div className="sim3d__engine-panel">
          <div className="engine-section">
            <div className="engine-section__header">SESSION</div>
            <div className="engine-row">
              <span className="engine-row__label">ID</span>
              <span className="engine-row__value">{simState.session_id?.slice(0, 8)}...</span>
            </div>
            <div className="engine-row">
              <span className="engine-row__label">Tick</span>
              <span className="engine-row__value">{simState.tick}</span>
            </div>
            <div className="engine-row">
              <span className="engine-row__label">Time</span>
              <span className="engine-row__value">{simState.time?.toFixed(2)}s</span>
            </div>
            <div className="engine-row">
              <span className="engine-row__label">Phase</span>
              <span className="engine-row__value">{simState.phase}</span>
            </div>
            <div className="engine-row">
              <span className="engine-row__label">Outcome</span>
              <span className={`engine-row__value ${simState.play_outcome !== 'in_progress' ? 'engine-row__value--highlight' : ''}`}>
                {simState.play_outcome}
              </span>
            </div>
          </div>

          <div className="engine-section">
            <div className="engine-section__header">BALL</div>
            <div className="engine-row">
              <span className="engine-row__label">State</span>
              <span className="engine-row__value">{simState.ball?.state}</span>
            </div>
            <div className="engine-row">
              <span className="engine-row__label">Position</span>
              <span className="engine-row__value">
                ({simState.ball?.x?.toFixed(1)}, {simState.ball?.y?.toFixed(1)})
              </span>
            </div>
            <div className="engine-row">
              <span className="engine-row__label">Carrier</span>
              <span className="engine-row__value">
                {simState.ball?.carrier_id
                  ? simState.players.find(p => p.id === simState.ball?.carrier_id)?.name || simState.ball.carrier_id
                  : '-'}
              </span>
            </div>
          </div>

          {simState.qb_state && (
            <div className="engine-section">
              <div className="engine-section__header">QB BRAIN</div>
              <div className="engine-row">
                <span className="engine-row__label">Read</span>
                <span className="engine-row__value">#{simState.qb_state.current_read}</span>
              </div>
              <div className="engine-row">
                <span className="engine-row__label">Pressure</span>
                <span className={`engine-row__value ${
                  simState.qb_state.pressure_level === 'HEAVY' || simState.qb_state.pressure_level === 'CRITICAL'
                    ? 'engine-row__value--danger' : ''
                }`}>
                  {simState.qb_state.pressure_level}
                </span>
              </div>
              <div className="engine-row">
                <span className="engine-row__label">Pocket Time</span>
                <span className="engine-row__value">{simState.qb_state.time_in_pocket?.toFixed(2)}s</span>
              </div>
              {simState.qb_state.coverage_shell && (
                <div className="engine-row">
                  <span className="engine-row__label">Coverage</span>
                  <span className="engine-row__value">{simState.qb_state.coverage_shell}</span>
                </div>
              )}
            </div>
          )}

          <div className="engine-section">
            <div className="engine-section__header">EVENTS ({simState.events?.length || 0})</div>
            <div className="engine-events">
              {(simState.events || []).slice(-12).map((event, i) => (
                <div key={i} className="engine-event">
                  <span className="engine-event__time">{event.time?.toFixed(2)}s</span>
                  <span className="engine-event__type">{event.type}</span>
                  <span className="engine-event__desc">{event.description}</span>
                </div>
              ))}
            </div>
          </div>

          {simState.qb_trace && simState.qb_trace.length > 0 && (
            <div className="engine-section">
              <div className="engine-section__header">QB TRACE</div>
              <div className="engine-trace">
                {simState.qb_trace.slice(-10).map((line, i) => (
                  <div key={i} className="engine-trace__line">{line}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
