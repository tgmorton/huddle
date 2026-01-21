/**
 * HistoricalLeagueSelector - Browse and start from historical simulations
 *
 * Provides:
 * - List of available simulations
 * - Generate new simulation with streaming progress
 * - Browse teams with GM archetype, status, cap info
 * - Start franchise from selected team
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  History,
  Play,
  Users,
  TrendingUp,
  DollarSign,
  Trophy,
  RefreshCw,
  ChevronRight,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import {
  listSimulations,
  getTeamsInSeason,
  runSimulationWithProgress,
  startFranchiseFromSimulation,
  type SimulationSummary,
  type TeamSnapshot,
  type ProgressEvent,
} from '../../../api/historyClient';

// GM Archetype display info
const GM_ARCHETYPES: Record<string, { label: string; color: string; description: string }> = {
  analytics: { label: 'Analytics', color: '#3b82f6', description: 'Data-driven decisions' },
  old_school: { label: 'Old School', color: '#f59e0b', description: 'Traditional values' },
  cap_wizard: { label: 'Cap Wizard', color: '#10b981', description: 'Financial mastery' },
  win_now: { label: 'Win Now', color: '#ef4444', description: 'All-in approach' },
  balanced: { label: 'Balanced', color: '#8b5cf6', description: 'Measured approach' },
};

// Status badge colors
const STATUS_COLORS: Record<string, string> = {
  DYNASTY: '#fbbf24',
  CONTENDING: '#22c55e',
  WINDOW_CLOSING: '#f97316',
  REBUILDING: '#3b82f6',
  STRUGGLING: '#ef4444',
  UNKNOWN: '#6b7280',
};

interface HistoricalLeagueSelectorProps {
  onFranchiseCreated: (franchiseId: string) => void;
}

export const HistoricalLeagueSelector: React.FC<HistoricalLeagueSelectorProps> = ({
  onFranchiseCreated,
}) => {
  // State
  const [simulations, setSimulations] = useState<SimulationSummary[]>([]);
  const [selectedSim, setSelectedSim] = useState<SimulationSummary | null>(null);
  const [teams, setTeams] = useState<TeamSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingTeams, setLoadingTeams] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generatingProgress, setGeneratingProgress] = useState<string[]>([]);
  const [startingFranchise, setStartingFranchise] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load simulations on mount
  useEffect(() => {
    loadSimulations();
  }, []);

  const loadSimulations = async () => {
    setLoading(true);
    setError(null);
    try {
      const sims = await listSimulations();
      setSimulations(sims);
      // Auto-select the most recent simulation
      if (sims.length > 0 && !selectedSim) {
        handleSelectSimulation(sims[0]);
      }
    } catch (err) {
      setError('Failed to load simulations');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSimulation = async (sim: SimulationSummary) => {
    setSelectedSim(sim);
    setLoadingTeams(true);
    setError(null);
    try {
      // Load teams from the final season
      const teamData = await getTeamsInSeason(sim.sim_id, sim.end_year);
      // Sort by wins descending
      setTeams(teamData.sort((a, b) => b.wins - a.wins));
    } catch (err) {
      setError('Failed to load teams');
      console.error(err);
    } finally {
      setLoadingTeams(false);
    }
  };

  const handleGenerateNew = async () => {
    setGenerating(true);
    setGeneratingProgress([]);
    setError(null);

    try {
      const summary = await runSimulationWithProgress(
        {
          num_teams: 32,
          years_to_simulate: 3,
          start_year: 2021,
        },
        (event: ProgressEvent) => {
          if (event.type === 'progress' && event.message) {
            setGeneratingProgress((prev) => [...prev.slice(-10), event.message!]);
          }
        }
      );

      // Reload simulations and select the new one
      await loadSimulations();
      handleSelectSimulation(summary);
    } catch (err) {
      setError(`Generation failed: ${err}`);
      console.error(err);
    } finally {
      setGenerating(false);
      setGeneratingProgress([]);
    }
  };

  const handleStartFranchise = async (teamId: string) => {
    if (!selectedSim) return;

    setStartingFranchise(teamId);
    setError(null);

    try {
      const result = await startFranchiseFromSimulation(selectedSim.sim_id, teamId);
      onFranchiseCreated(result.franchise_id);
    } catch (err) {
      setError(`Failed to create franchise: ${err}`);
      console.error(err);
    } finally {
      setStartingFranchise(null);
    }
  };

  const formatCap = (capUsed: number, capPct: number) => {
    const millions = capUsed / 1000;
    return `$${millions.toFixed(0)}M (${capPct.toFixed(0)}%)`;
  };

  return (
    <div className="historical-selector">
      {/* Header */}
      <header className="historical-selector__header">
        <div className="historical-selector__title">
          <History size={20} />
          <h2>Historical Leagues</h2>
        </div>
        <p className="historical-selector__subtitle">
          Start from a pre-simulated league with realistic team histories
        </p>
      </header>

      {/* Simulation Selection */}
      <section className="historical-selector__section">
        <div className="historical-selector__section-header">
          <h3>Available Simulations</h3>
          <button
            className="historical-selector__btn historical-selector__btn--generate"
            onClick={handleGenerateNew}
            disabled={generating}
          >
            {generating ? (
              <>
                <Loader2 size={14} className="spinning" />
                <span>Generating...</span>
              </>
            ) : (
              <>
                <RefreshCw size={14} />
                <span>Generate New</span>
              </>
            )}
          </button>
        </div>

        {/* Generation Progress */}
        {generating && generatingProgress.length > 0 && (
          <div className="historical-selector__progress">
            {generatingProgress.map((msg, i) => (
              <div key={i} className="historical-selector__progress-line">
                {msg}
              </div>
            ))}
          </div>
        )}

        {/* Simulation List */}
        {loading ? (
          <div className="historical-selector__loading">
            <Loader2 size={20} className="spinning" />
            <span>Loading simulations...</span>
          </div>
        ) : simulations.length === 0 ? (
          <div className="historical-selector__empty">
            <p>No simulations available</p>
            <button
              className="historical-selector__btn historical-selector__btn--primary"
              onClick={handleGenerateNew}
              disabled={generating}
            >
              Generate Your First League
            </button>
          </div>
        ) : (
          <div className="historical-selector__sim-list">
            {simulations.map((sim) => (
              <button
                key={sim.sim_id}
                className={`historical-selector__sim-card ${
                  selectedSim?.sim_id === sim.sim_id ? 'historical-selector__sim-card--selected' : ''
                }`}
                onClick={() => handleSelectSimulation(sim)}
              >
                <div className="historical-selector__sim-info">
                  <span className="historical-selector__sim-years">
                    {sim.start_year} - {sim.end_year}
                  </span>
                  <span className="historical-selector__sim-teams">
                    {sim.num_teams} teams
                  </span>
                  <span className="historical-selector__sim-txns">
                    {sim.total_transactions} transactions
                  </span>
                </div>
                <ChevronRight size={16} />
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Team Selection */}
      {selectedSim && (
        <section className="historical-selector__section">
          <div className="historical-selector__section-header">
            <h3>Select a Team ({selectedSim.end_year})</h3>
          </div>

          {loadingTeams ? (
            <div className="historical-selector__loading">
              <Loader2 size={20} className="spinning" />
              <span>Loading teams...</span>
            </div>
          ) : (
            <div className="historical-selector__team-grid">
              {teams.map((team) => {
                const gmInfo = GM_ARCHETYPES[team.gm_archetype || 'balanced'];
                const statusColor = STATUS_COLORS[team.status] || STATUS_COLORS.UNKNOWN;

                return (
                  <div key={team.team_id} className="historical-selector__team-card">
                    {/* Team Header */}
                    <div className="historical-selector__team-header">
                      <span className="historical-selector__team-name">{team.team_name}</span>
                      <span
                        className="historical-selector__team-status"
                        style={{ backgroundColor: statusColor }}
                      >
                        {team.status}
                      </span>
                    </div>

                    {/* Team Stats */}
                    <div className="historical-selector__team-stats">
                      <div className="historical-selector__stat">
                        <Trophy size={12} />
                        <span>{team.wins}-{team.losses}</span>
                        <span className="historical-selector__stat-label">Record</span>
                      </div>
                      <div className="historical-selector__stat">
                        <DollarSign size={12} />
                        <span>{formatCap(team.cap_used, team.cap_pct)}</span>
                        <span className="historical-selector__stat-label">Cap</span>
                      </div>
                      <div className="historical-selector__stat">
                        <Users size={12} />
                        <span>{team.roster_size}</span>
                        <span className="historical-selector__stat-label">Roster</span>
                      </div>
                    </div>

                    {/* GM Archetype */}
                    {gmInfo && (
                      <div
                        className="historical-selector__gm-badge"
                        style={{ borderColor: gmInfo.color }}
                      >
                        <TrendingUp size={12} style={{ color: gmInfo.color }} />
                        <span>{gmInfo.label}</span>
                      </div>
                    )}

                    {/* Start Button */}
                    <button
                      className="historical-selector__btn historical-selector__btn--start"
                      onClick={() => handleStartFranchise(team.team_id)}
                      disabled={startingFranchise !== null}
                    >
                      {startingFranchise === team.team_id ? (
                        <>
                          <Loader2 size={14} className="spinning" />
                          <span>Starting...</span>
                        </>
                      ) : (
                        <>
                          <Play size={14} />
                          <span>Start as {team.team_name.split(' ').pop()}</span>
                        </>
                      )}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      )}

      {/* Error Display */}
      {error && (
        <div className="historical-selector__error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};

export default HistoricalLeagueSelector;
