/**
 * GameStartFlow - Initial game setup screen
 *
 * Handles:
 * - Team selection (home vs away) from loaded league
 * - User team choice
 * - Game start trigger
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Play, Users, Home, Plane, Eye, Gamepad2, AlertCircle, Loader2, Database, RefreshCw, Plus } from 'lucide-react';

// NFL team colors and logos (primary, secondary, logo filename)
export const TEAM_COLORS: Record<string, { primary: string; secondary: string; logo: string }> = {
  ARI: { primary: '#97233F', secondary: '#000000', logo: 'Arizona_Cardinals_logo.svg' },
  ATL: { primary: '#A71930', secondary: '#000000', logo: 'Atlanta_Falcons_logo.svg' },
  BAL: { primary: '#241773', secondary: '#000000', logo: 'Baltimore_Ravens_logo.svg' },
  BUF: { primary: '#00338D', secondary: '#C60C30', logo: 'Buffalo_Bills_logo.svg' },
  CAR: { primary: '#0085CA', secondary: '#101820', logo: 'Carolina_Panthers_logo.svg' },
  CHI: { primary: '#0B162A', secondary: '#C83803', logo: 'Chicago_Bears_logo.svg' },
  CIN: { primary: '#FB4F14', secondary: '#000000', logo: 'Cincinnati_Bengals_logo.svg' },
  CLE: { primary: '#311D00', secondary: '#FF3C00', logo: 'Cleveland_Browns_logo.svg' },
  DAL: { primary: '#003594', secondary: '#869397', logo: 'Dallas_Cowboys.svg' },
  DEN: { primary: '#FB4F14', secondary: '#002244', logo: 'Denver_Broncos_logo.svg' },
  DET: { primary: '#0076B6', secondary: '#B0B7BC', logo: 'Detroit_Lions_logo.svg' },
  GB: { primary: '#203731', secondary: '#FFB612', logo: 'Green_Bay_Packers_logo.svg' },
  HOU: { primary: '#03202F', secondary: '#A71930', logo: 'Houston_Texans_logo.svg' },
  IND: { primary: '#002C5F', secondary: '#A2AAAD', logo: 'Indianapolis_Colts_logo.svg' },
  JAX: { primary: '#006778', secondary: '#D7A22A', logo: 'Jacksonville_Jaguars_logo.svg' },
  KC: { primary: '#E31837', secondary: '#FFB81C', logo: 'Kansas_City_Chiefs_logo.svg' },
  LV: { primary: '#000000', secondary: '#A5ACAF', logo: 'Las_Vegas_Raiders_logo.svg' },
  LAC: { primary: '#0080C6', secondary: '#FFC20E', logo: 'Los_Angeles_Chargers_logo.svg' },
  LAR: { primary: '#003594', secondary: '#FFA300', logo: 'Los_Angeles_Rams_logo.svg' },
  MIA: { primary: '#008E97', secondary: '#FC4C02', logo: 'Miami_Dolphins_logo.svg' },
  MIN: { primary: '#4F2683', secondary: '#FFC62F', logo: 'Minnesota_Vikings_logo.svg' },
  NE: { primary: '#002244', secondary: '#C60C30', logo: 'New_England_Patriots_logo.svg' },
  NO: { primary: '#D3BC8D', secondary: '#101820', logo: 'New_Orleans_Saints_logo.svg' },
  NYG: { primary: '#0B2265', secondary: '#A71930', logo: 'New_York_Giants_logo.svg' },
  NYJ: { primary: '#125740', secondary: '#000000', logo: 'New_York_Jets_logo.svg' },
  PHI: { primary: '#004C54', secondary: '#A5ACAF', logo: 'Philadelphia_Eagles_logo.svg' },
  PIT: { primary: '#FFB612', secondary: '#101820', logo: 'Pittsburgh_Steelers_logo.svg' },
  SF: { primary: '#AA0000', secondary: '#B3995D', logo: 'San_Francisco_49ers_logo.svg' },
  SEA: { primary: '#002244', secondary: '#69BE28', logo: 'Seattle_Seahawks_logo.svg' },
  TB: { primary: '#D50A0A', secondary: '#FF7900', logo: 'Tampa_Bay_Buccaneers_logo.svg' },
  TEN: { primary: '#0C2340', secondary: '#4B92DB', logo: 'Tennessee_Titans_logo.svg' },
  WAS: { primary: '#5A1414', secondary: '#FFB612', logo: 'Washington_Commanders_logo.svg' },
};

interface TeamData {
  id: string;
  abbreviation: string;
  name: string;
  city: string;
  nickname: string;
  conference: string;
  division: string;
}

interface SavedLeague {
  id: string;
  name: string;
  season: number;
  created_at: string;
}

export type GameMode = 'coach' | 'spectator';

interface GameStartFlowProps {
  onStartGame: (homeTeam: string, awayTeam: string, userIsHome: boolean, mode: GameMode) => void;
  loading?: boolean;
}

export const GameStartFlow: React.FC<GameStartFlowProps> = ({
  onStartGame,
  loading = false,
}) => {
  const [homeTeam, setHomeTeam] = useState<string>('');
  const [awayTeam, setAwayTeam] = useState<string>('');
  const [userIsHome, setUserIsHome] = useState<boolean>(true);
  const [filterConference, setFilterConference] = useState<'ALL' | 'AFC' | 'NFC'>('ALL');
  const [gameMode, setGameMode] = useState<GameMode>('spectator');

  // Team data from management API
  const [teams, setTeams] = useState<TeamData[]>([]);
  const [leagueLoaded, setLeagueLoaded] = useState<boolean>(true);
  const [teamsLoading, setTeamsLoading] = useState<boolean>(true);
  const [teamsError, setTeamsError] = useState<string | null>(null);

  // Saved leagues for league picker
  const [savedLeagues, setSavedLeagues] = useState<SavedLeague[]>([]);
  const [leaguesLoading, setLeaguesLoading] = useState<boolean>(false);
  const [loadingLeagueId, setLoadingLeagueId] = useState<string | null>(null);
  const [generatingLeague, setGeneratingLeague] = useState<boolean>(false);

  // Fetch teams from management API on mount
  useEffect(() => {
    const fetchTeams = async () => {
      setTeamsLoading(true);
      setTeamsError(null);

      try {
        const response = await fetch('/api/v1/management/teams');
        if (!response.ok) {
          throw new Error(`Failed to fetch teams: ${response.statusText}`);
        }

        const data = await response.json();
        setTeams(data.teams || []);
        setLeagueLoaded(data.league_loaded ?? false);

        // Set default teams if available
        if (data.teams && data.teams.length >= 2) {
          const sortedTeams = [...data.teams].sort((a: TeamData, b: TeamData) =>
            a.abbreviation.localeCompare(b.abbreviation)
          );
          // Default to first two teams alphabetically
          setHomeTeam(sortedTeams[0]?.abbreviation || '');
          setAwayTeam(sortedTeams[1]?.abbreviation || '');
        }
      } catch (err) {
        console.error('Failed to fetch teams:', err);
        setTeamsError(err instanceof Error ? err.message : 'Failed to load teams');
        setLeagueLoaded(false);
      } finally {
        setTeamsLoading(false);
      }
    };

    fetchTeams();
  }, []);

  // Fetch saved leagues when no league is loaded
  const fetchSavedLeagues = useCallback(async () => {
    setLeaguesLoading(true);
    try {
      const response = await fetch('/api/v1/admin/leagues');
      if (response.ok) {
        const data = await response.json();
        setSavedLeagues(data || []);
      }
    } catch (err) {
      console.error('Failed to fetch saved leagues:', err);
    } finally {
      setLeaguesLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!leagueLoaded && !teamsLoading) {
      fetchSavedLeagues();
    }
  }, [leagueLoaded, teamsLoading, fetchSavedLeagues]);

  // Load a saved league
  const handleLoadLeague = async (leagueId: string) => {
    setLoadingLeagueId(leagueId);
    try {
      const response = await fetch(`/api/v1/admin/league/load/${leagueId}`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to load league');
      }
      // Refresh teams after loading
      setTeamsLoading(true);
      setTeamsError(null);
      const teamsResponse = await fetch('/api/v1/management/teams');
      if (teamsResponse.ok) {
        const data = await teamsResponse.json();
        setTeams(data.teams || []);
        setLeagueLoaded(data.league_loaded ?? false);
        if (data.teams && data.teams.length >= 2) {
          const sortedTeams = [...data.teams].sort((a: TeamData, b: TeamData) =>
            a.abbreviation.localeCompare(b.abbreviation)
          );
          setHomeTeam(sortedTeams[0]?.abbreviation || '');
          setAwayTeam(sortedTeams[1]?.abbreviation || '');
        }
      }
    } catch (err) {
      console.error('Failed to load league:', err);
      setTeamsError(err instanceof Error ? err.message : 'Failed to load league');
    } finally {
      setLoadingLeagueId(null);
      setTeamsLoading(false);
    }
  };

  // Generate a new league
  const handleGenerateLeague = async () => {
    setGeneratingLeague(true);
    try {
      const response = await fetch('/api/v1/admin/league/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ season: 2024, include_schedule: true }),
      });
      if (!response.ok) {
        throw new Error('Failed to generate league');
      }
      // Refresh teams after generating
      setTeamsLoading(true);
      setTeamsError(null);
      const teamsResponse = await fetch('/api/v1/management/teams');
      if (teamsResponse.ok) {
        const data = await teamsResponse.json();
        setTeams(data.teams || []);
        setLeagueLoaded(data.league_loaded ?? false);
        if (data.teams && data.teams.length >= 2) {
          const sortedTeams = [...data.teams].sort((a: TeamData, b: TeamData) =>
            a.abbreviation.localeCompare(b.abbreviation)
          );
          setHomeTeam(sortedTeams[0]?.abbreviation || '');
          setAwayTeam(sortedTeams[1]?.abbreviation || '');
        }
      }
    } catch (err) {
      console.error('Failed to generate league:', err);
      setTeamsError(err instanceof Error ? err.message : 'Failed to generate league');
    } finally {
      setGeneratingLeague(false);
      setTeamsLoading(false);
    }
  };

  // Format date for display
  const formatDate = (isoString: string): string => {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(hours / 24);

    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
    if (days < 7) return `${days} day${days === 1 ? '' : 's'} ago`;
    return date.toLocaleDateString();
  };

  const handleStartGame = useCallback(() => {
    if (homeTeam && awayTeam && homeTeam !== awayTeam) {
      onStartGame(homeTeam, awayTeam, userIsHome, gameMode);
    }
  }, [homeTeam, awayTeam, userIsHome, gameMode, onStartGame]);

  const filteredTeams = filterConference === 'ALL'
    ? teams
    : teams.filter(t => t.conference === filterConference);

  const canStart = homeTeam && awayTeam && homeTeam !== awayTeam && !loading && leagueLoaded;

  const homeTeamInfo = teams.find(t => t.abbreviation === homeTeam);
  const awayTeamInfo = teams.find(t => t.abbreviation === awayTeam);

  // Loading state
  if (teamsLoading) {
    return (
      <div className="game-start-flow">
        <div className="game-start-flow__container">
          <div className="game-start-flow__loading">
            <Loader2 size={32} className="game-start-flow__loading-spinner" />
            <span>Loading teams...</span>
          </div>
        </div>
      </div>
    );
  }

  // No league loaded - show league picker
  if (!leagueLoaded || teamsError) {
    return (
      <div className="game-start-flow">
        <div className="game-start-flow__container">
          <div className="game-start-flow__league-picker">
            <Database size={48} />
            <h2>Load a League</h2>
            <p>Select a saved league or generate a new one to get started.</p>

            {teamsError && (
              <p className="game-start-flow__error-detail">Error: {teamsError}</p>
            )}

            {/* Saved Leagues List */}
            <div className="game-start-flow__leagues">
              <div className="game-start-flow__leagues-header">
                <span>Saved Leagues</span>
                <button
                  className="game-start-flow__refresh-btn"
                  onClick={fetchSavedLeagues}
                  disabled={leaguesLoading}
                  title="Refresh list"
                >
                  <RefreshCw size={14} className={leaguesLoading ? 'spinning' : ''} />
                </button>
              </div>

              {leaguesLoading && savedLeagues.length === 0 ? (
                <div className="game-start-flow__leagues-loading">
                  <Loader2 size={20} className="game-start-flow__loading-spinner" />
                  <span>Loading saved leagues...</span>
                </div>
              ) : savedLeagues.length === 0 ? (
                <div className="game-start-flow__leagues-empty">
                  <span>No saved leagues found</span>
                </div>
              ) : (
                <div className="game-start-flow__leagues-list">
                  {savedLeagues.map(league => (
                    <button
                      key={league.id}
                      className="game-start-flow__league-item"
                      onClick={() => handleLoadLeague(league.id)}
                      disabled={loadingLeagueId !== null || generatingLeague}
                    >
                      <div className="game-start-flow__league-info">
                        <span className="game-start-flow__league-name">{league.name}</span>
                        <span className="game-start-flow__league-season">{league.season} Season</span>
                      </div>
                      <div className="game-start-flow__league-meta">
                        <span className="game-start-flow__league-date">{formatDate(league.created_at)}</span>
                        {loadingLeagueId === league.id && (
                          <Loader2 size={16} className="game-start-flow__loading-spinner" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Generate New League Button */}
            <div className="game-start-flow__generate">
              <button
                className="game-start-flow__generate-btn"
                onClick={handleGenerateLeague}
                disabled={loadingLeagueId !== null || generatingLeague}
              >
                {generatingLeague ? (
                  <>
                    <Loader2 size={18} className="game-start-flow__loading-spinner" />
                    <span>Generating League...</span>
                  </>
                ) : (
                  <>
                    <Plus size={18} />
                    <span>Generate New League</span>
                  </>
                )}
              </button>
              <p className="game-start-flow__generate-hint">
                Creates a new 32-team NFL league with full schedule
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="game-start-flow">
      <div className="game-start-flow__container">
        {/* Header */}
        <div className="game-start-flow__header">
          <h1 className="game-start-flow__title">GAME DAY</h1>
          <p className="game-start-flow__subtitle">Set up your matchup</p>
        </div>

        {/* Matchup Preview */}
        <div className="game-start-flow__matchup">
          <div className={`game-start-flow__team ${gameMode === 'coach' && userIsHome ? 'game-start-flow__team--user' : ''}`}>
            <div className="game-start-flow__team-badge">
              <span className="game-start-flow__team-code">{homeTeam || '???'}</span>
              <Home size={14} />
            </div>
            <span className="game-start-flow__team-name">{homeTeamInfo?.name || 'Select Home'}</span>
            {gameMode === 'coach' && userIsHome && <span className="game-start-flow__user-badge">YOU</span>}
          </div>

          <div className="game-start-flow__vs">VS</div>

          <div className={`game-start-flow__team ${gameMode === 'coach' && !userIsHome ? 'game-start-flow__team--user' : ''}`}>
            <div className="game-start-flow__team-badge">
              <span className="game-start-flow__team-code">{awayTeam || '???'}</span>
              <Plane size={14} />
            </div>
            <span className="game-start-flow__team-name">{awayTeamInfo?.name || 'Select Away'}</span>
            {gameMode === 'coach' && !userIsHome && <span className="game-start-flow__user-badge">YOU</span>}
          </div>
        </div>

        {/* Game Mode Selection */}
        <div className="game-start-flow__mode">
          <span className="game-start-flow__mode-label">GAME MODE</span>
          <div className="game-start-flow__mode-btns">
            <button
              className={`game-start-flow__mode-btn ${gameMode === 'spectator' ? 'active' : ''}`}
              onClick={() => setGameMode('spectator')}
            >
              <Eye size={18} />
              <span>Watch Game</span>
              <small>Auto-play AI vs AI</small>
            </button>
            <button
              className={`game-start-flow__mode-btn ${gameMode === 'coach' ? 'active' : ''}`}
              onClick={() => setGameMode('coach')}
            >
              <Gamepad2 size={18} />
              <span>Coach Mode</span>
              <small>Call plays yourself</small>
            </button>
          </div>
        </div>

        {/* Team Selection */}
        <div className="game-start-flow__selection">
          {/* Conference Filter */}
          <div className="game-start-flow__filter">
            <button
              className={`game-start-flow__filter-btn ${filterConference === 'ALL' ? 'active' : ''}`}
              onClick={() => setFilterConference('ALL')}
            >
              ALL
            </button>
            <button
              className={`game-start-flow__filter-btn ${filterConference === 'AFC' ? 'active' : ''}`}
              onClick={() => setFilterConference('AFC')}
            >
              AFC
            </button>
            <button
              className={`game-start-flow__filter-btn ${filterConference === 'NFC' ? 'active' : ''}`}
              onClick={() => setFilterConference('NFC')}
            >
              NFC
            </button>
          </div>

          {/* Home Team Picker */}
          <div className="game-start-flow__picker">
            <label className="game-start-flow__picker-label">
              <Home size={14} />
              HOME TEAM
            </label>
            <div className="game-start-flow__picker-grid">
              {filteredTeams.map(team => (
                <button
                  key={`home-${team.abbreviation}`}
                  className={`game-start-flow__team-btn ${homeTeam === team.abbreviation ? 'active' : ''} ${awayTeam === team.abbreviation ? 'disabled' : ''}`}
                  onClick={() => setHomeTeam(team.abbreviation)}
                  disabled={awayTeam === team.abbreviation}
                  title={team.name}
                >
                  {team.abbreviation}
                </button>
              ))}
            </div>
          </div>

          {/* Away Team Picker */}
          <div className="game-start-flow__picker">
            <label className="game-start-flow__picker-label">
              <Plane size={14} />
              AWAY TEAM
            </label>
            <div className="game-start-flow__picker-grid">
              {filteredTeams.map(team => (
                <button
                  key={`away-${team.abbreviation}`}
                  className={`game-start-flow__team-btn ${awayTeam === team.abbreviation ? 'active' : ''} ${homeTeam === team.abbreviation ? 'disabled' : ''}`}
                  onClick={() => setAwayTeam(team.abbreviation)}
                  disabled={homeTeam === team.abbreviation}
                  title={team.name}
                >
                  {team.abbreviation}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* User Side Selection (only for coach mode) */}
        {gameMode === 'coach' && (
          <div className="game-start-flow__user-side">
            <span className="game-start-flow__user-side-label">
              <Users size={14} />
              YOU PLAY AS
            </span>
            <div className="game-start-flow__user-side-btns">
              <button
                className={`game-start-flow__side-btn ${userIsHome ? 'active' : ''}`}
                onClick={() => setUserIsHome(true)}
              >
                <Home size={16} />
                <span>{homeTeam || '???'} (HOME)</span>
              </button>
              <button
                className={`game-start-flow__side-btn ${!userIsHome ? 'active' : ''}`}
                onClick={() => setUserIsHome(false)}
              >
                <Plane size={16} />
                <span>{awayTeam || '???'} (AWAY)</span>
              </button>
            </div>
          </div>
        )}

        {/* Start Button */}
        <button
          className="game-start-flow__start"
          onClick={handleStartGame}
          disabled={!canStart}
        >
          {loading ? (
            <span>STARTING...</span>
          ) : (
            <>
              {gameMode === 'spectator' ? <Eye size={20} /> : <Play size={20} />}
              <span>{gameMode === 'spectator' ? 'WATCH GAME' : 'KICK OFF'}</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default GameStartFlow;
