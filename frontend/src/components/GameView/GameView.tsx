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
import type { GameMode } from './components/GameStartFlow';
import { SpecialTeamsModal } from './components/SpecialTeamsModal';
import { SpectatorControls } from './components/SpectatorControls';
import { PlayCanvas } from './components/PlayCanvas';
import { PlaybackControls } from './components/PlaybackControls';

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
  GameSituation,
  PlayResult,
  DrivePlay,
  Formation,
  PersonnelGroup,
  PlayOption,
  CoverageScheme,
  BlitzPackage,
} from './types';

// Panel views for left sidebar
type GamePanelView = 'drive' | 'scout' | 'stats' | 'settings' | null;

// Mock ticker events for game
const MOCK_TICKER_EVENTS = [
  { type: 'play', text: 'DAL ball at own 25 after touchback' },
  { type: 'score', text: 'TOUCHDOWN - NYG leads 7-0' },
  { type: 'injury', text: 'DAL WR questionable to return (hamstring)' },
  { type: 'play', text: 'NYG: 8 plays, 75 yards, 4:32 TOP' },
  { type: 'league', text: 'PHI 14, WAS 10 - 3rd Quarter' },
];

// Mock initial situation for development
const MOCK_SITUATION: GameSituation = {
  quarter: 2,
  timeRemaining: '5:42',
  down: 2,
  distance: 7,
  los: 65,
  yardLineDisplay: 'OPP 35',
  homeScore: 21,
  awayScore: 14,
  possessionHome: true,
  isRedZone: false,
  isGoalToGo: false,
  userOnOffense: true,
  homeTimeouts: 3,
  awayTimeouts: 2,
};

