/**
 * useCoachAPI - Hook for coach mode API integration
 *
 * Provides:
 * - Game session management (start, end)
 * - Situation fetching
 * - Play calling (offense and defense)
 * - Special teams
 * - Box score
 */

import { useState, useCallback } from 'react';
import type {
  GameSituation,
  PlayResult,
  PlayOption,
  BoxScore,
  DriveResult,
} from '../types';

const API_BASE = '/api/v1/coach';

interface UseCoachAPIResult {
  // State
  gameId: string | null;
  situation: GameSituation | null;
  availablePlays: PlayOption[];
  lastResult: PlayResult | null;
  boxScore: BoxScore | null;
  loading: boolean;
  error: string | null;

  // Actions
  startGame: (homeTeam: string, awayTeam: string) => Promise<void>;
  endGame: () => Promise<void>;
  fetchSituation: () => Promise<void>;
  fetchPlays: () => Promise<void>;
  executePlay: (playCode: string, shotgun?: boolean) => Promise<PlayResult>;
  executeDefense: (coverage: string, blitz: string) => Promise<PlayResult>;
  executeSpecialTeams: (playType: string, options?: Record<string, boolean>) => Promise<void>;
  fetchBoxScore: () => Promise<BoxScore>;
}

export function useCoachAPI(): UseCoachAPIResult {
  const [gameId, setGameId] = useState<string | null>(null);
  const [situation, setSituation] = useState<GameSituation | null>(null);
  const [availablePlays, setAvailablePlays] = useState<PlayOption[]>([]);
  const [lastResult, setLastResult] = useState<PlayResult | null>(null);
  const [boxScore, setBoxScore] = useState<BoxScore | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Start a new game
  // Note: The API currently requires team UUIDs from a loaded league.
  // For demo/development, we operate in mock mode without the API.
  const startGame = useCallback(async (homeTeam: string, awayTeam: string) => {
    setLoading(true);
    setError(null);
    try {
      // For now, skip the API call since it requires UUIDs from a loaded league
      // The GameView operates in mock mode for demo purposes
      // TODO: Wire up to real API when league selection is integrated
      console.log(`Starting game: ${homeTeam} vs ${awayTeam} (mock mode)`);

      // Set a mock game ID to indicate we're "in a game" even without API
      setGameId(`mock_${Date.now()}`);

      // In real implementation with a league loaded:
      // const response = await fetch(`${API_BASE}/start`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({
      //     home_team_id: homeTeamUUID,
      //     away_team_id: awayTeamUUID,
      //     user_controls_home: true
      //   }),
      // });
      // const data = await response.json();
      // setGameId(data.game_id);
      // await fetchSituationInternal(data.game_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start game');
    } finally {
      setLoading(false);
    }
  }, []);

  // End the current game
  const endGame = useCallback(async () => {
    if (!gameId) return;

    setLoading(true);
    try {
      await fetch(`${API_BASE}/${gameId}`, { method: 'DELETE' });
      setGameId(null);
      setSituation(null);
      setAvailablePlays([]);
      setLastResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to end game');
    } finally {
      setLoading(false);
    }
  }, [gameId]);

  // Internal fetch situation
  const fetchSituationInternal = async (gid: string) => {
    const response = await fetch(`${API_BASE}/${gid}/situation`);
    if (!response.ok) {
      throw new Error(`Failed to fetch situation: ${response.statusText}`);
    }

    const data = await response.json();
    setSituation(mapSituationFromAPI(data));
  };

  // Fetch current situation
  const fetchSituation = useCallback(async () => {
    if (!gameId) return;

    setLoading(true);
    setError(null);
    try {
      await fetchSituationInternal(gameId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch situation');
    } finally {
      setLoading(false);
    }
  }, [gameId]);

  // Fetch available plays
  const fetchPlays = useCallback(async () => {
    if (!gameId) return;

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/${gameId}/plays`);
      if (!response.ok) {
        throw new Error(`Failed to fetch plays: ${response.statusText}`);
      }

      const data = await response.json();
      setAvailablePlays(mapPlaysFromAPI(data.plays, data.recommended));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch plays');
    } finally {
      setLoading(false);
    }
  }, [gameId]);

  // Execute an offensive play
  const executePlay = useCallback(async (playCode: string, shotgun = true): Promise<PlayResult> => {
    if (!gameId) {
      throw new Error('No game in progress');
    }

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/${gameId}/play`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ play_code: playCode, shotgun }),
      });

      if (!response.ok) {
        throw new Error(`Failed to execute play: ${response.statusText}`);
      }

      const data = await response.json();
      const result = mapResultFromAPI(data);
      setLastResult(result);

      // Update situation
      setSituation(prev => prev ? {
        ...prev,
        down: data.new_down,
        distance: data.new_distance,
        los: data.new_los,
        yardLineDisplay: formatYardLine(data.new_los),
        isRedZone: data.new_los >= 80,
        isGoalToGo: data.new_distance >= (100 - data.new_los),
      } : null);

      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to execute play';
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  }, [gameId]);

  // Execute defensive play (simulate opponent offense)
  const executeDefense = useCallback(async (coverage: string, blitz: string): Promise<PlayResult> => {
    if (!gameId) {
      throw new Error('No game in progress');
    }

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/${gameId}/simulate-defense`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ coverage, blitz }),
      });

      if (!response.ok) {
        throw new Error(`Failed to execute defense: ${response.statusText}`);
      }

      const data = await response.json();
      const result = mapResultFromAPI(data);
      setLastResult(result);

      // Update situation after defensive play
      await fetchSituationInternal(gameId);

      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to execute defense';
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  }, [gameId]);

  // Execute special teams play
  const executeSpecialTeams = useCallback(async (
    playType: string,
    options: Record<string, boolean> = {}
  ) => {
    if (!gameId) return;

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/${gameId}/special`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ play_type: playType, ...options }),
      });

      if (!response.ok) {
        throw new Error(`Failed to execute special teams: ${response.statusText}`);
      }

      // Update situation after special teams
      await fetchSituationInternal(gameId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute special teams');
    } finally {
      setLoading(false);
    }
  }, [gameId]);

  // Fetch box score
  const fetchBoxScore = useCallback(async (): Promise<BoxScore> => {
    if (!gameId) {
      throw new Error('No game in progress');
    }

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/${gameId}/box-score`);
      if (!response.ok) {
        throw new Error(`Failed to fetch box score: ${response.statusText}`);
      }

      const data = await response.json();
      const score = mapBoxScoreFromAPI(data);
      setBoxScore(score);
      return score;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch box score';
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  }, [gameId]);

  return {
    gameId,
    situation,
    availablePlays,
    lastResult,
    boxScore,
    loading,
    error,
    startGame,
    endGame,
    fetchSituation,
    fetchPlays,
    executePlay,
    executeDefense,
    executeSpecialTeams,
    fetchBoxScore,
  };
}

// API response mappers
function mapSituationFromAPI(data: any): GameSituation {
  return {
    quarter: data.quarter,
    timeRemaining: data.time_remaining,
    down: data.down,
    distance: data.distance,
    los: data.los,
    yardLineDisplay: data.yard_line_display || formatYardLine(data.los),
    homeScore: data.home_score,
    awayScore: data.away_score,
    possessionHome: data.possession_home,
    isRedZone: data.is_red_zone || data.los >= 80,
    isGoalToGo: data.is_goal_to_go || false,
    userOnOffense: data.user_on_offense ?? true,
    homeTimeouts: data.home_timeouts ?? 3,
    awayTimeouts: data.away_timeouts ?? 3,
  };
}

function mapPlaysFromAPI(plays: string[], recommended?: string): PlayOption[] {
  // Map play codes to PlayOption objects
  return plays.map(code => ({
    code,
    name: formatPlayName(code),
    category: categorizePlay(code),
    isRecommended: code === recommended,
  }));
}

function mapResultFromAPI(data: any): PlayResult {
  return {
    outcome: data.outcome,
    yardsGained: data.yards_gained,
    description: data.description,
    newDown: data.new_down,
    newDistance: data.new_distance,
    newLos: data.new_los,
    firstDown: data.first_down || false,
    touchdown: data.touchdown || false,
    turnover: data.turnover || false,
    isDriveOver: data.is_drive_over || false,
    driveEndReason: data.drive_end_reason,
    passerName: data.passer_name,
    receiverName: data.receiver_name,
    tacklerName: data.tackler_name,
  };
}

function mapBoxScoreFromAPI(data: any): BoxScore {
  return {
    home: {
      totalYards: data.home?.total_yards ?? 0,
      passingYards: data.home?.passing_yards ?? 0,
      rushingYards: data.home?.rushing_yards ?? 0,
      firstDowns: data.home?.first_downs ?? 0,
      turnovers: data.home?.turnovers ?? 0,
      timeOfPossession: data.home?.time_of_possession ?? '0:00',
      thirdDownConversions: data.home?.third_down ?? '0/0',
    },
    away: {
      totalYards: data.away?.total_yards ?? 0,
      passingYards: data.away?.passing_yards ?? 0,
      rushingYards: data.away?.rushing_yards ?? 0,
      firstDowns: data.away?.first_downs ?? 0,
      turnovers: data.away?.turnovers ?? 0,
      timeOfPossession: data.away?.time_of_possession ?? '0:00',
      thirdDownConversions: data.away?.third_down ?? '0/0',
    },
  };
}

function formatYardLine(los: number): string {
  if (los <= 50) {
    return `OWN ${los}`;
  } else {
    return `OPP ${100 - los}`;
  }
}

function formatPlayName(code: string): string {
  return code
    .replace(/_/g, ' ')
    .replace(/^(PASS|RUN)\s+/i, '')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

function categorizePlay(code: string): 'run' | 'quick' | 'intermediate' | 'deep' | 'screen' | 'play_action' {
  const lower = code.toLowerCase();

  if (lower.includes('run') || lower.includes('zone') || lower.includes('power') ||
      lower.includes('draw') || lower.includes('counter') || lower.includes('stretch') ||
      lower.includes('toss')) {
    return 'run';
  }

  if (lower.includes('screen')) {
    return 'screen';
  }

  if (lower.includes('play_action') || lower.includes('pa_') || lower.includes('bootleg')) {
    return 'play_action';
  }

  if (lower.includes('slant') || lower.includes('quick') || lower.includes('hitch') ||
      lower.includes('flat') || lower.includes('out')) {
    return 'quick';
  }

  if (lower.includes('post') || lower.includes('go') || lower.includes('vert') ||
      lower.includes('bomb') || lower.includes('streak') || lower.includes('fade')) {
    return 'deep';
  }

  return 'intermediate';
}

export default useCoachAPI;
