/**
 * AdminScreen - League exploration and admin panel
 *
 * Provides a dashboard for exploring:
 * - League overview and stats
 * - All 32 teams with rosters
 * - Player search and details
 * - Standings by division
 * - Schedule
 * - Free agents and draft class
 */

import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/adminClient';
import type {
  LeagueSummary,
  TeamSummary,
  TeamDetail,
  PlayerSummary,
  PlayerDetail,
  DivisionStandings,
  AdminView,
  WeekResult,
  PlayoffPicture,
  ScheduledGame,
  GameDetail,
  SeasonLeader,
  PlayoffBracket,
  PlayerSeasonStats,
  DraftState,
  DraftPick,
} from '../../types/admin';
import { getOverallColor } from '../../types/admin';
import './AdminScreen.css';

// Position-relevant attributes mapping
const POSITION_ATTRIBUTES: Record<string, string[]> = {
  QB: ['throw_power', 'throw_accuracy_short', 'throw_accuracy_mid', 'throw_accuracy_deep', 'throw_on_run', 'awareness'],
  RB: ['speed', 'acceleration', 'agility', 'carrying', 'break_tackle', 'ball_carrier_vision'],
  FB: ['run_blocking', 'pass_blocking', 'carrying', 'strength', 'awareness', 'impact_blocking'],
  WR: ['speed', 'acceleration', 'catching', 'catch_in_traffic', 'route_running', 'release'],
  TE: ['catching', 'catch_in_traffic', 'run_blocking', 'speed', 'route_running', 'strength'],
  LT: ['pass_blocking', 'run_blocking', 'strength', 'awareness', 'impact_blocking', 'footwork'],
  LG: ['pass_blocking', 'run_blocking', 'strength', 'awareness', 'impact_blocking', 'footwork'],
  C: ['pass_blocking', 'run_blocking', 'strength', 'awareness', 'impact_blocking', 'footwork'],
  RG: ['pass_blocking', 'run_blocking', 'strength', 'awareness', 'impact_blocking', 'footwork'],
  RT: ['pass_blocking', 'run_blocking', 'strength', 'awareness', 'impact_blocking', 'footwork'],
  DE: ['power_moves', 'finesse_moves', 'block_shedding', 'speed', 'strength', 'tackle'],
  DT: ['power_moves', 'block_shedding', 'strength', 'tackle', 'awareness', 'pursuit'],
  NT: ['block_shedding', 'strength', 'tackle', 'awareness', 'power_moves', 'pursuit'],
  MLB: ['tackle', 'pursuit', 'play_recognition', 'zone_coverage', 'block_shedding', 'awareness'],
  ILB: ['tackle', 'pursuit', 'play_recognition', 'zone_coverage', 'block_shedding', 'awareness'],
  OLB: ['speed', 'tackle', 'pursuit', 'finesse_moves', 'zone_coverage', 'man_coverage'],
  CB: ['man_coverage', 'zone_coverage', 'speed', 'acceleration', 'press', 'play_recognition'],
  FS: ['zone_coverage', 'speed', 'pursuit', 'tackle', 'play_recognition', 'catching'],
  SS: ['zone_coverage', 'tackle', 'pursuit', 'man_coverage', 'block_shedding', 'strength'],
  K: ['kick_power', 'kick_accuracy', 'awareness', 'stamina', 'injury', 'toughness'],
  P: ['kick_power', 'kick_accuracy', 'awareness', 'stamina', 'injury', 'toughness'],
  LS: ['awareness', 'strength', 'stamina', 'injury', 'toughness', 'agility'],
};