// Mock available plays
const MOCK_PLAYS: PlayOption[] = [
  { code: 'INSIDE_ZONE', name: 'Inside Zone', category: 'run', isRecommended: true },
  { code: 'POWER', name: 'Power', category: 'run' },
  { code: 'COUNTER', name: 'Counter', category: 'run' },
  { code: 'DRAW', name: 'Draw', category: 'run' },
  { code: 'STRETCH', name: 'Stretch', category: 'run' },
  { code: 'SLANT', name: 'Slant', category: 'quick' },
  { code: 'HITCH', name: 'Hitch', category: 'quick' },
  { code: 'OUT', name: 'Out', category: 'quick' },
  { code: 'CURL', name: 'Curl', category: 'intermediate' },
  { code: 'DIG', name: 'Dig', category: 'intermediate' },
  { code: 'POST', name: 'Post', category: 'deep' },
  { code: 'GO_ROUTE', name: 'Go Route', category: 'deep' },
  { code: 'FADE', name: 'Fade', category: 'deep' },
  { code: 'SCREEN', name: 'Screen', category: 'screen' },
  { code: 'PA_BOOT', name: 'PA Boot', category: 'play_action' },
];

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
    startGame: coachStartGame,
    executePlay,
    executeDefense,
  } = useCoachAPI();

  // Spectator mode WebSocket hook
  const {
    isConnected,
    isLoading: spectatorLoading,
    error: spectatorError,
    gameId: spectatorGameId,
    situation: spectatorSituation,
    homeTeam: wsHomeTeam,
    awayTeam: wsAwayTeam,
    lastResult: wsLastResult,
    currentDrive: wsDrive,
    playLog,
    isPaused,
    pacing,
    gameOver,
    announcement,
    // Play visualization
    playFrames,
    currentPlayTick,
    isPlayAnimating,
    playbackSpeed,
    setCurrentPlayTick,
    setIsPlayAnimating,
    setPlaybackSpeed,
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

  // Use API/WS situation if available, otherwise mock
  const situation = isSpectatorMode
    ? (spectatorSituation || MOCK_SITUATION)
    : (coachSituation || MOCK_SITUATION);
  const plays = availablePlays.length > 0 ? availablePlays : MOCK_PLAYS;

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

  // Team info
  const [homeTeam, setHomeTeam] = useState('NYG');
  const [awayTeam, setAwayTeam] = useState('DAL');
  const [userIsHome, setUserIsHome] = useState(true);

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
  const handleStartGame = useCallback(async (home: string, away: string, isHome: boolean, mode: GameMode) => {
    setHomeTeam(home);
    setAwayTeam(away);
    setUserIsHome(isHome);
    setGameMode(mode);

    if (mode === 'spectator') {
      try {
        await spectatorStartGame(home, away);
        setGameStarted(true);
      } catch (err) {
        console.error('Failed to start spectator game:', err);
        // Stay on start screen if failed
      }
    } else {
      try {
        await coachStartGame(home, away);
      } catch {
        // Mock mode
      }
      setGameStarted(true);
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

  return (
    <div className="game-view" data-phase={phase}>
      {/* Middle: Nav + Panel + Main (flex row) */}
      <div className="game-view__middle">
        {/* Left: Icon Navigation Sidebar (ManagementV2 style) */}
        <aside className={`game-view__nav ${sidebarExpanded ? 'expanded' : ''}`}>
        <div className="game-view__nav-top">
          {/* App menu (hamburger) */}
          <div className="game-view__nav-app" ref={appNavRef}>
            <button
              className={`game-view__nav-btn ${appNavOpen ? 'active' : ''}`}
              onClick={() => setAppNavOpen(!appNavOpen)}
              title="Menu"
            >
              <Menu size={18} />
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
          >
            <Calendar size={18} />
            {sidebarExpanded && <span className="game-view__nav-label">Drive</span>}
          </button>
          <button
            className={`game-view__nav-btn ${activePanel === 'scout' ? 'active' : ''}`}
            onClick={() => togglePanel('scout')}
            title="Scouting Intel"
          >
            <Target size={18} />
            {sidebarExpanded && <span className="game-view__nav-label">Scout</span>}
          </button>
          <button
            className={`game-view__nav-btn ${activePanel === 'stats' ? 'active' : ''}`}
            onClick={() => togglePanel('stats')}
            title="Game Stats"
          >
            <BarChart3 size={18} />
            {sidebarExpanded && <span className="game-view__nav-label">Stats</span>}
          </button>
        </div>

        <div className="game-view__nav-bottom">
          <button
            className={`game-view__nav-btn ${activePanel === 'settings' ? 'active' : ''}`}
            onClick={() => togglePanel('settings')}
            title="Settings"
          >
            <Settings size={18} />
            {sidebarExpanded && <span className="game-view__nav-label">Settings</span>}
          </button>
          <div className="game-view__nav-divider" />
          <button
            className="game-view__nav-btn game-view__nav-toggle"
            onClick={() => setSidebarExpanded(!sidebarExpanded)}
            title={sidebarExpanded ? 'Collapse' : 'Expand'}
          >
            {sidebarExpanded ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
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
      <div className="game-view__main">
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
            >
              {tickerPaused ? <Play size={12} /> : <Pause size={12} />}
            </button>
          </div>

          {/* Right: View Controls */}
          <div className="game-view__controls">
            <button
              className={`game-view__view-btn ${viewMode === 'simulcast' ? 'active' : ''}`}
              onClick={() => setViewMode('simulcast')}
              title="Simulcast View (V)"
            >
              <Tv size={14} />
            </button>
            <button
              className={`game-view__view-btn ${viewMode === 'full_field' ? 'active' : ''}`}
              onClick={() => setViewMode('full_field')}
              title="Full Field View (V)"
            >
              <CircleDot size={14} />
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
                driveStartLos={currentDrive.length > 0 ? currentDrive[0].los : situation?.los || 25}
                homeTeamColor={TEAM_COLORS[homeTeam]?.primary}
                awayTeamColor={TEAM_COLORS[awayTeam]?.primary}
                homeTeamLogo={TEAM_COLORS[homeTeam]?.logo}
                homeTeam={homeTeam}
                awayTeam={awayTeam}
              />
            ) : (
              /* Live Play View - PixiJS canvas with playback controls */
              <div className="game-view__live-play">
                <PlayCanvas
                  frames={playFrames}
                  currentTick={currentPlayTick}
                  isPlaying={isPlayAnimating}
                  playbackSpeed={playbackSpeed}
                  onTickChange={setCurrentPlayTick}
                  onComplete={() => setIsPlayAnimating(false)}
                />
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
      </div>
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
