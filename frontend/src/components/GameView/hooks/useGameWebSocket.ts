/**
 * useGameWebSocket - Real-time game simulation via WebSocket
 *
 * Connects to the Coach Mode API for V2 game simulation:
 * - Auto-play spectator mode (watch AI vs AI with V2 physics-based simulation)
 * - Real-time play-by-play updates
 * - Pacing controls (slow/normal/fast)
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import type { GameSituation, PlayResult, DrivePlay } from '../types';
import type { PlayFrame } from '../components/PlayCanvas';

// Coach API endpoints (V2 simulation)
const API_BASE = '/api/v1/coach';
const WS_BASE = 'ws://localhost:8000/api/v1/coach';

export type Pacing = 'slow' | 'normal' | 'fast' | 'step';

interface TeamInfo {
  id: string;
  name: string;
  abbreviation: string;
}

interface UseGameWebSocketResult {
  // Connection state
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;

  // Game state
  gameId: string | null;
  situation: GameSituation | null;
  homeTeam: TeamInfo | null;
  awayTeam: TeamInfo | null;
  lastResult: PlayResult | null;
  currentDrive: DrivePlay[];
  playLog: Array<{
    description: string;
    quarter: number;
    time: string;
    isScoring: boolean;
    isTurnover: boolean;
  }>;

  // Simulation state
  isPaused: boolean;
  pacing: Pacing;
  gameOver: boolean;

  // Play visualization
  playFrames: PlayFrame[];
  currentPlayTick: number;
  isPlayAnimating: boolean;
  playbackSpeed: number;
  setCurrentPlayTick: (tick: number) => void;
  setIsPlayAnimating: (animating: boolean) => void;
  setPlaybackSpeed: (speed: number) => void;

  // Announcement
  announcement: {
    type: 'kickoff' | 'punt' | 'field_goal' | 'touchdown' | 'turnover' | 'drive_start' | 'pat' | 'safety' | null;
    message: string;
    subtext?: string;
  } | null;

  // Actions
  startGame: (homeTeamCode: string, awayTeamCode: string) => Promise<void>;
  setPacing: (pacing: Pacing) => void;
  togglePause: () => void;
  step: () => void;
  endGame: () => void;
}

export function useGameWebSocket(): UseGameWebSocketResult {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [gameId, setGameId] = useState<string | null>(null);
  const [situation, setSituation] = useState<GameSituation | null>(null);
  const [homeTeam, setHomeTeam] = useState<TeamInfo | null>(null);
  const [awayTeam, setAwayTeam] = useState<TeamInfo | null>(null);
  const [lastResult, setLastResult] = useState<PlayResult | null>(null);
  const [currentDrive, setCurrentDrive] = useState<DrivePlay[]>([]);
  const [playLog, setPlayLog] = useState<Array<{
    description: string;
    quarter: number;
    time: string;
    isScoring: boolean;
    isTurnover: boolean;
  }>>([]);

  const [isPaused, setIsPaused] = useState(false);
  const [pacing, setPacingState] = useState<Pacing>('step');
  const [gameOver, setGameOver] = useState(false);

  // Play visualization state
  const [playFrames, setPlayFrames] = useState<PlayFrame[]>([]);
  const [currentPlayTick, setCurrentPlayTick] = useState(0);
  const [isPlayAnimating, setIsPlayAnimating] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  // Announcement for major events (kickoff, punt, TD, etc.)
  const [announcement, setAnnouncement] = useState<{
    type: 'kickoff' | 'punt' | 'field_goal' | 'touchdown' | 'turnover' | 'drive_start' | 'pat' | 'safety' | null;
    message: string;
    subtext?: string;
  } | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const driveStartLosRef = useRef<number>(25);

  // Auto-dismiss announcements after a delay
  const showAnnouncement = useCallback((
    type: 'kickoff' | 'punt' | 'field_goal' | 'touchdown' | 'turnover' | 'drive_start' | 'pat' | 'safety',
    message: string,
    subtext?: string,
    duration: number = 3000
  ) => {
    setAnnouncement({ type, message, subtext });
    setTimeout(() => setAnnouncement(null), duration);
  }, []);

  // Parse situation from coach API response format
  const parseSituation = useCallback((sitData: Record<string, unknown>): GameSituation => {
    return {
      quarter: sitData.quarter as number,
      timeRemaining: sitData.time_remaining as string,
      down: sitData.down as number,
      distance: sitData.distance as number,
      los: sitData.los as number,
      yardLineDisplay: sitData.yard_line_display as string,
      homeScore: sitData.home_score as number,
      awayScore: sitData.away_score as number,
      possessionHome: sitData.possession_home as boolean,
      isRedZone: sitData.is_red_zone as boolean,
      isGoalToGo: sitData.is_goal_to_go as boolean,
      userOnOffense: true, // Spectator mode - always watching
      homeTimeouts: 3,
      awayTimeouts: 3,
    };
  }, []);

  // Handle WebSocket messages from Coach API
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message = JSON.parse(event.data);
      console.log('[WS Coach] Received:', message.type, message);

      switch (message.type) {
        case 'connected': {
          // Initial connection with situation
          if (message.situation) {
            setSituation(parseSituation(message.situation));
            driveStartLosRef.current = message.situation.los;
          }
          break;
        }

        case 'auto_play_started': {
          console.log('[WS Coach] Auto-play started with pacing:', message.pacing);
          setIsPaused(false);
          if (message.pacing) {
            setPacingState(message.pacing as Pacing);
          }
          break;
        }

        case 'drive_start': {
          // New drive starting
          setCurrentDrive([]);
          const startLos = Math.max(1, Math.min(99, message.starting_los || 25));
          driveStartLosRef.current = startLos;

          // Update possession in situation
          setSituation(prev => prev ? {
            ...prev,
            possessionHome: message.offense_is_home ?? prev.possessionHome,
            los: startLos,
            down: 1,
            distance: 10,
          } : prev);

          // Show announcement
          const teamName = message.offense || 'Team';
          const yardLine = startLos <= 50 ? `own ${startLos}` : `opp ${100 - startLos}`;
          showAnnouncement('drive_start', `${teamName} BALL`, `1st & 10 at the ${yardLine}`);

          setPlayLog(prev => [...prev, {
            description: `${teamName} ball at the ${yardLine}`,
            quarter: message.quarter || 1,
            time: message.time_remaining || '15:00',
            isScoring: false,
            isTurnover: false,
          }]);
          break;
        }

        case 'play_frames': {
          // Received frame data for play visualization
          console.log('[WS Coach] Received play frames:', message.total_frames);
          const frames = message.frames || [];
          setPlayFrames(frames);
          setCurrentPlayTick(0);
          setIsPlayAnimating(true);  // Auto-start playback
          break;
        }

        case 'play_result': {
          const result = message.result || {};

          // Map to our PlayResult type
          const playResult: PlayResult = {
            outcome: result.outcome?.toLowerCase() || 'complete',
            yardsGained: result.yards_gained || 0,
            description: result.description || 'Play completed',
            newDown: result.new_down || 1,
            newDistance: result.new_distance || 10,
            newLos: result.new_los || 25,
            firstDown: result.first_down || false,
            touchdown: result.touchdown || false,
            turnover: result.turnover || false,
            isDriveOver: result.is_drive_over || false,
          };
          setLastResult(playResult);

          // Show announcements for big plays
          if (result.touchdown) {
            showAnnouncement('touchdown', 'TOUCHDOWN!', result.description, 4000);
          } else if (result.turnover) {
            const turnoverType = result.outcome === 'interception' ? 'INTERCEPTION!' : 'FUMBLE!';
            showAnnouncement('turnover', turnoverType, 'Turnover - change of possession', 3000);
          }

          // Update situation from result (use ?? for numbers to handle 0 correctly)
          setSituation(prev => {
            if (!prev) return prev;
            const newLos = result.new_los ?? prev.los;
            const clampedLos = Math.max(1, Math.min(99, newLos)); // Clamp to valid field range
            const newDistance = result.new_distance ?? prev.distance;
            return {
              ...prev,
              down: result.new_down ?? prev.down,
              distance: newDistance,
              los: clampedLos,
              yardLineDisplay: clampedLos >= 50
                ? `OPP ${100 - Math.round(clampedLos)}`
                : `OWN ${Math.round(clampedLos)}`,
              isRedZone: clampedLos >= 80,
              isGoalToGo: newDistance >= (100 - clampedLos),
              possessionHome: result.offense_is_home ?? prev.possessionHome,
            };
          });

          // Add to drive (if not turnover/score)
          if (!result.turnover && !result.touchdown) {
            const playLos = Math.max(1, Math.min(99, result.new_los ?? 25));
            setCurrentDrive(prev => [...prev, {
              playNumber: prev.length + 1,
              down: prev.length > 0 ? prev[prev.length - 1].down : 1,
              distance: result.new_distance ?? 10,
              los: playLos,
              playType: result.outcome?.includes('pass') || result.outcome?.includes('complete') || result.outcome?.includes('incomplete') ? 'pass' : 'run',
              playName: result.play_call || result.outcome || 'Play',
              yardsGained: Math.round(result.yards_gained ?? 0),
              outcome: result.outcome || 'complete',
              isFirstDown: result.first_down || false,
            }]);
          } else {
            // Drive ended - reset
            setCurrentDrive([]);
            driveStartLosRef.current = Math.max(1, Math.min(99, result.new_los ?? 25));
          }

          // Add to play log
          setPlayLog(prev => [...prev, {
            description: result.description || 'Play completed',
            quarter: situation?.quarter || 1,
            time: situation?.timeRemaining || '0:00',
            isScoring: result.touchdown || false,
            isTurnover: result.turnover || false,
          }]);
          break;
        }

        case 'special_teams': {
          const result = message.result || {};
          const playType = result.play_type || 'special';

          // Show announcement based on play type
          if (playType === 'kickoff') {
            showAnnouncement('kickoff', 'KICKOFF', result.description || 'Ball kicked off');
          } else if (playType === 'punt') {
            showAnnouncement('punt', 'PUNT', result.description || 'Ball punted away');
          } else if (playType === 'field_goal') {
            const made = result.result === 'good' || (result.points_scored || 0) > 0;
            showAnnouncement('field_goal', made ? 'FIELD GOAL!' : 'NO GOOD', result.description);
          } else if (playType === 'pat') {
            const made = (result.points_scored || 0) > 0;
            showAnnouncement('pat', made ? 'EXTRA POINT GOOD' : 'PAT NO GOOD', '');
          }

          // Update LOS if provided
          if (result.new_los !== undefined) {
            const newLos = Math.max(1, Math.min(99, result.new_los));
            setSituation(prev => prev ? { ...prev, los: newLos } : prev);
          }

          // Add to play log
          setPlayLog(prev => [...prev, {
            description: result.description || `${playType} play`,
            quarter: situation?.quarter || 1,
            time: situation?.timeRemaining || '0:00',
            isScoring: (result.points_scored || 0) > 0,
            isTurnover: false,
          }]);

          // Reset drive after special teams
          if (result.play_type === 'kickoff' || result.play_type === 'punt') {
            setCurrentDrive([]);
            driveStartLosRef.current = result.new_los || 25;
          }
          break;
        }

        case 'situation_update': {
          if (message.situation) {
            setSituation(parseSituation(message.situation));
          }
          break;
        }

        case 'score_update': {
          setSituation(prev => prev ? {
            ...prev,
            homeScore: message.home_score ?? prev.homeScore,
            awayScore: message.away_score ?? prev.awayScore,
          } : prev);
          break;
        }

        case 'drive_ended': {
          // Drive finished summary
          setCurrentDrive([]);
          setPlayLog(prev => [...prev, {
            description: `Drive ended: ${message.result || 'possession change'}`,
            quarter: situation?.quarter || 1,
            time: situation?.timeRemaining || '0:00',
            isScoring: message.result === 'touchdown' || message.result === 'field_goal',
            isTurnover: message.result === 'turnover' || message.result === 'turnover_on_downs',
          }]);
          break;
        }

        case 'game_over': {
          setGameOver(true);
          const finalScore = message.final_score || {};
          setSituation(prev => prev ? {
            ...prev,
            homeScore: finalScore.home ?? prev.homeScore,
            awayScore: finalScore.away ?? prev.awayScore,
          } : prev);
          setPlayLog(prev => [...prev, {
            description: `FINAL: ${homeTeam?.abbreviation || 'Home'} ${finalScore.home || 0} - ${awayTeam?.abbreviation || 'Away'} ${finalScore.away || 0}`,
            quarter: 4,
            time: '0:00',
            isScoring: false,
            isTurnover: false,
          }]);
          break;
        }

        case 'auto_play_paused': {
          setIsPaused(true);
          break;
        }

        case 'auto_play_resumed': {
          setIsPaused(false);
          break;
        }

        case 'auto_play_stopped': {
          setIsPaused(true);
          break;
        }

        case 'pacing_changed': {
          if (message.pacing) {
            setPacingState(message.pacing as Pacing);
          }
          break;
        }

        case 'error': {
          console.error('[WS Coach] Error:', message.message);
          setError(message.message || 'WebSocket error');
          break;
        }

        case 'pong':
        case 'keep_alive': {
          // Ignore keep-alive messages
          break;
        }

        default: {
          console.log('[WS Coach] Unknown message type:', message.type);
        }
      }
    } catch (err) {
      console.error('[WS Coach] Failed to parse message:', err);
    }
  }, [parseSituation, situation, homeTeam, awayTeam]);

  // Start a new game using Coach API (V2 simulation)
  const startGame = useCallback(async (homeTeamCode: string, awayTeamCode: string) => {
    setIsLoading(true);
    setError(null);
    setGameOver(false);
    setPlayLog([]);
    setCurrentDrive([]);
    setLastResult(null);
    setIsPaused(false);

    try {
      // 1. Create game via Coach API
      console.log('[Coach] Creating game:', homeTeamCode, 'vs', awayTeamCode);
      const response = await fetch(`${API_BASE}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          home_team_abbr: homeTeamCode,
          away_team_abbr: awayTeamCode,
          user_controls_home: true,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to create game: ${response.statusText}`);
      }

      const data = await response.json();
      const newGameId = data.game_id;

      if (!newGameId) {
        throw new Error('No game ID returned from server');
      }

      console.log('[Coach] Game created:', newGameId);
      setGameId(newGameId);

      // Set team info
      setHomeTeam({
        id: newGameId + '_home',
        name: data.home_team_name || homeTeamCode,
        abbreviation: homeTeamCode,
      });
      setAwayTeam({
        id: newGameId + '_away',
        name: data.away_team_name || awayTeamCode,
        abbreviation: awayTeamCode,
      });

      // Set initial situation
      if (data.situation) {
        setSituation(parseSituation(data.situation));
      }

      // 2. Connect WebSocket
      console.log('[Coach] Connecting WebSocket...');
      const ws = new WebSocket(`${WS_BASE}/${newGameId}/stream`);

      ws.onopen = async () => {
        console.log('[Coach WS] Connected to game:', newGameId);
        setIsConnected(true);
        setIsLoading(false);

        // 3. Start auto-play only if NOT in step mode
        if (pacing !== 'step') {
          console.log('[Coach] Starting auto-play...');
          try {
            const autoPlayResponse = await fetch(`${API_BASE}/${newGameId}/auto-play`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ pacing: pacing }),
            });

            if (!autoPlayResponse.ok) {
              const errorData = await autoPlayResponse.json().catch(() => ({}));
              console.error('[Coach] Failed to start auto-play:', errorData);
              setError(errorData.detail || 'Failed to start auto-play');
            } else {
              console.log('[Coach] Auto-play started');
            }
          } catch (err) {
            console.error('[Coach] Auto-play error:', err);
            setError('Failed to start auto-play');
          }
        } else {
          console.log('[Coach] Step mode - ready for manual play advancement');
          setIsPaused(true);
        }
      };

      ws.onmessage = handleMessage;

      ws.onerror = (event) => {
        console.error('[Coach WS] Error:', event);
        setError('WebSocket connection error');
        setIsLoading(false);
      };

      ws.onclose = () => {
        console.log('[Coach WS] Disconnected');
        setIsConnected(false);
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('[Coach] Failed to start game:', err);
      setError(err instanceof Error ? err.message : 'Failed to start game');
      setIsLoading(false);
    }
  }, [handleMessage, parseSituation, pacing]);

  // Send pacing update via WebSocket
  const setPacing = useCallback(async (newPacing: Pacing) => {
    const oldPacing = pacing;
    setPacingState(newPacing);

    if (!gameId) return;

    // Switching to step mode: stop auto-play
    if (newPacing === 'step' && oldPacing !== 'step') {
      try {
        await fetch(`/api/v1/coach/${gameId}/auto-play/stop`, { method: 'POST' });
        setIsPaused(true);
        console.log('[Coach] Switched to step mode, auto-play stopped');
      } catch (err) {
        console.error('[Coach] Failed to stop auto-play:', err);
      }
    }
    // Switching from step mode to auto-play: start auto-play
    else if (newPacing !== 'step' && oldPacing === 'step') {
      try {
        const response = await fetch(`/api/v1/coach/${gameId}/auto-play`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pacing: newPacing }),
        });
        if (response.ok) {
          setIsPaused(false);
          console.log('[Coach] Switched to auto-play mode');
        }
      } catch (err) {
        console.error('[Coach] Failed to start auto-play:', err);
      }
    }
    // Already in auto-play, just change pacing
    else if (newPacing !== 'step') {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'set_pacing',
          payload: { pacing: newPacing },
        }));
      }
    }
  }, [gameId, pacing]);

  // Toggle pause/resume via WebSocket
  const togglePause = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: isPaused ? 'resume' : 'pause',
      }));
      // Optimistic update - will be confirmed by server message
      setIsPaused(!isPaused);
    }
  }, [isPaused]);

  // Step forward one play (for step mode)
  const step = useCallback(async () => {
    if (!gameId) {
      console.log('[Coach] No game to step');
      return;
    }

    try {
      const response = await fetch(`/api/v1/coach/${gameId}/step`, {
        method: 'POST',
      });

      if (!response.ok) {
        const error = await response.json();
        console.error('[Coach] Step failed:', error.detail || 'Unknown error');
      }
      // Results will come through WebSocket
    } catch (err) {
      console.error('[Coach] Step error:', err);
    }
  }, [gameId]);

  // End game and disconnect
  const endGame = useCallback(() => {
    // Stop auto-play if running
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'stop_auto_play',
      }));
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    setGameId(null);
    setSituation(null);
    setHomeTeam(null);
    setAwayTeam(null);
    setLastResult(null);
    setCurrentDrive([]);
    setPlayLog([]);
    setGameOver(false);
    setIsPaused(false);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    isConnected,
    isLoading,
    error,
    gameId,
    situation,
    homeTeam,
    awayTeam,
    lastResult,
    currentDrive,
    playLog,
    isPaused,
    pacing,
    gameOver,
    // Play visualization
    playFrames,
    currentPlayTick,
    isPlayAnimating,
    playbackSpeed,
    setCurrentPlayTick,
    setIsPlayAnimating,
    setPlaybackSpeed,
    announcement,
    startGame,
    setPacing,
    togglePause,
    step,
    endGame,
  };
}

export default useGameWebSocket;