export const AdminScreen: React.FC = () => {
  // State
  const [league, setLeague] = useState<LeagueSummary | null>(null);
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<TeamDetail | null>(null);
  const [roster, setRoster] = useState<PlayerSummary[]>([]);
  const [selectedPlayer, setSelectedPlayer] = useState<PlayerDetail | null>(null);
  const [standings, setStandings] = useState<DivisionStandings[]>([]);
  const [freeAgents, setFreeAgents] = useState<PlayerSummary[]>([]);
  const [draftClass, setDraftClass] = useState<PlayerSummary[]>([]);
  const [currentView, setCurrentView] = useState<AdminView>('dashboard');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Simulation state
  const [lastSimResults, setLastSimResults] = useState<WeekResult[]>([]);
  const [playoffPicture, setPlayoffPicture] = useState<PlayoffPicture | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);

  // Schedule & Game state
  const [schedule, setSchedule] = useState<ScheduledGame[]>([]);
  const [selectedWeek, setSelectedWeek] = useState<number>(1);
  const [selectedGame, setSelectedGame] = useState<GameDetail | null>(null);

  // Stats state
  const [seasonLeaders, setSeasonLeaders] = useState<{
    passing: SeasonLeader[];
    rushing: SeasonLeader[];
    receiving: SeasonLeader[];
  }>({ passing: [], rushing: [], receiving: [] });

  // Playoff bracket state
  const [_playoffBracket, setPlayoffBracket] = useState<PlayoffBracket | null>(null);

  // Draft state
  const [draftState, setDraftState] = useState<DraftState | null>(null);
  const [draftPicks, setDraftPicks] = useState<DraftPick[]>([]);
  const [draftAvailable, setDraftAvailable] = useState<PlayerSummary[]>([]);
  const [isDrafting, setIsDrafting] = useState(false);
  const [draftPositionFilter, setDraftPositionFilter] = useState<string>('');

  // Team and player stats state
  const [teamStats, setTeamStats] = useState<{
    passing: PlayerSeasonStats[];
    rushing: PlayerSeasonStats[];
    receiving: PlayerSeasonStats[];
    defense: PlayerSeasonStats[];
  } | null>(null);
  const [playerStats, setPlayerStats] = useState<PlayerSeasonStats | null>(null);

  // Filters
  const [conferenceFilter, setConferenceFilter] = useState<string>('');
  const [positionFilter, setPositionFilter] = useState<string>('');

  // UI state
  const [showAllAttributes, setShowAllAttributes] = useState(false);

  // Load league on mount
  useEffect(() => {
    loadLeague();
  }, []);

  const loadLeague = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await adminApi.getLeague();
      setLeague(data);
      await loadTeams();
    } catch (err) {
      // No league exists yet
      setLeague(null);
    } finally {
      setIsLoading(false);
    }
  };

  const generateLeague = async (fantasyDraft: boolean = false) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await adminApi.generateLeague({
        season: 2024,
        include_schedule: true,
        fantasy_draft: fantasyDraft,
      });
      setLeague(data);
      await loadTeams();
      await loadStandings();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate league');
    } finally {
      setIsLoading(false);
    }
  };

  const loadTeams = async () => {
    try {
      const data = await adminApi.listTeams(
        conferenceFilter || undefined,
        undefined
      );
      setTeams(data);
    } catch (err) {
      console.error('Failed to load teams', err);
    }
  };

  const loadTeamDetail = async (abbr: string) => {
    setIsLoading(true);
    try {
      const [team, rosterData] = await Promise.all([
        adminApi.getTeam(abbr),
        adminApi.getTeamRoster(abbr, positionFilter || undefined),
      ]);
      setSelectedTeam(team);
      setRoster(rosterData);
      setTeamStats(null); // Reset team stats
      setCurrentView('team-detail');
    } catch (err) {
      setError('Failed to load team');
    } finally {
      setIsLoading(false);
    }
  };

  const loadTeamStats = async (abbr: string) => {
    try {
      const stats = await adminApi.getTeamStats(abbr);
      setTeamStats(stats);
    } catch (err) {
      console.error('Failed to load team stats', err);
    }
  };

  const loadPlayerDetail = async (playerId: string) => {
    setIsLoading(true);
    setShowAllAttributes(false); // Reset when loading new player
    try {
      const [player, stats] = await Promise.all([
        adminApi.getPlayer(playerId),
        adminApi.getPlayerSeasonStats(playerId).catch(() => null),
      ]);
      setSelectedPlayer(player);
      setPlayerStats(stats);
      setCurrentView('player-detail');
    } catch (err) {
      setError('Failed to load player');
    } finally {
      setIsLoading(false);
    }
  };

  const loadStandings = async () => {
    try {
      const data = await adminApi.getStandings(conferenceFilter || undefined);
      setStandings(data);
    } catch (err) {
      console.error('Failed to load standings', err);
    }
  };

  const loadFreeAgents = async () => {
    setIsLoading(true);
    try {
      const data = await adminApi.getFreeAgents(
        positionFilter || undefined,
        undefined,
        100
      );
      setFreeAgents(data);
      setCurrentView('free-agents');
    } catch (err) {
      setError('Failed to load free agents');
    } finally {
      setIsLoading(false);
    }
  };

  const loadDraftClass = async () => {
    setIsLoading(true);
    try {
      const data = await adminApi.getDraftClass(
        positionFilter || undefined,
        100
      );
      setDraftClass(data);
      setCurrentView('draft-class');
    } catch (err) {
      setError('Failed to load draft class');
    } finally {
      setIsLoading(false);
    }
  };

  // Simulation functions
  const simulateWeek = async () => {
    setIsSimulating(true);
    setError(null);
    try {
      const result = await adminApi.simulateWeek({});
      setLastSimResults([result]);
      // Refresh league and standings
      await loadLeague();
      await loadStandings();
      await loadPlayoffPicture();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to simulate week');
    } finally {
      setIsSimulating(false);
    }
  };

  const simulateToWeek = async (targetWeek: number) => {
    setIsSimulating(true);
    setError(null);
    try {
      const results = await adminApi.simulateToWeek({ target_week: targetWeek });
      setLastSimResults(results);
      await loadLeague();
      await loadStandings();
      await loadPlayoffPicture();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to simulate');
    } finally {
      setIsSimulating(false);
    }
  };

  const simulateSeason = async () => {
    setIsSimulating(true);
    setError(null);
    try {
      const results = await adminApi.simulateSeason();
      setLastSimResults(results);
      await loadLeague();
      await loadStandings();
      await loadPlayoffPicture();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to simulate season');
    } finally {
      setIsSimulating(false);
    }
  };

  const loadPlayoffPicture = async () => {
    try {
      const data = await adminApi.getPlayoffPicture();
      setPlayoffPicture(data);
    } catch (err) {
      console.error('Failed to load playoff picture', err);
    }
  };

  const loadSchedule = async (week?: number) => {
    setIsLoading(true);
    try {
      const data = await adminApi.getSchedule(week);
      setSchedule(data);
      setCurrentView('schedule');
    } catch (err) {
      setError('Failed to load schedule');
    } finally {
      setIsLoading(false);
    }
  };

  const loadGameDetail = async (gameId: string) => {
    setIsLoading(true);
    try {
      const data = await adminApi.getGameDetail(gameId);
      setSelectedGame(data);
      setCurrentView('game-detail');
    } catch (err) {
      setError('Game details not available (game may not be played yet)');
    } finally {
      setIsLoading(false);
    }
  };

  const loadSeasonLeaders = async () => {
    setIsLoading(true);
    try {
      const [passing, rushing, receiving] = await Promise.all([
        adminApi.getSeasonLeaders('passing', 'yards', 10),
        adminApi.getSeasonLeaders('rushing', 'yards', 10),
        adminApi.getSeasonLeaders('receiving', 'yards', 10),
      ]);
      setSeasonLeaders({ passing, rushing, receiving });
      setCurrentView('stats');
    } catch (err) {
      setError('Failed to load season leaders');
    } finally {
      setIsLoading(false);
    }
  };

  const loadPlayoffBracket = async () => {
    try {
      const data = await adminApi.getPlayoffBracket();
      setPlayoffBracket(data);
    } catch (err) {
      console.error('Failed to load playoff bracket', err);
    }
  };

  const simulatePlayoffs = async () => {
    setIsSimulating(true);
    setError(null);
    try {
      await adminApi.simulatePlayoffs();
      await loadLeague();
      await loadPlayoffBracket();
      await loadPlayoffPicture();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to simulate playoffs');
    } finally {
      setIsSimulating(false);
    }
  };

  // Draft functions
  const loadDraftView = async () => {
    setIsLoading(true);
    try {
      const state = await adminApi.getDraftState();
      setDraftState(state);
      if (state.phase === 'in_progress') {
        await loadDraftData();
      }
    } catch {
      // No draft exists yet - that's OK
      setDraftState(null);
    }
    setCurrentView('draft');
    setIsLoading(false);
  };

  const loadDraftData = async () => {
    try {
      const [picks, available] = await Promise.all([
        adminApi.getDraftPicks(),
        adminApi.getAvailablePlayers(draftPositionFilter || undefined, 100),
      ]);
      setDraftPicks(picks);
      setDraftAvailable(available);
    } catch (err) {
      console.error('Failed to load draft data', err);
    }
  };

  const createDraft = async (draftType: 'nfl' | 'fantasy') => {
    setIsDrafting(true);
    setError(null);
    try {
      const numRounds = draftType === 'fantasy' ? 15 : 7;
      const state = await adminApi.createDraft({
        draft_type: draftType,
        num_rounds: numRounds,
      });
      setDraftState(state);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create draft');
    } finally {
      setIsDrafting(false);
    }
  };

  const startDraft = async () => {
    setIsDrafting(true);
    setError(null);
    try {
      const state = await adminApi.startDraft();
      setDraftState(state);
      await loadDraftData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start draft');
    } finally {
      setIsDrafting(false);
    }
  };

  const simulateFullDraft = async () => {
    setIsDrafting(true);
    setError(null);
    try {
      const result = await adminApi.simulateFullDraft();
      setDraftPicks(result.picks_made);
      // Refresh state
      const state = await adminApi.getDraftState();
      setDraftState(state);
      await loadLeague(); // Refresh league to see roster changes
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to simulate draft');
    } finally {
      setIsDrafting(false);
    }
  };

  const makeDraftPick = async (playerId: string) => {
    setIsDrafting(true);
    try {
      await adminApi.makePick(playerId);
      // Refresh draft state and data
      const state = await adminApi.getDraftState();
      setDraftState(state);
      await loadDraftData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to make pick');
    } finally {
      setIsDrafting(false);
    }
  };

  // Navigation
  const goBack = () => {
    if (currentView === 'player-detail') {
      setSelectedPlayer(null);
      setCurrentView(selectedTeam ? 'team-detail' : 'teams');
    } else if (currentView === 'team-detail') {
      setSelectedTeam(null);
      setRoster([]);
      setCurrentView('teams');
    } else if (currentView === 'game-detail') {
      setSelectedGame(null);
      setCurrentView('schedule');
    } else if (currentView === 'draft') {
      setDraftState(null);
      setDraftPicks([]);
      setDraftAvailable([]);
      setCurrentView('dashboard');
    } else {
      setCurrentView('dashboard');
    }
  };

  // Render loading state
  if (isLoading && !league) {
    return (
      <div className="admin-screen admin-screen--loading">
        <div className="admin-loader">Loading...</div>
      </div>
    );
  }

  // Render no league state
  if (!league) {
    return (
      <div className="admin-screen admin-screen--empty">
        <div className="admin-empty">
          <h2>No League Loaded</h2>
          <p>Generate a new 32-team NFL league to get started.</p>
          <div className="admin-empty__options">
            <div className="admin-empty__option">
              <h3>Standard League</h3>
              <p>Pre-generated rosters with realistic team compositions.</p>
              <button
                className="admin-btn admin-btn--primary"
                onClick={() => generateLeague(false)}
                disabled={isLoading}
              >
                {isLoading ? 'Generating...' : 'Generate League'}
              </button>
            </div>
            <div className="admin-empty__option">
              <h3>Fantasy Draft League</h3>
              <p>Start fresh with a 53-round fantasy draft to build all rosters from scratch.</p>
              <button
                className="admin-btn admin-btn--secondary"
                onClick={() => generateLeague(true)}
                disabled={isLoading}
              >
                {isLoading ? 'Drafting...' : 'Fantasy Draft League'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-screen">
      {/* Sidebar Navigation */}
      <aside className="admin-sidebar">
        <div className="admin-sidebar__header">
          <h1>League Admin</h1>
          <span className="admin-sidebar__season">{league.current_season}</span>
        </div>

        <nav className="admin-nav">
          <button
            className={`admin-nav__item ${currentView === 'dashboard' ? 'active' : ''}`}
            onClick={() => setCurrentView('dashboard')}
          >
            Dashboard
          </button>
          <button
            className={`admin-nav__item ${currentView === 'teams' || currentView === 'team-detail' ? 'active' : ''}`}
            onClick={() => { setCurrentView('teams'); loadTeams(); }}
          >
            Teams ({league.team_count})
          </button>
          <button
            className={`admin-nav__item ${currentView === 'standings' ? 'active' : ''}`}
            onClick={() => { setCurrentView('standings'); loadStandings(); }}
          >
            Standings
          </button>
          <button
            className={`admin-nav__item ${currentView === 'schedule' || currentView === 'game-detail' ? 'active' : ''}`}
            onClick={() => loadSchedule()}
          >
            Schedule
          </button>
          <button
            className={`admin-nav__item ${currentView === 'stats' ? 'active' : ''}`}
            onClick={loadSeasonLeaders}
          >
            Stats
          </button>
          <button
            className={`admin-nav__item ${currentView === 'free-agents' ? 'active' : ''}`}
            onClick={loadFreeAgents}
          >
            Free Agents ({league.free_agent_count})
          </button>
          <button
            className={`admin-nav__item ${currentView === 'draft-class' ? 'active' : ''}`}
            onClick={loadDraftClass}
          >
            Draft Class ({league.draft_class_size})
          </button>
          <button
            className={`admin-nav__item ${currentView === 'draft' ? 'active' : ''}`}
            onClick={loadDraftView}
          >
            Draft
          </button>
          <button
            className={`admin-nav__item ${currentView === 'simulate' ? 'active' : ''}`}
            onClick={() => { setCurrentView('simulate'); loadPlayoffPicture(); }}
          >
            Simulate
          </button>
        </nav>

        <div className="admin-sidebar__footer">
          <button
            className="admin-btn admin-btn--secondary"
            onClick={() => generateLeague(false)}
            disabled={isLoading}
          >
            Regenerate
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="admin-main">
        {/* Breadcrumb */}
        {currentView !== 'dashboard' && (
          <div className="admin-breadcrumb">
            <button onClick={goBack}>&larr; Back</button>
            <span>{currentView.replace('-', ' ').toUpperCase()}</span>
          </div>
        )}

        {/* Error display */}
        {error && (
          <div className="admin-error">
            {error}
            <button onClick={() => setError(null)}>Dismiss</button>
          </div>
        )}

        {/* Loading overlay */}
        {isLoading && (
          <div className="admin-loading-overlay">Loading...</div>
        )}

        {/* Dashboard View */}
        {currentView === 'dashboard' && (
          <div className="admin-dashboard">
            <h2>League Overview</h2>
            <div className="admin-stats-grid">
              <div className="admin-stat-card">
                <div className="admin-stat-card__value">{league.team_count}</div>
                <div className="admin-stat-card__label">Teams</div>
              </div>
              <div className="admin-stat-card">
                <div className="admin-stat-card__value">{league.total_players}</div>
                <div className="admin-stat-card__label">Players</div>
              </div>
              <div className="admin-stat-card">
                <div className="admin-stat-card__value">{league.free_agent_count}</div>
                <div className="admin-stat-card__label">Free Agents</div>
              </div>
              <div className="admin-stat-card">
                <div className="admin-stat-card__value">{league.draft_class_size}</div>
                <div className="admin-stat-card__label">Draft Prospects</div>
              </div>
              <div className="admin-stat-card">
                <div className="admin-stat-card__value">Week {league.current_week}</div>
                <div className="admin-stat-card__label">
                  {league.is_offseason ? 'Offseason' : league.is_playoffs ? 'Playoffs' : 'Regular Season'}
                </div>
              </div>
            </div>

            {/* Quick team list */}
            <h3>Teams by Conference</h3>
            <div className="admin-conference-grid">
              {['AFC', 'NFC'].map(conf => (
                <div key={conf} className="admin-conference-column">
                  <h4>{conf}</h4>
                  {teams
                    .filter(t => t.conference === conf)
                    .map(team => (
                      <div
                        key={team.abbreviation}
                        className="admin-team-row"
                        onClick={() => loadTeamDetail(team.abbreviation)}
                      >
                        <span
                          className="admin-team-row__color"
                          style={{ backgroundColor: team.primary_color }}
                        />
                        <span className="admin-team-row__abbr">{team.abbreviation}</span>
                        <span className="admin-team-row__name">{team.name}</span>
                        <span className="admin-team-row__ratings">
                          OFF: {team.offense_rating} | DEF: {team.defense_rating}
                        </span>
                      </div>
                    ))}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Teams List View */}
        {currentView === 'teams' && (
          <div className="admin-teams">
            <h2>All Teams</h2>
            <div className="admin-filters">
              <select
                value={conferenceFilter}
                onChange={(e) => { setConferenceFilter(e.target.value); loadTeams(); }}
              >
                <option value="">All Conferences</option>
                <option value="AFC">AFC</option>
                <option value="NFC">NFC</option>
              </select>
            </div>
            <div className="admin-teams-grid">
              {teams.map(team => (
                <div
                  key={team.abbreviation}
                  className="admin-team-card"
                  onClick={() => loadTeamDetail(team.abbreviation)}
                  style={{ borderColor: team.primary_color }}
                >
                  <div
                    className="admin-team-card__header"
                    style={{ backgroundColor: team.primary_color }}
                  >
                    <span className="admin-team-card__abbr">{team.abbreviation}</span>
                  </div>
                  <div className="admin-team-card__body">
                    <div className="admin-team-card__name">{team.full_name}</div>
                    <div className="admin-team-card__division">{team.division}</div>
                    <div className="admin-team-card__ratings">
                      <span>OFF: {team.offense_rating}</span>
                      <span>DEF: {team.defense_rating}</span>
                    </div>
                    <div className="admin-team-card__roster">
                      {team.roster_size} players
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Team Detail View */}
        {currentView === 'team-detail' && selectedTeam && (
          <div className="admin-team-detail">
            <div
              className="admin-team-detail__header"
              style={{ backgroundColor: selectedTeam.primary_color }}
            >
              <h2>{selectedTeam.full_name}</h2>
              <div className="admin-team-detail__meta">
                <span>{selectedTeam.division}</span>
                <span>|</span>
                <span>OFF: {selectedTeam.offense_rating}</span>
                <span>DEF: {selectedTeam.defense_rating}</span>
              </div>
              {selectedTeam.qb_name && (
                <div className="admin-team-detail__qb">
                  QB: {selectedTeam.qb_name} ({selectedTeam.qb_overall} OVR)
                </div>
              )}
            </div>

            {/* Team Tabs */}
            <div className="admin-team-tabs">
              <button
                className={`admin-team-tab ${!teamStats ? 'active' : ''}`}
                onClick={() => setTeamStats(null)}
              >
                Roster
              </button>
              <button
                className={`admin-team-tab ${teamStats ? 'active' : ''}`}
                onClick={() => loadTeamStats(selectedTeam.abbreviation)}
              >
                Season Stats
              </button>
            </div>

            {/* Roster Tab */}
            {!teamStats && (
              <div className="admin-roster">
                <div className="admin-roster__header">
                  <h3>Roster ({roster.length})</h3>
                  <select
                    value={positionFilter}
                    onChange={(e) => {
                      setPositionFilter(e.target.value);
                      adminApi.getTeamRoster(selectedTeam.abbreviation, e.target.value || undefined)
                        .then(setRoster);
                    }}
                  >
                    <option value="">All Positions</option>
                    <option value="QB">QB</option>
                    <option value="RB">RB</option>
                    <option value="WR">WR</option>
                    <option value="TE">TE</option>
                    <option value="LT">LT</option>
                    <option value="LG">LG</option>
                    <option value="C">C</option>
                    <option value="RG">RG</option>
                    <option value="RT">RT</option>
                    <option value="DE">DE</option>
                    <option value="DT">DT</option>
                    <option value="MLB">MLB</option>
                    <option value="OLB">OLB</option>
                    <option value="CB">CB</option>
                    <option value="FS">FS</option>
                    <option value="SS">SS</option>
                    <option value="K">K</option>
                    <option value="P">P</option>
                  </select>
                </div>

                <table className="admin-roster__table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Name</th>
                      <th>Pos</th>
                      <th>OVR</th>
                      <th>POT</th>
                      <th>Age</th>
                      <th>Exp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {roster.map(player => (
                      <tr
                        key={player.id}
                        onClick={() => loadPlayerDetail(player.id)}
                        className="admin-roster__row"
                      >
                        <td>{player.jersey_number}</td>
                        <td>{player.full_name}</td>
                        <td>{player.position}</td>
                        <td style={{ color: getOverallColor(player.overall) }}>
                          {player.overall}
                        </td>
                        <td style={{ color: getOverallColor(player.potential) }}>
                          {player.potential}
                        </td>
                        <td>{player.age}</td>
                        <td>{player.experience}yr</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Stats Tab */}
            {teamStats && (
              <div className="admin-team-stats">
                {/* Passing */}
                {teamStats.passing.length > 0 && (
                  <div className="admin-team-stats__section">
                    <h3>Passing</h3>
                    <table>
                      <thead>
                        <tr>
                          <th>Player</th>
                          <th>GP</th>
                          <th>CMP</th>
                          <th>ATT</th>
                          <th>YDS</th>
                          <th>TD</th>
                          <th>INT</th>
                          <th>RTG</th>
                        </tr>
                      </thead>
                      <tbody>
                        {teamStats.passing.map(p => (
                          <tr key={p.player_id} onClick={() => loadPlayerDetail(p.player_id)}>
                            <td>{p.player_name}</td>
                            <td>{p.games_played}</td>
                            <td>{p.passing?.completions || 0}</td>
                            <td>{p.passing?.attempts || 0}</td>
                            <td>{p.passing?.yards?.toLocaleString() || 0}</td>
                            <td>{p.passing?.touchdowns || 0}</td>
                            <td>{p.passing?.interceptions || 0}</td>
                            <td>{p.passing?.passer_rating?.toFixed(1) || 0}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Rushing */}
                {teamStats.rushing.length > 0 && (
                  <div className="admin-team-stats__section">
                    <h3>Rushing</h3>
                    <table>
                      <thead>
                        <tr>
                          <th>Player</th>
                          <th>GP</th>
                          <th>ATT</th>
                          <th>YDS</th>
                          <th>TD</th>
                          <th>Y/A</th>
                          <th>LNG</th>
                        </tr>
                      </thead>
                      <tbody>
                        {teamStats.rushing.map(p => (
                          <tr key={p.player_id} onClick={() => loadPlayerDetail(p.player_id)}>
                            <td>{p.player_name}</td>
                            <td>{p.games_played}</td>
                            <td>{p.rushing?.attempts || 0}</td>
                            <td>{p.rushing?.yards?.toLocaleString() || 0}</td>
                            <td>{p.rushing?.touchdowns || 0}</td>
                            <td>{p.rushing?.yards_per_carry?.toFixed(1) || 0}</td>
                            <td>{p.rushing?.longest || 0}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Receiving */}
                {teamStats.receiving.length > 0 && (
                  <div className="admin-team-stats__section">
                    <h3>Receiving</h3>
                    <table>
                      <thead>
                        <tr>
                          <th>Player</th>
                          <th>GP</th>
                          <th>REC</th>
                          <th>TGT</th>
                          <th>YDS</th>
                          <th>TD</th>
                          <th>Y/R</th>
                        </tr>
                      </thead>
                      <tbody>
                        {teamStats.receiving.map(p => (
                          <tr key={p.player_id} onClick={() => loadPlayerDetail(p.player_id)}>
                            <td>{p.player_name}</td>
                            <td>{p.games_played}</td>
                            <td>{p.receiving?.receptions || 0}</td>
                            <td>{p.receiving?.targets || 0}</td>
                            <td>{p.receiving?.yards?.toLocaleString() || 0}</td>
                            <td>{p.receiving?.touchdowns || 0}</td>
                            <td>{p.receiving?.yards_per_reception?.toFixed(1) || 0}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Defense */}
                {teamStats.defense.length > 0 && (
                  <div className="admin-team-stats__section">
                    <h3>Defense</h3>
                    <table>
                      <thead>
                        <tr>
                          <th>Player</th>
                          <th>GP</th>
                          <th>TKL</th>
                          <th>SCK</th>
                          <th>INT</th>
                          <th>PD</th>
                          <th>FF</th>
                        </tr>
                      </thead>
                      <tbody>
                        {teamStats.defense.map(p => (
                          <tr key={p.player_id} onClick={() => loadPlayerDetail(p.player_id)}>
                            <td>{p.player_name}</td>
                            <td>{p.games_played}</td>
                            <td>{p.defense?.tackles || 0}</td>
                            <td>{p.defense?.sacks || 0}</td>
                            <td>{p.defense?.interceptions || 0}</td>
                            <td>{p.defense?.passes_defended || 0}</td>
                            <td>{p.defense?.forced_fumbles || 0}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {teamStats.passing.length === 0 && teamStats.rushing.length === 0 &&
                 teamStats.receiving.length === 0 && teamStats.defense.length === 0 && (
                  <div className="admin-no-stats">
                    No stats available. Simulate some games first!
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Player Detail View */}
        {currentView === 'player-detail' && selectedPlayer && (
          <div className="admin-player-detail">
            <div className="admin-player-detail__header">
              <div className="admin-player-detail__jersey">
                #{selectedPlayer.jersey_number}
              </div>
              <div className="admin-player-detail__info">
                <h2>{selectedPlayer.full_name}</h2>
                <div className="admin-player-detail__meta">
                  <span>{selectedPlayer.position}</span>
                  <span>|</span>
                  <span>{selectedPlayer.height}, {selectedPlayer.weight} lbs</span>
                  <span>|</span>
                  <span>Age: {selectedPlayer.age}</span>
                  {selectedPlayer.team_abbr && (
                    <>
                      <span>|</span>
                      <span>{selectedPlayer.team_abbr}</span>
                    </>
                  )}
                </div>
              </div>
              <div className="admin-player-detail__ratings">
                <div className="admin-player-detail__overall">
                  <span style={{ color: getOverallColor(selectedPlayer.overall) }}>
                    {selectedPlayer.overall}
                  </span>
                  <label>OVR</label>
                </div>
                <div className="admin-player-detail__potential">
                  <span style={{ color: getOverallColor(selectedPlayer.potential) }}>
                    {selectedPlayer.potential}
                  </span>
                  <label>POT</label>
                </div>
              </div>
            </div>

            <div className="admin-player-detail__body">
              {/* Background + Attributes Row */}
              <div className="admin-player-detail__info-row">
                <div className="admin-player-detail__background">
                  <h3>Background</h3>
                  <div className="admin-player-detail__fields">
                    <div><label>College:</label> {selectedPlayer.college || 'N/A'}</div>
                    <div><label>Experience:</label> {selectedPlayer.experience} years</div>
                    <div><label>Years on Team:</label> {selectedPlayer.years_on_team}</div>
                    {selectedPlayer.draft_year && (
                      <div>
                        <label>Draft:</label> {selectedPlayer.draft_year} Round {selectedPlayer.draft_round}, Pick {selectedPlayer.draft_pick}
                      </div>
                    )}
                    <div><label>Status:</label> {selectedPlayer.is_rookie ? 'Rookie' : selectedPlayer.is_veteran ? 'Veteran' : 'Developing'}</div>
                  </div>
                </div>

                <div className="admin-player-detail__attributes">
                  <h3>Key Attributes</h3>
                  {(() => {
                    const positionAttrs = POSITION_ATTRIBUTES[selectedPlayer.position] || [];
                    const allAttrs = Object.entries(selectedPlayer.attributes);
                    const keyAttrs = positionAttrs
                      .map(key => [key, selectedPlayer.attributes[key]] as [string, number])
                      .filter(([, val]) => val !== undefined);
                    const otherAttrs = allAttrs
                      .filter(([key]) => !positionAttrs.includes(key))
                      .sort(([, a], [, b]) => (b as number) - (a as number));

                    return (
                      <>
                        <div className="admin-attributes-grid">
                          {keyAttrs.map(([key, value]) => (
                            <div key={key} className="admin-attribute-box">
                              <div
                                className="admin-attribute-box__value"
                                style={{ color: getOverallColor(value) }}
                              >
                                {value}
                              </div>
                              <div className="admin-attribute-box__label">
                                {key.replace(/_/g, ' ')}
                              </div>
                            </div>
                          ))}
                          {showAllAttributes && otherAttrs.map(([key, value]) => (
                            <div key={key} className="admin-attribute-box admin-attribute-box--secondary">
                              <div
                                className="admin-attribute-box__value"
                                style={{ color: getOverallColor(value as number) }}
                              >
                                {value}
                              </div>
                              <div className="admin-attribute-box__label">
                                {key.replace(/_/g, ' ')}
                              </div>
                            </div>
                          ))}
                        </div>
                        {otherAttrs.length > 0 && (
                          <button
                            className="admin-btn admin-btn--text"
                            onClick={() => setShowAllAttributes(!showAllAttributes)}
                          >
                            {showAllAttributes ? 'Show Less' : `+${otherAttrs.length} More`}
                          </button>
                        )}
                      </>
                    );
                  })()}
                </div>
              </div>

              {/* Season Stats */}
              {playerStats && playerStats.games_played > 0 && (
                <div className="admin-player-detail__section admin-player-stats">
                  <h3>Season Stats ({playerStats.games_played} Games)</h3>

                  {/* Passing Stats */}
                  {playerStats.passing && playerStats.passing.attempts > 0 && (
                    <div className="admin-player-stats__category">
                      <h4>Passing</h4>
                      <div className="admin-player-stats__grid">
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.passing.completions}/{playerStats.passing.attempts}</div>
                          <div className="admin-player-stat__label">CMP/ATT</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.passing.yards.toLocaleString()}</div>
                          <div className="admin-player-stat__label">YDS</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.passing.touchdowns}</div>
                          <div className="admin-player-stat__label">TD</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.passing.interceptions}</div>
                          <div className="admin-player-stat__label">INT</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.passing.completion_pct.toFixed(1)}%</div>
                          <div className="admin-player-stat__label">CMP%</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.passing.passer_rating.toFixed(1)}</div>
                          <div className="admin-player-stat__label">RTG</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Rushing Stats */}
                  {playerStats.rushing && playerStats.rushing.attempts > 0 && (
                    <div className="admin-player-stats__category">
                      <h4>Rushing</h4>
                      <div className="admin-player-stats__grid">
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.rushing.attempts}</div>
                          <div className="admin-player-stat__label">ATT</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.rushing.yards.toLocaleString()}</div>
                          <div className="admin-player-stat__label">YDS</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.rushing.touchdowns}</div>
                          <div className="admin-player-stat__label">TD</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.rushing.yards_per_carry.toFixed(1)}</div>
                          <div className="admin-player-stat__label">Y/A</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.rushing.longest}</div>
                          <div className="admin-player-stat__label">LNG</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.rushing.fumbles_lost}</div>
                          <div className="admin-player-stat__label">FUM</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Receiving Stats */}
                  {playerStats.receiving && playerStats.receiving.receptions > 0 && (
                    <div className="admin-player-stats__category">
                      <h4>Receiving</h4>
                      <div className="admin-player-stats__grid">
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.receiving.receptions}</div>
                          <div className="admin-player-stat__label">REC</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.receiving.targets}</div>
                          <div className="admin-player-stat__label">TGT</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.receiving.yards.toLocaleString()}</div>
                          <div className="admin-player-stat__label">YDS</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.receiving.touchdowns}</div>
                          <div className="admin-player-stat__label">TD</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.receiving.yards_per_reception.toFixed(1)}</div>
                          <div className="admin-player-stat__label">Y/R</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.receiving.catch_pct.toFixed(1)}%</div>
                          <div className="admin-player-stat__label">CATCH%</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Defense Stats */}
                  {playerStats.defense && (playerStats.defense.tackles > 0 || playerStats.defense.sacks > 0 || playerStats.defense.interceptions > 0) && (
                    <div className="admin-player-stats__category">
                      <h4>Defense</h4>
                      <div className="admin-player-stats__grid">
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.defense.tackles}</div>
                          <div className="admin-player-stat__label">TKL</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.defense.sacks}</div>
                          <div className="admin-player-stat__label">SCK</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.defense.interceptions}</div>
                          <div className="admin-player-stat__label">INT</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.defense.passes_defended}</div>
                          <div className="admin-player-stat__label">PD</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.defense.forced_fumbles}</div>
                          <div className="admin-player-stat__label">FF</div>
                        </div>
                        <div className="admin-player-stat">
                          <div className="admin-player-stat__value">{playerStats.defense.fumble_recoveries}</div>
                          <div className="admin-player-stat__label">FR</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Standings View */}
        {currentView === 'standings' && (
          <div className="admin-standings">
            <h2>League Standings</h2>
            <div className="admin-filters">
              <select
                value={conferenceFilter}
                onChange={(e) => { setConferenceFilter(e.target.value); loadStandings(); }}
              >
                <option value="">All Conferences</option>
                <option value="AFC">AFC</option>
                <option value="NFC">NFC</option>
              </select>
            </div>
            <div className="admin-standings-grid">
              {standings.map(div => (
                <div key={div.division} className="admin-division-standings">
                  <h3>{div.division}</h3>
                  <table>
                    <thead>
                      <tr>
                        <th>Team</th>
                        <th>W</th>
                        <th>L</th>
                        <th>T</th>
                        <th>PCT</th>
                        <th>PF</th>
                        <th>PA</th>
                        <th>DIFF</th>
                      </tr>
                    </thead>
                    <tbody>
                      {div.teams.map(team => (
                        <tr
                          key={team.abbreviation}
                          onClick={() => loadTeamDetail(team.abbreviation)}
                          className="admin-standings__row"
                        >
                          <td>
                            <strong>{team.abbreviation}</strong>
                          </td>
                          <td>{team.wins}</td>
                          <td>{team.losses}</td>
                          <td>{team.ties}</td>
                          <td>{team.win_pct.toFixed(3)}</td>
                          <td>{team.points_for}</td>
                          <td>{team.points_against}</td>
                          <td className={team.point_diff >= 0 ? 'positive' : 'negative'}>
                            {team.point_diff >= 0 ? '+' : ''}{team.point_diff}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Free Agents View */}
        {currentView === 'free-agents' && (
          <div className="admin-free-agents">
            <h2>Free Agents</h2>
            <div className="admin-filters">
              <select
                value={positionFilter}
                onChange={(e) => {
                  setPositionFilter(e.target.value);
                  adminApi.getFreeAgents(e.target.value || undefined, undefined, 100)
                    .then(setFreeAgents);
                }}
              >
                <option value="">All Positions</option>
                <option value="QB">QB</option>
                <option value="RB">RB</option>
                <option value="WR">WR</option>
                <option value="TE">TE</option>
                <option value="DE">DE</option>
                <option value="CB">CB</option>
              </select>
            </div>
            <table className="admin-players-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Pos</th>
                  <th>OVR</th>
                  <th>POT</th>
                  <th>Age</th>
                  <th>Exp</th>
                </tr>
              </thead>
              <tbody>
                {freeAgents.map(player => (
                  <tr
                    key={player.id}
                    onClick={() => loadPlayerDetail(player.id)}
                    className="admin-players-table__row"
                  >
                    <td>{player.full_name}</td>
                    <td>{player.position}</td>
                    <td style={{ color: getOverallColor(player.overall) }}>
                      {player.overall}
                    </td>
                    <td style={{ color: getOverallColor(player.potential) }}>
                      {player.potential}
                    </td>
                    <td>{player.age}</td>
                    <td>{player.experience}yr</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Draft Class View */}
        {currentView === 'draft-class' && (
          <div className="admin-draft-class">
            <h2>Draft Class {league.current_season + 1}</h2>
            <div className="admin-filters">
              <select
                value={positionFilter}
                onChange={(e) => {
                  setPositionFilter(e.target.value);
                  adminApi.getDraftClass(e.target.value || undefined, 100)
                    .then(setDraftClass);
                }}
              >
                <option value="">All Positions</option>
                <option value="QB">QB</option>
                <option value="RB">RB</option>
                <option value="WR">WR</option>
                <option value="TE">TE</option>
                <option value="DE">DE</option>
                <option value="CB">CB</option>
              </select>
            </div>
            <table className="admin-players-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Name</th>
                  <th>Pos</th>
                  <th>OVR</th>
                  <th>POT</th>
                  <th>Age</th>
                </tr>
              </thead>
              <tbody>
                {draftClass.map((player, idx) => (
                  <tr
                    key={player.id}
                    onClick={() => loadPlayerDetail(player.id)}
                    className="admin-players-table__row"
                  >
                    <td>{idx + 1}</td>
                    <td>{player.full_name}</td>
                    <td>{player.position}</td>
                    <td style={{ color: getOverallColor(player.overall) }}>
                      {player.overall}
                    </td>
                    <td style={{ color: getOverallColor(player.potential) }}>
                      {player.potential}
                    </td>
                    <td>{player.age}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Schedule View */}
        {currentView === 'schedule' && (
          <div className="admin-schedule">
            <h2>Season Schedule</h2>
            <div className="admin-filters">
              <select
                value={selectedWeek}
                onChange={(e) => {
                  const week = parseInt(e.target.value);
                  setSelectedWeek(week);
                  loadSchedule(week || undefined);
                }}
              >
                <option value={0}>All Weeks</option>
                {Array.from({ length: 22 }, (_, i) => i + 1).map(w => (
                  <option key={w} value={w}>
                    {w <= 18 ? `Week ${w}` : w === 19 ? 'Wild Card' : w === 20 ? 'Divisional' : w === 21 ? 'Conf. Championship' : 'Super Bowl'}
                  </option>
                ))}
              </select>
            </div>
            <div className="admin-schedule-grid">
              {schedule.map(game => (
                <div
                  key={game.id}
                  className={`admin-schedule-game ${game.is_played ? 'played' : 'upcoming'}`}
                  onClick={() => game.is_played && loadGameDetail(game.id)}
                  style={{ cursor: game.is_played ? 'pointer' : 'default' }}
                >
                  <div className="admin-schedule-game__week">
                    {game.week <= 18 ? `Week ${game.week}` : game.week === 19 ? 'Wild Card' : game.week === 20 ? 'Divisional' : game.week === 21 ? 'Conf. Champ' : 'Super Bowl'}
                  </div>
                  <div className="admin-schedule-game__matchup">
                    <span className={game.winner === game.away_team ? 'winner' : ''}>
                      {game.away_team} {game.is_played && game.away_score}
                    </span>
                    <span className="admin-schedule-game__at">@</span>
                    <span className={game.winner === game.home_team ? 'winner' : ''}>
                      {game.home_team} {game.is_played && game.home_score}
                    </span>
                  </div>
                  <div className="admin-schedule-game__type">
                    {game.is_divisional && <span className="tag">DIV</span>}
                    {game.is_conference && !game.is_divisional && <span className="tag">CONF</span>}
                    {!game.is_played && <span className="tag upcoming">Upcoming</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Game Detail View */}
        {currentView === 'game-detail' && selectedGame && (
          <div className="admin-game-detail">
            <div className="admin-game-detail__header">
              <h2>
                {selectedGame.away_team} {selectedGame.away_score} @ {selectedGame.home_team} {selectedGame.home_score}
                {selectedGame.is_overtime && <span className="ot-tag">OT</span>}
              </h2>
              <div className="admin-game-detail__meta">
                Week {selectedGame.week} {selectedGame.is_playoff && '(Playoff)'}
              </div>
            </div>

            <div className="admin-game-detail__stats">
              <h3>Team Stats</h3>
              <table className="admin-game-stats-table">
                <thead>
                  <tr>
                    <th>{selectedGame.away_team}</th>
                    <th>Stat</th>
                    <th>{selectedGame.home_team}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>{selectedGame.away_stats.total_yards}</td>
                    <td>Total Yards</td>
                    <td>{selectedGame.home_stats.total_yards}</td>
                  </tr>
                  <tr>
                    <td>{selectedGame.away_stats.passing_yards}</td>
                    <td>Passing Yards</td>
                    <td>{selectedGame.home_stats.passing_yards}</td>
                  </tr>
                  <tr>
                    <td>{selectedGame.away_stats.rushing_yards}</td>
                    <td>Rushing Yards</td>
                    <td>{selectedGame.home_stats.rushing_yards}</td>
                  </tr>
                  <tr>
                    <td>{selectedGame.away_stats.first_downs}</td>
                    <td>First Downs</td>
                    <td>{selectedGame.home_stats.first_downs}</td>
                  </tr>
                  <tr>
                    <td>{selectedGame.away_stats.turnovers}</td>
                    <td>Turnovers</td>
                    <td>{selectedGame.home_stats.turnovers}</td>
                  </tr>
                  <tr>
                    <td>{selectedGame.away_stats.penalties} ({selectedGame.away_stats.penalty_yards} yds)</td>
                    <td>Penalties</td>
                    <td>{selectedGame.home_stats.penalties} ({selectedGame.home_stats.penalty_yards} yds)</td>
                  </tr>
                  <tr>
                    <td>{selectedGame.away_stats.time_of_possession}</td>
                    <td>Time of Possession</td>
                    <td>{selectedGame.home_stats.time_of_possession}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {selectedGame.scoring_plays.length > 0 && (
              <div className="admin-game-detail__scoring">
                <h3>Scoring Summary</h3>
                <div className="admin-scoring-plays">
                  {selectedGame.scoring_plays.map((play, idx) => (
                    <div key={idx} className="admin-scoring-play">
                      <div className="admin-scoring-play__quarter">Q{play.quarter}</div>
                      <div className="admin-scoring-play__info">
                        <div className="admin-scoring-play__desc">{play.description}</div>
                        <div className="admin-scoring-play__score">
                          {selectedGame.away_team} {play.away_score} - {selectedGame.home_team} {play.home_score}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Stats View */}
        {currentView === 'stats' && (
          <div className="admin-stats">
            <h2>Season Leaders</h2>
            <div className="admin-stats-leaders">
              <div className="admin-stats-category">
                <h3>Passing Yards</h3>
                <table>
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Player</th>
                      <th>Team</th>
                      <th>Yards</th>
                    </tr>
                  </thead>
                  <tbody>
                    {seasonLeaders.passing.map(leader => (
                      <tr key={leader.player_id} onClick={() => loadPlayerDetail(leader.player_id)}>
                        <td>{leader.rank}</td>
                        <td>{leader.player_name}</td>
                        <td>{leader.team_abbr}</td>
                        <td>{leader.value.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="admin-stats-category">
                <h3>Rushing Yards</h3>
                <table>
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Player</th>
                      <th>Team</th>
                      <th>Yards</th>
                    </tr>
                  </thead>
                  <tbody>
                    {seasonLeaders.rushing.map(leader => (
                      <tr key={leader.player_id} onClick={() => loadPlayerDetail(leader.player_id)}>
                        <td>{leader.rank}</td>
                        <td>{leader.player_name}</td>
                        <td>{leader.team_abbr}</td>
                        <td>{leader.value.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="admin-stats-category">
                <h3>Receiving Yards</h3>
                <table>
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Player</th>
                      <th>Team</th>
                      <th>Yards</th>
                    </tr>
                  </thead>
                  <tbody>
                    {seasonLeaders.receiving.map(leader => (
                      <tr key={leader.player_id} onClick={() => loadPlayerDetail(leader.player_id)}>
                        <td>{leader.rank}</td>
                        <td>{leader.player_name}</td>
                        <td>{leader.team_abbr}</td>
                        <td>{leader.value.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Simulate View */}
        {currentView === 'simulate' && (
          <div className="admin-simulate">
            <h2>Season Simulation</h2>

            {/* Current Status */}
            <div className="admin-sim-status">
              <div className="admin-stat-card">
                <div className="admin-stat-card__value">Week {league.current_week}</div>
                <div className="admin-stat-card__label">Current Week</div>
              </div>
              <div className="admin-stat-card">
                <div className="admin-stat-card__value">{18 - league.current_week}</div>
                <div className="admin-stat-card__label">Weeks Remaining</div>
              </div>
            </div>

            {/* Simulation Controls */}
            <div className="admin-sim-controls">
              <h3>Simulation Controls</h3>
              <div className="admin-sim-buttons">
                <button
                  className="admin-btn admin-btn--primary"
                  onClick={simulateWeek}
                  disabled={isSimulating || league.current_week >= 18}
                >
                  {isSimulating ? 'Simulating...' : 'Simulate Next Week'}
                </button>

                <button
                  className="admin-btn admin-btn--secondary"
                  onClick={() => simulateToWeek(Math.min(league.current_week + 4, 18))}
                  disabled={isSimulating || league.current_week >= 18}
                >
                  Simulate 4 Weeks
                </button>

                <button
                  className="admin-btn admin-btn--secondary"
                  onClick={() => simulateToWeek(9)}
                  disabled={isSimulating || league.current_week >= 9}
                >
                  Simulate to Week 9
                </button>

                <button
                  className="admin-btn admin-btn--secondary"
                  onClick={simulateSeason}
                  disabled={isSimulating || league.current_week >= 18}
                >
                  Simulate Full Season
                </button>

                {league.current_week >= 18 && (
                  <button
                    className="admin-btn admin-btn--primary"
                    onClick={simulatePlayoffs}
                    disabled={isSimulating || league.current_week >= 22}
                  >
                    {isSimulating ? 'Simulating...' : 'Simulate Playoffs'}
                  </button>
                )}
              </div>
            </div>

            {/* Last Simulation Results */}
            {lastSimResults.length > 0 && (
              <div className="admin-sim-results">
                <h3>Last Simulation Results</h3>
                {lastSimResults.slice(-3).map(weekResult => (
                  <div key={weekResult.week} className="admin-sim-week">
                    <h4>Week {weekResult.week} ({weekResult.total_games} games)</h4>
                    <div className="admin-sim-games">
                      {weekResult.games.map(game => (
                        <div key={game.game_id} className="admin-sim-game">
                          <span className={game.winner === game.away_team ? 'winner' : ''}>
                            {game.away_team} {game.away_score}
                          </span>
                          <span className="admin-sim-game__at">@</span>
                          <span className={game.winner === game.home_team ? 'winner' : ''}>
                            {game.home_team} {game.home_score}
                          </span>
                          {game.is_overtime && <span className="admin-sim-game__ot">OT</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Playoff Picture */}
            {playoffPicture && league.current_week > 0 && (
              <div className="admin-playoff-picture">
                <h3>Playoff Picture</h3>
                <div className="admin-playoff-grid">
                  {['afc', 'nfc'].map(conf => (
                    <div key={conf} className="admin-playoff-conference">
                      <h4>{conf.toUpperCase()}</h4>
                      <table>
                        <thead>
                          <tr>
                            <th>Seed</th>
                            <th>Team</th>
                            <th>Record</th>
                            <th>Type</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(conf === 'afc' ? playoffPicture.afc : playoffPicture.nfc).map(team => (
                            <tr
                              key={team.abbreviation}
                              className={team.is_division_winner ? 'division-winner' : 'wild-card'}
                              onClick={() => loadTeamDetail(team.abbreviation)}
                            >
                              <td>{team.seed}</td>
                              <td><strong>{team.abbreviation}</strong></td>
                              <td>{team.record}</td>
                              <td>{team.is_division_winner ? 'DIV' : 'WC'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Draft View */}
        {currentView === 'draft' && (
          <div className="admin-draft">
            <h2>Draft Room</h2>

            {/* No draft started */}
            {!draftState && (
              <div className="admin-draft-setup">
                <h3>Create New Draft</h3>
                <p>Choose a draft type to begin:</p>
                <div className="admin-draft-options">
                  <div className="admin-draft-option">
                    <h4>NFL Draft</h4>
                    <p>7 rounds, draft class only, worst-to-best order</p>
                    <button
                      className="admin-btn admin-btn--primary"
                      onClick={() => createDraft('nfl')}
                      disabled={isDrafting || league.draft_class_size === 0}
                    >
                      {isDrafting ? 'Creating...' : 'Create NFL Draft'}
                    </button>
                    {league.draft_class_size === 0 && (
                      <p className="admin-draft-warning">No draft class available</p>
                    )}
                  </div>
                  <div className="admin-draft-option">
                    <h4>Fantasy Draft</h4>
                    <p>15 rounds, all players available, snake draft order</p>
                    <button
                      className="admin-btn admin-btn--primary"
                      onClick={() => createDraft('fantasy')}
                      disabled={isDrafting}
                    >
                      {isDrafting ? 'Creating...' : 'Create Fantasy Draft'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Draft not started */}
            {draftState && draftState.phase === 'not_started' && (
              <div className="admin-draft-ready">
                <div className="admin-draft-info">
                  <h3>{draftState.draft_type.toUpperCase()} Draft Ready</h3>
                  <div className="admin-draft-meta">
                    <span>{draftState.num_teams} teams</span>
                    <span>|</span>
                    <span>{draftState.num_rounds} rounds</span>
                    <span>|</span>
                    <span>{draftState.picks_remaining} total picks</span>
                  </div>
                </div>
                <div className="admin-draft-actions">
                  <button
                    className="admin-btn admin-btn--primary"
                    onClick={startDraft}
                    disabled={isDrafting}
                  >
                    {isDrafting ? 'Starting...' : 'Start Draft'}
                  </button>
                  <button
                    className="admin-btn admin-btn--secondary"
                    onClick={() => { startDraft().then(() => simulateFullDraft()); }}
                    disabled={isDrafting}
                  >
                    Auto-Draft (Simulate All)
                  </button>
                </div>
              </div>
            )}

            {/* Draft in progress */}
            {draftState && draftState.phase === 'in_progress' && (
              <div className="admin-draft-live">
                {/* Current pick info */}
                <div className="admin-draft-current">
                  <div className="admin-draft-status">
                    <div className="admin-stat-card">
                      <div className="admin-stat-card__value">R{draftState.current_round}</div>
                      <div className="admin-stat-card__label">Round</div>
                    </div>
                    <div className="admin-stat-card">
                      <div className="admin-stat-card__value">#{draftState.current_pick?.pick_number || '-'}</div>
                      <div className="admin-stat-card__label">Overall Pick</div>
                    </div>
                    <div className="admin-stat-card">
                      <div className="admin-stat-card__value">{draftState.current_pick?.current_team || '-'}</div>
                      <div className="admin-stat-card__label">On the Clock</div>
                    </div>
                    <div className="admin-stat-card">
                      <div className="admin-stat-card__value">{draftState.picks_remaining}</div>
                      <div className="admin-stat-card__label">Picks Left</div>
                    </div>
                  </div>

                  <div className="admin-draft-controls">
                    <button
                      className="admin-btn admin-btn--secondary"
                      onClick={simulateFullDraft}
                      disabled={isDrafting}
                    >
                      {isDrafting ? 'Simulating...' : 'Simulate Remaining'}
                    </button>
                  </div>
                </div>

                {/* Two-column layout: Available players | Recent picks */}
                <div className="admin-draft-grid">
                  {/* Available players */}
                  <div className="admin-draft-available">
                    <div className="admin-draft-available__header">
                      <h3>Available Players</h3>
                      <select
                        value={draftPositionFilter}
                        onChange={(e) => {
                          setDraftPositionFilter(e.target.value);
                          adminApi.getAvailablePlayers(e.target.value || undefined, 100)
                            .then(setDraftAvailable);
                        }}
                      >
                        <option value="">All Positions</option>
                        <option value="QB">QB</option>
                        <option value="RB">RB</option>
                        <option value="WR">WR</option>
                        <option value="TE">TE</option>
                        <option value="LT">LT</option>
                        <option value="LG">LG</option>
                        <option value="C">C</option>
                        <option value="RG">RG</option>
                        <option value="RT">RT</option>
                        <option value="DE">DE</option>
                        <option value="DT">DT</option>
                        <option value="MLB">MLB</option>
                        <option value="OLB">OLB</option>
                        <option value="CB">CB</option>
                        <option value="FS">FS</option>
                        <option value="SS">SS</option>
                      </select>
                    </div>
                    <table className="admin-draft-table">
                      <thead>
                        <tr>
                          <th>Rank</th>
                          <th>Name</th>
                          <th>Pos</th>
                          <th>OVR</th>
                          <th>POT</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {draftAvailable.map((player, idx) => (
                          <tr key={player.id}>
                            <td>{idx + 1}</td>
                            <td>{player.full_name}</td>
                            <td>{player.position}</td>
                            <td style={{ color: getOverallColor(player.overall) }}>{player.overall}</td>
                            <td style={{ color: getOverallColor(player.potential) }}>{player.potential}</td>
                            <td>
                              <button
                                className="admin-btn admin-btn--small"
                                onClick={() => makeDraftPick(player.id)}
                                disabled={isDrafting}
                              >
                                Draft
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Recent picks */}
                  <div className="admin-draft-picks">
                    <h3>Recent Picks</h3>
                    <div className="admin-draft-pick-list">
                      {draftPicks
                        .filter(p => p.is_selected)
                        .slice(-20)
                        .reverse()
                        .map(pick => (
                          <div key={pick.id} className="admin-draft-pick-item">
                            <div className="admin-draft-pick-item__number">
                              R{pick.round} #{pick.pick_number}
                            </div>
                            <div className="admin-draft-pick-item__team">{pick.current_team}</div>
                            <div className="admin-draft-pick-item__player">
                              <strong>{pick.player_name}</strong>
                              <span>{pick.player_position}</span>
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Draft completed */}
            {draftState && draftState.phase === 'completed' && (
              <div className="admin-draft-complete">
                <h3>Draft Complete!</h3>
                <p>{draftState.picks_made} players were selected.</p>
                <div className="admin-draft-results">
                  <h4>Full Draft Results</h4>
                  <table className="admin-draft-results-table">
                    <thead>
                      <tr>
                        <th>Pick</th>
                        <th>Team</th>
                        <th>Player</th>
                        <th>Position</th>
                      </tr>
                    </thead>
                    <tbody>
                      {draftPicks.filter(p => p.is_selected).map(pick => (
                        <tr key={pick.id}>
                          <td>R{pick.round} #{pick.pick_number}</td>
                          <td>{pick.current_team}</td>
                          <td>{pick.player_name}</td>
                          <td>{pick.player_position}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <button
                  className="admin-btn admin-btn--secondary"
                  onClick={() => {
                    setDraftState(null);
                    setDraftPicks([]);
                  }}
                >
                  Start New Draft
                </button>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default AdminScreen;
