/**
 * GameView - Coach's Game Day Experience
 *
 * An immersive "coach's booth" interface for calling plays during games.
 * Uses the SAME design language as ManagementV2 (ops center aesthetic).
 *
 * Layout (mirrors ManagementV2):
 * - Left: Icon-based nav sidebar (collapsible)
 * - Top: Context bar (game status | ticker | controls)
 * - Main: Workpane (field visualization + play calling)
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Menu,
  Calendar,
  Users,
  Target,
  BarChart3,
  Settings,
  Zap,
  ChevronLeft,
  ChevronRight,
  Tv,
  CircleDot,
  Play,
  Pause,
  Shield,
  Crosshair,
  Eye,
} from 'lucide-react';
import './GameView.css';

// Components
import { SimulcastView } from './views/SimulcastView';
import { PlayCaller } from './components/offense/PlayCaller';
import { DefenseCaller } from './components/defense/DefenseCaller';
import { GameStartFlow, TEAM_COLORS } from './components/GameStartFlow';
import type { GameMode, GameStartParams } from './components/GameStartFlow';
import { SpecialTeamsModal } from './components/SpecialTeamsModal';
import { SpectatorControls } from './components/SpectatorControls';
import { PlaybackControls } from './components/PlaybackControls';
import { GameViewErrorBoundary } from './components/GameViewErrorBoundary';
import { BroadcastCanvas, Scoreboard } from '../BroadcastCanvas';

// Panels
import { DriveSummary } from './panels/DriveSummary';
import { ScoutingIntel } from './panels/ScoutingIntel';
import { SituationStats } from './panels/SituationStats';

// Hooks
import { useCoachAPI } from './hooks/useCoachAPI';
import { useGameWebSocket } from './hooks/useGameWebSocket';

// Types
import type {
  GamePhase,
  ViewMode,
  PlayResult,
  DrivePlay,
  Formation,
  PersonnelGroup,
  CoverageScheme,
  BlitzPackage,
} from './types';

// Constants - mock data moved here for explicit dev-only mode
import {
  USE_MOCK_DATA,
  MOCK_SITUATION,
  MOCK_PLAYS,
  MOCK_TICKER_EVENTS,
} from './constants';

// Panel views for left sidebar
type GamePanelView = 'drive' | 'scout' | 'stats' | 'settings' | null;

export const GameView: React.FC = () => {
  // Game mode
  const [gameMode, setGameMode] = useState<GameMode>('coach');

  // Coach mode API hook
  const {
    gameId: coachGameId,
    situation: coachSituation,
    availablePlays,
    loading: coachLoading,
    error: coachError,
    // Coach mode play visualization
    playFrames: coachPlayFrames,
    currentPlayTick: coachCurrentPlayTick,
    isPlayAnimating: coachIsPlayAnimating,
    playbackSpeed: coachPlaybackSpeed,
    setCurrentPlayTick: setCoachCurrentPlayTick,
    setIsPlayAnimating: setCoachIsPlayAnimating,
    setPlaybackSpeed: setCoachPlaybackSpeed,
    startGame: coachStartGame,
    executePlay,
    executeDefense,
  } = useCoachAPI();

  // Spectator mode WebSocket hook
  const {
    isLoading: spectatorLoading,
    error: spectatorError,
    gameId: spectatorGameId,
    situation: spectatorSituation,
    lastResult: wsLastResult,
    currentDrive: wsDrive,
    driveStartLos: wsDriveStartLos,
    isPaused,
    pacing,
    gameOver,
    announcement,
    // Spectator mode play visualization
    playFrames: spectatorPlayFrames,
    currentPlayTick: spectatorCurrentPlayTick,
    isPlayAnimating: spectatorIsPlayAnimating,
    playbackSpeed: spectatorPlaybackSpeed,
    setCurrentPlayTick: setSpectatorCurrentPlayTick,
    setIsPlayAnimating: setSpectatorIsPlayAnimating,
    setPlaybackSpeed: setSpectatorPlaybackSpeed,
    startGame: spectatorStartGame,
    setPacing,
    togglePause,
    step,
    endGame: spectatorEndGame,
  } = useGameWebSocket();

  // Derived values based on mode
  const isSpectatorMode = gameMode === 'spectator';
  const gameId = isSpectatorMode ? spectatorGameId : coachGameId;
  const loading = isSpectatorMode ? spectatorLoading : coachLoading;
  const error = isSpectatorMode ? spectatorError : coachError;

  // Derived play visualization state (choose source based on mode)
  const playFrames = isSpectatorMode ? spectatorPlayFrames : coachPlayFrames;
  const currentPlayTick = isSpectatorMode ? spectatorCurrentPlayTick : coachCurrentPlayTick;
  const isPlayAnimating = isSpectatorMode ? spectatorIsPlayAnimating : coachIsPlayAnimating;
  const playbackSpeed = isSpectatorMode ? spectatorPlaybackSpeed : coachPlaybackSpeed;
  const setCurrentPlayTick = isSpectatorMode ? setSpectatorCurrentPlayTick : setCoachCurrentPlayTick;
  const setIsPlayAnimating = isSpectatorMode ? setSpectatorIsPlayAnimating : setCoachIsPlayAnimating;
  const setPlaybackSpeed = isSpectatorMode ? setSpectatorPlaybackSpeed : setCoachPlaybackSpeed;

  // Get real situation from API/WS, use mock only if explicitly enabled
  const realSituation = isSpectatorMode ? spectatorSituation : coachSituation;
  const situation = realSituation ?? (USE_MOCK_DATA ? MOCK_SITUATION : null);

  // Get plays from API, use mock only if explicitly enabled
  const plays = availablePlays.length > 0
    ? availablePlays
    : (USE_MOCK_DATA ? MOCK_PLAYS : []);

  // Game state
  const [phase, setPhase] = useState<GamePhase>('pre_snap');
  const [coachLastResult, setCoachLastResult] = useState<PlayResult | null>(null);

  // Derived: use WS result in spectator mode, coach result otherwise
  const lastResult = isSpectatorMode ? wsLastResult : coachLastResult;
  const setLastResult = setCoachLastResult; // Only used in coach mode

  // User selections (offense)
  const [selectedFormation, setSelectedFormation] = useState<Formation | null>('shotgun');
  const [selectedPersonnel, setSelectedPersonnel] = useState<PersonnelGroup>('11');
  const [selectedPlayCode, setSelectedPlayCode] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('run');

  // User selections (defense)
  const [selectedCoverage, setSelectedCoverage] = useState<CoverageScheme | null>('cover_3');
  const [selectedBlitz, setSelectedBlitz] = useState<BlitzPackage>('none');

  // History
  const [coachDrive, setCoachDrive] = useState<DrivePlay[]>([]);

  // Derived: use WS drive in spectator mode, coach drive otherwise
  const currentDrive = isSpectatorMode ? wsDrive : coachDrive;
  const setCurrentDrive = setCoachDrive; // Only used in coach mode

  // UI state
  const [viewMode, setViewMode] = useState<ViewMode>('simulcast');
  const [sidebarExpanded, setSidebarExpanded] = useState(false);
  const [activePanel, setActivePanel] = useState<GamePanelView>('drive');
  const [gameStarted, setGameStarted] = useState(false);
  const [showSpecialTeamsModal, setShowSpecialTeamsModal] = useState(false);
  const [tickerPaused, setTickerPaused] = useState(false);
  const [appNavOpen, setAppNavOpen] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);

  // Team info
  const [homeTeam, setHomeTeam] = useState('NYG');
  const [awayTeam, setAwayTeam] = useState('DAL');
  const [_userIsHome, setUserIsHome] = useState(true);

  // Refs
  const appNavRef = useRef<HTMLDivElement>(null);

  // Load sidebar state from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('gameview-sidebar-expanded');
    if (saved) setSidebarExpanded(saved === 'true');
  }, []);

  // Save sidebar state
  useEffect(() => {
    localStorage.setItem('gameview-sidebar-expanded', String(sidebarExpanded));
  }, [sidebarExpanded]);

  // Close app nav on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (appNavRef.current && !appNavRef.current.contains(e.target as Node)) {
        setAppNavOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle game start
  const handleStartGame = useCallback(async (params: GameStartParams) => {
    const { homeTeamAbbr, awayTeamAbbr, homeTeamId, awayTeamId, userIsHome: isHome, mode } = params;

    setHomeTeam(homeTeamAbbr);
    setAwayTeam(awayTeamAbbr);
    setUserIsHome(isHome);
    setGameMode(mode);

    if (mode === 'spectator') {
      try {
        await spectatorStartGame(homeTeamAbbr, awayTeamAbbr);
        setGameStarted(true);
      } catch (err) {
        console.error('Failed to start spectator game:', err);
        // Stay on start screen if failed
      }
    } else {
      try {
        await coachStartGame({
          homeTeamId,
          awayTeamId,
          homeTeamAbbr,
          awayTeamAbbr,
          userControlsHome: isHome,
        });
        setGameStarted(true);
      } catch (err) {
        console.error('Failed to start coach game:', err);
        // Stay on start screen if API fails
      }
    }
  }, [spectatorStartGame, coachStartGame]);

  // Toggle view mode
  const toggleViewMode = useCallback(() => {
    setViewMode(prev => prev === 'simulcast' ? 'full_field' : 'simulcast');
  }, []);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      switch (e.key.toLowerCase()) {
        case 'v':
          toggleViewMode();
          break;
        case ' ':
          e.preventDefault();
          if (phase === 'pre_snap' && selectedPlayCode && situation?.userOnOffense) {
            handleSnapOffense();
          } else if (phase === 'pre_snap' && selectedCoverage && !situation?.userOnOffense) {
            handleSetDefense();
          }
          break;
        case 'escape':
          if (phase === 'result') handleDismissResult();
          if (showSpecialTeamsModal) setShowSpecialTeamsModal(false);
          break;
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleViewMode, phase, selectedPlayCode, selectedCoverage, situation?.userOnOffense, showSpecialTeamsModal]);

  // Check for 4th down (only in coach mode)
  useEffect(() => {
    if (!isSpectatorMode && situation?.down === 4 && phase === 'pre_snap' && situation?.userOnOffense) {
      setShowSpecialTeamsModal(true);
    }
  }, [situation?.down, phase, situation?.userOnOffense, isSpectatorMode]);

  // Handle snap (execute offensive play)
  const handleSnapOffense = useCallback(async () => {
    if (!selectedPlayCode) return;
    setPhase('executing');
    try {
      if (gameId) {
        const result = await executePlay(selectedPlayCode, selectedFormation === 'shotgun');
        setLastResult(result);
      } else {
        const mockResult: PlayResult = {
          outcome: 'complete',
          yardsGained: Math.floor(Math.random() * 15) - 2,
          description: 'Pass complete to the right side',
          newDown: 1,
          newDistance: 10,
          newLos: 72,
          firstDown: true,
          touchdown: false,
          turnover: false,
          isDriveOver: false,
        };
        setLastResult(mockResult);
        setCurrentDrive(prev => [...prev, {
          playNumber: prev.length + 1,
          down: situation?.down || 1,
          distance: situation?.distance || 10,
          los: situation?.los || 50,
          playType: selectedCategory === 'run' ? 'run' : 'pass',
          playName: plays.find(p => p.code === selectedPlayCode)?.name || selectedPlayCode || '',
          yardsGained: mockResult.yardsGained,
          outcome: mockResult.outcome,
          isFirstDown: mockResult.firstDown,
        }]);
      }
      setPhase('result');
    } catch (err) {
      console.error('Failed to execute play:', err);
      setPhase('pre_snap');
    }
  }, [selectedPlayCode, selectedFormation, selectedCategory, gameId, executePlay, situation, plays]);

  // Handle set defense
  const handleSetDefense = useCallback(async () => {
    if (!selectedCoverage) return;
    setPhase('executing');
    try {
      if (gameId) {
        const result = await executeDefense(selectedCoverage, selectedBlitz);
        setLastResult(result);
      } else {
        const mockResult: PlayResult = {
          outcome: 'incomplete',
          yardsGained: 0,
          description: 'Pass defended by the corner',
          newDown: 2,
          newDistance: 10,
          newLos: 30,
          firstDown: false,
          touchdown: false,
          turnover: false,
          isDriveOver: false,
        };
        setLastResult(mockResult);
      }
      setPhase('result');
    } catch (err) {
      console.error('Failed to execute defense:', err);
      setPhase('pre_snap');
    }
  }, [selectedCoverage, selectedBlitz, gameId, executeDefense]);

  // Special teams handlers
  const handleGoForIt = useCallback(() => {
    setShowSpecialTeamsModal(false);
  }, []);

  const handlePunt = useCallback(() => {
    setShowSpecialTeamsModal(false);
    setPhase('result');
    setLastResult({
      outcome: 'punt',
      yardsGained: 0,
      description: 'Punt downed at opponent 20',
      newDown: 1,
      newDistance: 10,
      newLos: 20,
      firstDown: false,
      touchdown: false,
      turnover: false,
      isDriveOver: true,
      driveEndReason: 'punt',
    });
  }, []);

  const handleFieldGoal = useCallback(() => {
    setShowSpecialTeamsModal(false);
    const fgDistance = 100 - (situation?.los || 65) + 17;
    const made = Math.random() > (fgDistance / 100);
    setPhase('result');
    setLastResult({
      outcome: made ? 'field_goal_good' : 'field_goal_missed',
      yardsGained: 0,
      description: made ? `${fgDistance} yard field goal is GOOD!` : `${fgDistance} yard field goal MISSED`,
      newDown: 1,
      newDistance: 10,
      newLos: made ? 35 : situation?.los || 65,
      firstDown: false,
      touchdown: false,
      turnover: false,
      isDriveOver: true,
      driveEndReason: made ? 'field_goal' : 'missed_fg',
    });
  }, [situation?.los]);

  const handleDismissResult = useCallback(() => {
    setPhase('pre_snap');
    setSelectedPlayCode(null);
  }, []);

  // Handle end spectator game
  const handleEndSpectatorGame = useCallback(() => {
    spectatorEndGame();
    setGameStarted(false);
    setGameMode('coach');
  }, [spectatorEndGame]);

  // Panel toggle
  const togglePanel = (panel: GamePanelView) => {
    setActivePanel(prev => prev === panel ? null : panel);
  };

  // Computed
  const userOnOffense = situation?.userOnOffense ?? true;
  const filteredPlays = plays.filter(p => p.category === selectedCategory);

  // Show start flow if game hasn't started
  if (!gameStarted) {
    return (
      <div className="game-view" data-phase="setup">
        <GameStartFlow onStartGame={handleStartGame} loading={loading} />
      </div>
    );
  }

  // Show loading state while waiting for game situation
  if (!situation) {
    return (
      <div className="game-view" data-phase="loading">
        <div className="game-view__loading">
          <div className="game-view__loading-spinner" />
          <span>Loading game data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="game-view" data-phase={phase}>
      {/* Skip navigation link for keyboard users */}
      <a href="#game-main-content" className="game-view__skip-link">
        Skip to main content
      </a>

      {/* Middle: Nav + Panel + Main (flex row) */}
      <div className="game-view__middle">
        {/* Left: Icon Navigation Sidebar (ManagementV2 style) */}
        <aside
          className={`game-view__nav ${sidebarExpanded ? 'expanded' : ''}`}
          role="navigation"
          aria-label="Game navigation"
        >
        <div className="game-view__nav-top">
          {/* App menu (hamburger) */}
          <div className="game-view__nav-app" ref={appNavRef}>
            <button
              className={`game-view__nav-btn ${appNavOpen ? 'active' : ''}`}
              onClick={() => setAppNavOpen(!appNavOpen)}
              title="Menu"
              aria-label="Open navigation menu"
              aria-expanded={appNavOpen}
              aria-haspopup="menu"
            >
              <Menu size={18} aria-hidden="true" />
              {sidebarExpanded && <span className="game-view__nav-label">Menu</span>}
            </button>
            {appNavOpen && (
              <div className="game-view__app-dropdown">
                <a href="/management" className="game-view__app-link">
                  <Users size={14} />
                  <span>Management</span>
                </a>
                <a href="/v2-sim" className="game-view__app-link">
                  <Zap size={14} />
                  <span>Simulation</span>
                </a>
                <a href="/coach" className="game-view__app-link active">
                  <Target size={14} />
                  <span>Coach Mode</span>
                </a>
              </div>
            )}
          </div>

          <div className="game-view__nav-divider" />

          {/* Intel panels */}
          <button
            className={`game-view__nav-btn ${activePanel === 'drive' ? 'active' : ''}`}
            onClick={() => togglePanel('drive')}
            title="Current Drive"
            aria-label="Toggle drive summary panel"
            aria-pressed={activePanel === 'drive'}
          >
            <Calendar size={18} aria-hidden="true" />
            {sidebarExpanded && <span className="game-view__nav-label">Drive</span>}
          </button>
          <button
            className={`game-view__nav-btn ${activePanel === 'scout' ? 'active' : ''}`}
            onClick={() => togglePanel('scout')}
            title="Scouting Intel"
            aria-label="Toggle scouting intel panel"
            aria-pressed={activePanel === 'scout'}
          >
            <Target size={18} aria-hidden="true" />
            {sidebarExpanded && <span className="game-view__nav-label">Scout</span>}
          </button>
          <button
            className={`game-view__nav-btn ${activePanel === 'stats' ? 'active' : ''}`}
            onClick={() => togglePanel('stats')}
            title="Game Stats"
            aria-label="Toggle game stats panel"
            aria-pressed={activePanel === 'stats'}
          >
            <BarChart3 size={18} aria-hidden="true" />
            {sidebarExpanded && <span className="game-view__nav-label">Stats</span>}
          </button>
        </div>

        <div className="game-view__nav-bottom">
          <button
            className={`game-view__nav-btn ${activePanel === 'settings' ? 'active' : ''}`}
            onClick={() => togglePanel('settings')}
            title="Settings"
            aria-label="Toggle settings panel"
            aria-pressed={activePanel === 'settings'}
          >
            <Settings size={18} aria-hidden="true" />
            {sidebarExpanded && <span className="game-view__nav-label">Settings</span>}
          </button>
          <div className="game-view__nav-divider" role="separator" />
          <button
            className="game-view__nav-btn game-view__nav-toggle"
            onClick={() => setSidebarExpanded(!sidebarExpanded)}
            title={sidebarExpanded ? 'Collapse sidebar' : 'Expand sidebar'}
            aria-label={sidebarExpanded ? 'Collapse sidebar' : 'Expand sidebar'}
            aria-expanded={sidebarExpanded}
          >
            {sidebarExpanded ? <ChevronLeft size={18} aria-hidden="true" /> : <ChevronRight size={18} aria-hidden="true" />}
          </button>
        </div>
      </aside>

      {/* Left Panel (when active) */}
      {activePanel && (
        <div className="game-view__left-panel">
          <div className="game-view__panel-header">
            <h3>
              {activePanel === 'drive' && 'Current Drive'}
              {activePanel === 'scout' && 'Scouting Intel'}
              {activePanel === 'stats' && 'Game Stats'}
              {activePanel === 'settings' && 'Settings'}
            </h3>
            <button className="game-view__panel-close" onClick={() => setActivePanel(null)}>
              &times;
            </button>
          </div>
          <div className="game-view__panel-body">
            {activePanel === 'drive' && <DriveSummary plays={currentDrive} />}
            {activePanel === 'scout' && <ScoutingIntel />}
            {activePanel === 'stats' && <SituationStats />}
            {activePanel === 'settings' && (
              <div className="game-view__settings">
                <label className="game-view__setting">
                  <span>View Mode</span>
                  <select value={viewMode} onChange={e => setViewMode(e.target.value as ViewMode)}>
                    <option value="simulcast">Simulcast</option>
                    <option value="full_field">Full Field</option>
                  </select>
                </label>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Area */}
      <main id="game-main-content" className="game-view__main" role="main" aria-label="Game field and controls">
        {/* Top: Context Bar (game status | ticker | controls) */}
        <header className="game-view__context">
          {/* Left: Game Status */}
          <div className="game-view__status">
            <span className="game-view__status-quarter">Q{situation.quarter}</span>
            <span className="game-view__status-sep">&middot;</span>
            <span className="game-view__status-time">{situation.timeRemaining}</span>
            <span className="game-view__status-sep">&middot;</span>
            <span className="game-view__status-score">
              <span className={`game-view__status-team ${situation.possessionHome ? 'has-ball' : ''}`}>
                {situation.possessionHome && <span className="game-view__status-ball">●</span>}
                {homeTeam} <strong>{situation.homeScore}</strong>
              </span>
              <span className="game-view__status-vs">-</span>
              <span className={`game-view__status-team ${!situation.possessionHome ? 'has-ball' : ''}`}>
                <strong>{situation.awayScore}</strong> {awayTeam}
                {!situation.possessionHome && <span className="game-view__status-ball">●</span>}
              </span>
            </span>
            <span className="game-view__status-sep">&middot;</span>
            <span className={`game-view__status-down ${situation.down === 4 ? 'fourth' : ''}`}>
              {situation.down}&amp;{situation.distance}
            </span>
            <span className="game-view__status-los">{situation.yardLineDisplay}</span>
          </div>

          {/* Center: Event Ticker */}
          <div className="game-view__ticker">
            <div className={`game-view__ticker-scroll ${tickerPaused ? 'paused' : ''}`}>
              {MOCK_TICKER_EVENTS.map((event, i) => (
                <React.Fragment key={i}>
                  <span className={`game-view__ticker-item game-view__ticker-item--${event.type}`}>
                    {event.type === 'score' && <span className="game-view__ticker-tag">TD</span>}
                    {event.type === 'injury' && <span className="game-view__ticker-tag injury">INJ</span>}
                    {event.text}
                  </span>
                  <span className="game-view__ticker-sep">|</span>
                </React.Fragment>
              ))}
            </div>
            <button
              className={`game-view__ticker-pause ${tickerPaused ? 'paused' : ''}`}
              onClick={() => setTickerPaused(!tickerPaused)}
              title={tickerPaused ? 'Resume ticker' : 'Pause ticker'}
              aria-label={tickerPaused ? 'Resume news ticker' : 'Pause news ticker'}
              aria-pressed={tickerPaused}
            >
              {tickerPaused ? <Play size={12} aria-hidden="true" /> : <Pause size={12} aria-hidden="true" />}
            </button>
          </div>

          {/* Right: View Controls */}
          <div className="game-view__controls" role="group" aria-label="View controls">
            <button
              className={`game-view__view-btn ${viewMode === 'simulcast' ? 'active' : ''}`}
              onClick={() => setViewMode('simulcast')}
              title="Simulcast View (V)"
              aria-label="Switch to simulcast view. Keyboard shortcut: V"
              aria-pressed={viewMode === 'simulcast'}
            >
              <Tv size={14} aria-hidden="true" />
            </button>
            <button
              className={`game-view__view-btn ${viewMode === 'full_field' ? 'active' : ''}`}
              onClick={() => setViewMode('full_field')}
              title="Full Field View (V)"
              aria-label="Switch to full field view. Keyboard shortcut: V"
              aria-pressed={viewMode === 'full_field'}
            >
              <CircleDot size={14} aria-hidden="true" />
            </button>
            <span className="game-view__controls-sep" />
            {isSpectatorMode ? (
              <span className="game-view__possession spectator">
                <Eye size={14} />
                {situation?.possessionHome ? homeTeam : awayTeam} BALL
              </span>
            ) : (
              <span className={`game-view__possession ${userOnOffense ? 'offense' : 'defense'}`}>
                {userOnOffense ? <Crosshair size={14} /> : <Shield size={14} />}
                {userOnOffense ? 'OFFENSE' : 'DEFENSE'}
              </span>
            )}
          </div>
        </header>

        {/* Workpane: Field + Play Calling */}
        <div className="game-view__workpane">
          {/* Field Visualization */}
          <div className="game-view__field">
            {viewMode === 'simulcast' ? (
              <GameViewErrorBoundary section="Simulcast View" minimal>
                <SimulcastView
                  situation={situation}
                  formation={selectedFormation}
                  personnel={selectedPersonnel}
                  lastResult={lastResult}
                  showResult={phase === 'result'}
                  onDismissResult={handleDismissResult}
                  userOnOffense={userOnOffense}
                  possessionHome={situation.possessionHome}
                  currentDrive={currentDrive}
                  driveStartLos={isSpectatorMode ? wsDriveStartLos : (currentDrive.length > 0 ? currentDrive[0].los : situation?.los || 25)}
                  homeTeamColor={TEAM_COLORS[homeTeam]?.primary}
                  awayTeamColor={TEAM_COLORS[awayTeam]?.primary}
                  homeTeamLogo={TEAM_COLORS[homeTeam]?.logo}
                  homeTeam={homeTeam}
                  awayTeam={awayTeam}
                />
              </GameViewErrorBoundary>
            ) : (
              /* Live Play View - AWS Next Gen Stats style broadcast canvas */
              <div className="game-view__live-play">
                {/* Scoreboard bar */}
                {situation && (
                  <Scoreboard
                    homeTeam={{
                      abbr: homeTeam,
                      primaryColor: TEAM_COLORS[homeTeam]?.primary || '#1565c0',
                    }}
                    awayTeam={{
                      abbr: awayTeam,
                      primaryColor: TEAM_COLORS[awayTeam]?.primary || '#b71c1c',
                    }}
                    homeScore={situation.homeScore}
                    awayScore={situation.awayScore}
                    quarter={situation.quarter}
                    timeRemaining={situation.timeRemaining}
                    down={situation.down}
                    distance={situation.distance}
                    possessionHome={situation.possessionHome}
                  />
                )}

                {/* Zoom control */}
                <div className="game-view__zoom-control">
                  <label htmlFor="zoom-slider" className="game-view__zoom-label">Zoom</label>
                  <input
                    id="zoom-slider"
                    type="range"
                    min="0.5"
                    max="3"
                    step="0.1"
                    value={zoomLevel}
                    onChange={(e) => setZoomLevel(parseFloat(e.target.value))}
                    className="game-view__zoom-slider"
                  />
                  <span className="game-view__zoom-value">{zoomLevel.toFixed(1)}x</span>
                </div>

                {/* BroadcastCanvas - AWS Next Gen Stats style - fills container */}
                <GameViewErrorBoundary section="Broadcast Canvas" minimal>
                  <BroadcastCanvas
                    frames={playFrames}
                    currentTick={currentPlayTick}
                    isPlaying={isPlayAnimating}
                    viewMode="game"
                    homeTeam={{
                      abbr: homeTeam,
                      primaryColor: TEAM_COLORS[homeTeam]?.primary || '#1565c0',
                      logo: TEAM_COLORS[homeTeam]?.logo,
                    }}
                    awayTeam={{
                      abbr: awayTeam,
                      primaryColor: TEAM_COLORS[awayTeam]?.primary || '#b71c1c',
                      logo: TEAM_COLORS[awayTeam]?.logo,
                    }}
                    userControlsHome={_userIsHome}
                    possessionHome={situation?.possessionHome}
                    fieldPosition={situation ? {
                      yardLine: situation.los,
                      yardsToGo: situation.distance,
                      down: situation.down,
                      ownTerritory: situation.los <= 50,
                    } : undefined}
                    showOffenseRoutes={userOnOffense || isSpectatorMode}
                    showDefenseCoverage={!userOnOffense || isSpectatorMode}
                    onTickChange={setCurrentPlayTick}
                    onComplete={() => setIsPlayAnimating(false)}
                    zoomLevel={zoomLevel}
                  />
                </GameViewErrorBoundary>

                {/* Playback controls */}
                <PlaybackControls
                  currentTick={currentPlayTick}
                  totalTicks={playFrames.length}
                  isPlaying={isPlayAnimating}
                  speed={playbackSpeed}
                  onPlay={() => setIsPlayAnimating(true)}
                  onPause={() => setIsPlayAnimating(false)}
                  onSeek={setCurrentPlayTick}
                  onSpeedChange={setPlaybackSpeed}
                />
              </div>
            )}

            {/* Announcement overlay */}
            {announcement && (
              <div className={`game-view__announcement game-view__announcement--${announcement.type}`}>
                <span className="game-view__announcement-message">{announcement.message}</span>
                {announcement.subtext && (
                  <span className="game-view__announcement-subtext">{announcement.subtext}</span>
                )}
              </div>
            )}
          </div>

          {/* Play Calling Interface (or Spectator Controls) */}
          <div className="game-view__play-caller">
            {isSpectatorMode ? (
              <SpectatorControls
                isPaused={isPaused}
                pacing={pacing}
                gameOver={gameOver}
                onTogglePause={togglePause}
                onSetPacing={setPacing}
                onStep={step}
                onEndGame={handleEndSpectatorGame}
              />
            ) : userOnOffense ? (
              <PlayCaller
                selectedFormation={selectedFormation}
                selectedPersonnel={selectedPersonnel}
                selectedPlay={selectedPlayCode}
                selectedCategory={selectedCategory}
                availablePlays={filteredPlays}
                situation={situation}
                onFormationChange={setSelectedFormation}
                onPersonnelChange={setSelectedPersonnel}
                onPlaySelect={setSelectedPlayCode}
                onCategoryChange={setSelectedCategory}
                onSnap={handleSnapOffense}
                disabled={phase !== 'pre_snap' || loading}
              />
            ) : (
              <DefenseCaller
                selectedCoverage={selectedCoverage}
                selectedBlitz={selectedBlitz}
                situation={situation}
                onCoverageChange={setSelectedCoverage}
                onBlitzChange={setSelectedBlitz}
                onSetDefense={handleSetDefense}
                disabled={phase !== 'pre_snap' || loading}
              />
            )}
          </div>
        </div>
      </main>
      </div>{/* end middle */}

      {/* Loading overlay */}
      {loading && (
        <div className="game-view__loading">
          <div className="game-view__loading-spinner" />
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="game-view__error">
          <span>{error}</span>
        </div>
      )}

      {/* Special Teams Modal */}
      {situation && (
        <SpecialTeamsModal
          situation={situation}
          isOpen={showSpecialTeamsModal}
          onGoForIt={handleGoForIt}
          onPunt={handlePunt}
          onFieldGoal={handleFieldGoal}
          onClose={() => setShowSpecialTeamsModal(false)}
        />
      )}
    </div>
  );
};

export default GameView;
