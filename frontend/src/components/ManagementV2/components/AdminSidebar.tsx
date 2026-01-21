/**
 * AdminSidebar - Developer/admin controls for ManagementV2
 *
 * Provides:
 * - Franchise creation/connection
 * - Quick simulation controls
 * - Debug tools
 */

import React, { useState, useEffect } from 'react';
import { X, Play, FastForward, Zap, RefreshCw, Plus, Trash2, Link2, Download, History, Clock } from 'lucide-react';
import { adminApi, type SavedLeague } from '../../../api/adminClient';
import { managementApi } from '../../../api/managementClient';
import {
  listSimulations,
  runSimulationWithProgress,
  startFranchiseFromSimulation,
  saveSimulation,
  loadSavedSimulation,
  listSavedSimulations,
  type SimulationSummary,
  type SavedSimulationInfo,
  type ProgressEvent,
} from '../../../api/historyClient';
import { useManagementStore } from '../../../stores/managementStore';
import type { LeagueSummary, TeamSummary } from '../../../types/admin';

interface AdminSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  franchiseId: string | null;
  onFranchiseChange: (id: string | null) => void;
  onLog: (message: string, type?: 'info' | 'success' | 'error' | 'warning') => void;
}

export const AdminSidebar: React.FC<AdminSidebarProps> = ({
  isOpen,
  onClose,
  franchiseId,
  onFranchiseChange,
  onLog,
}) => {
  // Get WebSocket connection status from store
  const { isConnected } = useManagementStore();

  // League state
  const [league, setLeague] = useState<LeagueSummary | null>(null);
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [sessions, setSessions] = useState<string[]>([]);
  const [selectedTeamAbbr, setSelectedTeamAbbr] = useState<string>('');
  const [savedLeagues, setSavedLeagues] = useState<SavedLeague[]>([]);

  // Loading states
  const [isGenerating, setIsGenerating] = useState(false);
  const [isCreatingFranchise, setIsCreatingFranchise] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [isLoadingLeague, setIsLoadingLeague] = useState(false);

  // Historical simulation state
  const [historicalSims, setHistoricalSims] = useState<SimulationSummary[]>([]);
  const [savedSims, setSavedSims] = useState<SavedSimulationInfo[]>([]);
  const [isGeneratingHistorical, setIsGeneratingHistorical] = useState(false);
  const [historicalProgress, setHistoricalProgress] = useState<string>('');
  const [selectedHistoricalSim, setSelectedHistoricalSim] = useState<string>('');
  const [selectedHistoricalTeam, setSelectedHistoricalTeam] = useState<string>('');
  const [isStartingFromHistorical, setIsStartingFromHistorical] = useState(false);
  const [isSavingSimulation, setIsSavingSimulation] = useState(false);
  const [isLoadingSimulation, setIsLoadingSimulation] = useState(false);

  // Load league info on mount
  useEffect(() => {
    if (isOpen) {
      loadLeagueInfo();
      loadSessions();
      loadHistoricalSimulations();
    }
  }, [isOpen]);

  const loadHistoricalSimulations = async () => {
    try {
      const sims = await listSimulations();
      setHistoricalSims(sims);
      if (sims.length > 0 && !selectedHistoricalSim) {
        setSelectedHistoricalSim(sims[0].sim_id);
      }
    } catch {
      setHistoricalSims([]);
    }

    // Also load saved simulations
    try {
      const saved = await listSavedSimulations();
      setSavedSims(saved);
    } catch {
      setSavedSims([]);
    }
  };

  const loadLeagueInfo = async () => {
    try {
      const leagueData = await adminApi.getLeague();
      setLeague(leagueData);
      setSavedLeagues([]); // Clear saved leagues when we have a current league
      const teamsData = await adminApi.listTeams();
      setTeams(teamsData);
      if (teamsData.length > 0 && !selectedTeamAbbr) {
        setSelectedTeamAbbr(teamsData[0].abbreviation);
      }
      onLog('League info loaded', 'info');
    } catch {
      setLeague(null);
      setTeams([]);
      // Try to load saved leagues
      try {
        const saved = await adminApi.listLeagues();
        setSavedLeagues(saved);
        if (saved.length > 0) {
          onLog(`No active league - ${saved.length} saved league(s) available`, 'info');
        } else {
          onLog('No league exists', 'warning');
        }
      } catch {
        setSavedLeagues([]);
        onLog('No league exists', 'warning');
      }
    }
  };

  const handleLoadLeague = async (leagueId: string) => {
    setIsLoadingLeague(true);
    onLog('Loading saved league...', 'info');
    try {
      const leagueData = await adminApi.loadLeague(leagueId);
      setLeague(leagueData);
      setSavedLeagues([]);
      await loadLeagueInfo();
      onLog(`League loaded: ${leagueData.team_count} teams`, 'success');
    } catch (err) {
      onLog(`Failed to load league: ${err}`, 'error');
    } finally {
      setIsLoadingLeague(false);
    }
  };

  const loadSessions = async () => {
    try {
      const sessionsData = await managementApi.listSessions();
      setSessions(sessionsData.active_sessions || []);
    } catch {
      setSessions([]);
    }
  };

  const handleGenerateLeague = async (fantasyDraft: boolean = false) => {
    setIsGenerating(true);
    onLog(`Generating ${fantasyDraft ? 'fantasy draft' : 'standard'} league...`, 'info');
    try {
      const data = await adminApi.generateLeague({
        season: 2024,
        include_schedule: true,
        fantasy_draft: fantasyDraft,
      });
      setLeague(data);
      await loadLeagueInfo();
      onLog(`League generated: ${data.team_count} teams, ${data.total_players} players`, 'success');
    } catch (err) {
      onLog(`Failed to generate league: ${err}`, 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCreateFranchise = async () => {
    if (!selectedTeamAbbr) {
      onLog('Select a team first', 'warning');
      return;
    }

    // Get full team details to get the team ID
    const selectedTeam = teams.find(t => t.abbreviation === selectedTeamAbbr);
    if (!selectedTeam) {
      onLog('Team not found', 'error');
      return;
    }

    setIsCreatingFranchise(true);
    onLog(`Creating franchise for ${selectedTeamAbbr}...`, 'info');
    try {
      const session = await managementApi.createFranchise({
        team_id: selectedTeam.id,
        team_name: selectedTeam.name,
        season_year: league?.current_season || 2024,
      });
      onFranchiseChange(session.franchise_id);
      await loadSessions();
      onLog(`Franchise created: ${session.franchise_id.slice(0, 8)}...`, 'success');

      // Start portrait generation polling
      const franchiseState = await managementApi.getFranchise(session.franchise_id);
      const leagueId = (franchiseState as { league_id?: string }).league_id;
      if (leagueId) {
        onLog('Portrait generation started...', 'info');
        pollPortraitStatus(leagueId);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      onLog(`Failed to create franchise: ${errorMsg}`, 'error');
    } finally {
      setIsCreatingFranchise(false);
    }
  };

  // Poll portrait batch status and log progress
  const pollPortraitStatus = async (leagueId: string) => {
    let lastCompleted = 0;
    const poll = async () => {
      try {
        const status = await managementApi.getPortraitBatchStatus(leagueId);
        if (status.completed !== lastCompleted) {
          const pct = Math.round((status.completed / status.total) * 100);
          onLog(`Portraits: ${status.completed}/${status.total} (${pct}%)`, 'info');
          lastCompleted = status.completed;
        }
        if (status.status === 'complete') {
          onLog(`Portrait generation complete: ${status.total} portraits`, 'success');
          return;
        }
        if (status.status === 'failed') {
          onLog(`Portrait generation failed: ${status.failed} errors`, 'error');
          return;
        }
        // Continue polling
        setTimeout(poll, 2000);
      } catch {
        // Endpoint might not exist yet, silently stop
      }
    };
    poll();
  };

  const handleConnectFranchise = (id: string) => {
    onFranchiseChange(id);
    onLog(`Connecting to franchise: ${id}`, 'info');
  };

  const handleDeleteFranchise = async (id: string) => {
    try {
      await managementApi.deleteFranchise(id);
      if (franchiseId === id) {
        onFranchiseChange(null);
      }
      await loadSessions();
      onLog(`Franchise deleted: ${id}`, 'success');
    } catch (err) {
      onLog(`Failed to delete franchise: ${err}`, 'error');
    }
  };

  const handleSimulateWeek = async () => {
    setIsSimulating(true);
    onLog('Simulating week...', 'info');
    try {
      const result = await adminApi.simulateWeek({});
      onLog(`Week ${result.week} simulated: ${result.total_games} games`, 'success');
      await loadLeagueInfo();
    } catch (err) {
      onLog(`Simulation failed: ${err}`, 'error');
    } finally {
      setIsSimulating(false);
    }
  };

  const handleSimulateToPlayoffs = async () => {
    setIsSimulating(true);
    onLog('Simulating to playoffs...', 'info');
    try {
      const results = await adminApi.simulateToWeek({ target_week: 18 });
      onLog(`Simulated ${results.length} weeks to playoffs`, 'success');
      await loadLeagueInfo();
    } catch (err) {
      onLog(`Simulation failed: ${err}`, 'error');
    } finally {
      setIsSimulating(false);
    }
  };

  const handleSimulateSeason = async () => {
    setIsSimulating(true);
    onLog('Simulating full season...', 'info');
    try {
      const results = await adminApi.simulateSeason();
      onLog(`Season simulated: ${results.length} weeks`, 'success');
      await loadLeagueInfo();
    } catch (err) {
      onLog(`Simulation failed: ${err}`, 'error');
    } finally {
      setIsSimulating(false);
    }
  };

  const handleSimulatePlayoffs = async () => {
    setIsSimulating(true);
    onLog('Simulating playoffs...', 'info');
    try {
      await adminApi.simulatePlayoffs();
      onLog('Playoffs simulated', 'success');
      await loadLeagueInfo();
    } catch (err) {
      onLog(`Simulation failed: ${err}`, 'error');
    } finally {
      setIsSimulating(false);
    }
  };

  // Historical Simulation Handlers
  const handleGenerateHistorical = async () => {
    setIsGeneratingHistorical(true);
    setHistoricalProgress('Starting simulation...');
    onLog('Generating historical simulation (3 years)...', 'info');

    try {
      const summary = await runSimulationWithProgress(
        { years_to_simulate: 3, start_year: 2021 },
        (event: ProgressEvent) => {
          if (event.type === 'progress' && event.message) {
            setHistoricalProgress(event.message);
            onLog(event.message, 'info');
          }
        }
      );
      setHistoricalProgress('');
      onLog(`Historical simulation complete: ${summary.seasons_simulated} seasons`, 'success');
      await loadHistoricalSimulations();
      setSelectedHistoricalSim(summary.sim_id);
    } catch (err) {
      setHistoricalProgress('');
      onLog(`Historical simulation failed: ${err}`, 'error');
    } finally {
      setIsGeneratingHistorical(false);
    }
  };

  const handleStartFromHistorical = async () => {
    if (!selectedHistoricalSim || !selectedHistoricalTeam) {
      onLog('Select a simulation and team first', 'warning');
      return;
    }

    setIsStartingFromHistorical(true);
    onLog(`Starting franchise from historical sim: ${selectedHistoricalTeam}...`, 'info');

    try {
      const result = await startFranchiseFromSimulation(selectedHistoricalSim, selectedHistoricalTeam);
      onFranchiseChange(result.franchise_id);
      await loadSessions();
      await loadLeagueInfo();
      onLog(`Franchise created: ${result.team_name} (${result.season})`, 'success');

      // Start portrait generation polling
      if (result.league_id) {
        onLog('Portrait generation started...', 'info');
        pollPortraitStatus(result.league_id);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      onLog(`Failed to start from historical: ${errorMsg}`, 'error');
    } finally {
      setIsStartingFromHistorical(false);
    }
  };

  const handleSaveSimulation = async (simId: string) => {
    setIsSavingSimulation(true);
    onLog(`Saving simulation ${simId}...`, 'info');

    try {
      await saveSimulation(simId);
      onLog(`Simulation saved: ${simId}`, 'success');
      await loadHistoricalSimulations(); // Refresh saved list
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      onLog(`Failed to save simulation: ${errorMsg}`, 'error');
    } finally {
      setIsSavingSimulation(false);
    }
  };

  const handleLoadSavedSimulation = async (simId: string) => {
    setIsLoadingSimulation(true);
    onLog(`Loading saved simulation ${simId}...`, 'info');

    try {
      const summary = await loadSavedSimulation(simId);
      onLog(`Simulation loaded: ${summary.start_year}-${summary.end_year}`, 'success');
      await loadHistoricalSimulations(); // Refresh in-memory list
      setSelectedHistoricalSim(simId);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      onLog(`Failed to load simulation: ${errorMsg}`, 'error');
    } finally {
      setIsLoadingSimulation(false);
    }
  };

  // Get team options from selected historical simulation
  const selectedSim = historicalSims.find(s => s.sim_id === selectedHistoricalSim);

  if (!isOpen) return null

  return (
    <aside className="admin-sidebar">
      <header className="admin-sidebar__header">
        <h2>Admin Panel</h2>
        <button className="admin-sidebar__close" onClick={onClose}>
          <X size={16} />
        </button>
      </header>

      <div className="admin-sidebar__content">
        {/* League Section */}
        <section className="admin-sidebar__section">
          <h3>League</h3>
          {league ? (
            <div className="admin-sidebar__info">
              <div className="admin-sidebar__stat">
                <span className="admin-sidebar__stat-label">Season</span>
                <span className="admin-sidebar__stat-value">{league.current_season}</span>
              </div>
              <div className="admin-sidebar__stat">
                <span className="admin-sidebar__stat-label">Week</span>
                <span className="admin-sidebar__stat-value">{league.current_week}</span>
              </div>
              <div className="admin-sidebar__stat">
                <span className="admin-sidebar__stat-label">Teams</span>
                <span className="admin-sidebar__stat-value">{league.team_count}</span>
              </div>
              <div className="admin-sidebar__stat">
                <span className="admin-sidebar__stat-label">Players</span>
                <span className="admin-sidebar__stat-value">{league.total_players}</span>
              </div>
            </div>
          ) : (
            <p className="admin-sidebar__empty">No league exists</p>
          )}
          <div className="admin-sidebar__actions">
            {!league && savedLeagues.length > 0 && (
              <button
                className="admin-sidebar__btn admin-sidebar__btn--primary"
                onClick={() => handleLoadLeague(savedLeagues[0].id)}
                disabled={isLoadingLeague}
              >
                <Download size={14} />
                <span>{isLoadingLeague ? 'Loading...' : `Load ${savedLeagues[0].name} (${savedLeagues[0].season})`}</span>
              </button>
            )}
            <button
              className={`admin-sidebar__btn ${!savedLeagues.length && !league ? 'admin-sidebar__btn--primary' : ''}`}
              onClick={() => handleGenerateLeague(false)}
              disabled={isGenerating || isLoadingLeague}
            >
              {isGenerating ? 'Generating...' : league ? 'Regenerate' : 'Generate League'}
            </button>
            {!league && (
              <button
                className="admin-sidebar__btn"
                onClick={() => handleGenerateLeague(true)}
                disabled={isGenerating || isLoadingLeague}
              >
                Fantasy Draft
              </button>
            )}
          </div>
        </section>

        {/* Franchise Section */}
        <section className="admin-sidebar__section">
          <h3>Franchise</h3>
          {franchiseId ? (
            <div className="admin-sidebar__connected">
              <span className={`admin-sidebar__connected-label ${isConnected ? '' : 'admin-sidebar__connected-label--disconnected'}`}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
              <code className="admin-sidebar__franchise-id">{franchiseId.slice(0, 8)}...</code>
            </div>
          ) : (
            <p className="admin-sidebar__empty">No franchise</p>
          )}

          {league && teams.length > 0 && (
            <div className="admin-sidebar__create">
              <select
                className="admin-sidebar__select"
                value={selectedTeamAbbr}
                onChange={(e) => setSelectedTeamAbbr(e.target.value)}
              >
                {teams.map(team => (
                  <option key={team.abbreviation} value={team.abbreviation}>
                    {team.abbreviation} - {team.name}
                  </option>
                ))}
              </select>
              <button
                className="admin-sidebar__btn admin-sidebar__btn--icon"
                onClick={handleCreateFranchise}
                disabled={isCreatingFranchise || !selectedTeamAbbr}
                title="Create Franchise"
              >
                <Plus size={16} />
              </button>
            </div>
          )}

          {sessions.length > 0 && (
            <div className="admin-sidebar__sessions">
              <h4>Active Sessions</h4>
              {sessions.map(sessionId => (
                <div key={sessionId} className="admin-sidebar__session">
                  <code className="admin-sidebar__session-id">{sessionId.slice(0, 12)}...</code>
                  <button
                    className="admin-sidebar__btn admin-sidebar__btn--icon admin-sidebar__btn--small"
                    onClick={() => handleConnectFranchise(sessionId)}
                    title="Connect"
                    disabled={franchiseId === sessionId}
                  >
                    <Link2 size={12} />
                  </button>
                  <button
                    className="admin-sidebar__btn admin-sidebar__btn--icon admin-sidebar__btn--small admin-sidebar__btn--danger"
                    onClick={() => handleDeleteFranchise(sessionId)}
                    title="Delete"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Quick Sim Section */}
        <section className="admin-sidebar__section">
          <h3>Quick Sim</h3>
          <div className="admin-sidebar__actions admin-sidebar__actions--grid">
            <button
              className="admin-sidebar__btn"
              onClick={handleSimulateWeek}
              disabled={isSimulating || !league || league.current_week >= 22}
            >
              <Play size={14} />
              <span>Week</span>
            </button>
            <button
              className="admin-sidebar__btn"
              onClick={handleSimulateToPlayoffs}
              disabled={isSimulating || !league || league.current_week >= 18}
            >
              <FastForward size={14} />
              <span>To Playoffs</span>
            </button>
            <button
              className="admin-sidebar__btn"
              onClick={handleSimulateSeason}
              disabled={isSimulating || !league || league.current_week >= 18}
            >
              <Zap size={14} />
              <span>Season</span>
            </button>
            <button
              className="admin-sidebar__btn"
              onClick={handleSimulatePlayoffs}
              disabled={isSimulating || !league || league.current_week < 18 || league.current_week >= 22}
            >
              <Zap size={14} />
              <span>Playoffs</span>
            </button>
          </div>
        </section>

        {/* Historical Simulation Section */}
        <section className="admin-sidebar__section">
          <h3>
            <History size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
            Historical League
          </h3>
          {historicalSims.length > 0 ? (
            <div className="admin-sidebar__info">
              <div className="admin-sidebar__stat">
                <span className="admin-sidebar__stat-label">Available</span>
                <span className="admin-sidebar__stat-value">{historicalSims.length} sim(s)</span>
              </div>
            </div>
          ) : (
            <p className="admin-sidebar__empty">No historical simulations</p>
          )}

          {isGeneratingHistorical && historicalProgress && (
            <div className="admin-sidebar__progress">
              <Clock size={12} className="admin-sidebar__progress-icon" />
              <span className="admin-sidebar__progress-text">{historicalProgress}</span>
            </div>
          )}

          <div className="admin-sidebar__actions">
            <button
              className="admin-sidebar__btn admin-sidebar__btn--primary"
              onClick={handleGenerateHistorical}
              disabled={isGeneratingHistorical}
            >
              <History size={14} />
              <span>{isGeneratingHistorical ? 'Generating...' : 'Generate Historical'}</span>
            </button>
          </div>

          {historicalSims.length > 0 && (
            <div className="admin-sidebar__historical-start">
              <h4>Start from Simulation</h4>
              <div className="admin-sidebar__sim-select-row">
                <select
                  className="admin-sidebar__select"
                  value={selectedHistoricalSim}
                  onChange={(e) => {
                    setSelectedHistoricalSim(e.target.value);
                    setSelectedHistoricalTeam(''); // Reset team when sim changes
                  }}
                >
                  {historicalSims.map(sim => (
                    <option key={sim.sim_id} value={sim.sim_id}>
                      {sim.start_year}-{sim.end_year} ({sim.seasons_simulated}yr)
                    </option>
                  ))}
                </select>
                <button
                  className="admin-sidebar__btn admin-sidebar__btn--icon admin-sidebar__btn--small"
                  onClick={() => selectedHistoricalSim && handleSaveSimulation(selectedHistoricalSim)}
                  disabled={isSavingSimulation || !selectedHistoricalSim}
                  title="Save simulation to disk"
                >
                  <Download size={12} />
                </button>
              </div>
              <select
                className="admin-sidebar__select"
                value={selectedHistoricalTeam}
                onChange={(e) => setSelectedHistoricalTeam(e.target.value)}
                disabled={!selectedHistoricalSim}
              >
                <option value="">Select team...</option>
                {/* Common NFL team abbreviations */}
                {['ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE',
                  'DAL', 'DEN', 'DET', 'GB', 'HOU', 'IND', 'JAX', 'KC',
                  'LAC', 'LAR', 'LV', 'MIA', 'MIN', 'NE', 'NO', 'NYG',
                  'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WAS'].map(abbr => (
                  <option key={abbr} value={abbr}>{abbr}</option>
                ))}
              </select>
              <button
                className="admin-sidebar__btn admin-sidebar__btn--primary"
                onClick={handleStartFromHistorical}
                disabled={isStartingFromHistorical || !selectedHistoricalSim || !selectedHistoricalTeam}
              >
                <Play size={14} />
                <span>{isStartingFromHistorical ? 'Starting...' : 'Start Franchise'}</span>
              </button>
            </div>
          )}

          {savedSims.length > 0 && (
            <div className="admin-sidebar__saved-sims">
              <h4>Saved Simulations</h4>
              {savedSims.map(sim => (
                <div key={sim.sim_id} className="admin-sidebar__saved-sim">
                  <span className="admin-sidebar__saved-sim-info">
                    {sim.start_year}-{sim.end_year}
                  </span>
                  <button
                    className="admin-sidebar__btn admin-sidebar__btn--icon admin-sidebar__btn--small"
                    onClick={() => handleLoadSavedSimulation(sim.sim_id)}
                    disabled={isLoadingSimulation || historicalSims.some(s => s.sim_id === sim.sim_id)}
                    title={historicalSims.some(s => s.sim_id === sim.sim_id) ? 'Already loaded' : 'Load into memory'}
                  >
                    <Play size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Debug Section */}
        <section className="admin-sidebar__section">
          <h3>Debug</h3>
          <div className="admin-sidebar__actions">
            <button
              className="admin-sidebar__btn"
              onClick={() => {
                loadLeagueInfo();
                loadSessions();
                loadHistoricalSimulations();
                onLog('Refreshed all data', 'info');
              }}
            >
              <RefreshCw size={14} />
              <span>Refresh All</span>
            </button>
          </div>
        </section>
      </div>
    </aside>
  );
};

export default AdminSidebar;
