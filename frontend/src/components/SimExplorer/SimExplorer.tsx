/**
 * SimExplorer - Historical Simulation Explorer
 *
 * Allows exploring simulated league history:
 * - Generate new simulations
 * - Browse teams, rosters, standings
 * - View draft results and transactions
 */

import { useEffect } from 'react';
import { useSimExplorerStore } from '../../stores/simExplorerStore';
import type { ViewMode } from '../../stores/simExplorerStore';
import './SimExplorer.css';

export default function SimExplorer() {
  const {
    simulations,
    currentSimulation,
    selectedSeason,
    selectedTeamId,
    viewMode,
    standings,
    draft,
    transactions,
    selectedRoster,
    isLoading,
    isGenerating,
    progressMessage,
    error,
    loadSimulations,
    generateSimulation,
    selectSimulation,
    selectSeason,
    selectTeam,
    setViewMode,
    clearError,
  } = useSimExplorerStore();

  useEffect(() => {
    loadSimulations();
  }, [loadSimulations]);

  const seasons = currentSimulation
    ? Array.from(
        { length: currentSimulation.summary.seasons_simulated },
        (_, i) => currentSimulation.config.start_year + i
      )
    : [];

  return (
    <div className="sim-explorer">
      {/* Header */}
      <header className="sim-explorer-header">
        <h1>League History Explorer</h1>
        <div className="header-actions">
          {isGenerating && progressMessage && (
            <span className="progress-message">{progressMessage}</span>
          )}
          <button
            className="generate-btn"
            onClick={() => generateSimulation()}
            disabled={isGenerating}
          >
            {isGenerating ? 'Generating...' : 'Generate New League'}
          </button>
        </div>
      </header>

      {/* Error Display */}
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={clearError}>Dismiss</button>
        </div>
      )}

      <div className="sim-explorer-content">
        {/* Left Sidebar */}
        <aside className="sim-sidebar">
          {/* Simulation Selector */}
          <section className="sidebar-section">
            <h3>Simulations</h3>
            {simulations.length === 0 ? (
              <p className="empty-state">No simulations yet. Generate one to start!</p>
            ) : (
              <ul className="sim-list">
                {simulations.map((sim) => (
                  <li
                    key={sim.sim_id}
                    className={currentSimulation?.sim_id === sim.sim_id ? 'selected' : ''}
                    onClick={() => selectSimulation(sim.sim_id)}
                  >
                    <span className="sim-id">{sim.sim_id}</span>
                    <span className="sim-info">
                      {sim.num_teams} teams, {sim.seasons_simulated} seasons
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Season Selector */}
          {currentSimulation && (
            <section className="sidebar-section">
              <h3>Seasons</h3>
              <ul className="season-list">
                {seasons.map((season) => (
                  <li
                    key={season}
                    className={selectedSeason === season ? 'selected' : ''}
                    onClick={() => selectSeason(season)}
                  >
                    {season}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Team List */}
          {currentSimulation && (
            <section className="sidebar-section team-list-section">
              <h3>Teams</h3>
              <ul className="team-list">
                {currentSimulation.teams
                  .sort((a, b) => b.win_pct - a.win_pct)
                  .map((team) => (
                    <li
                      key={team.team_id}
                      className={selectedTeamId === team.team_id ? 'selected' : ''}
                      onClick={() => selectTeam(team.team_id)}
                    >
                      <span className="team-name">{team.team_name}</span>
                      <span className="team-record">
                        {team.wins}-{team.losses}
                      </span>
                      <span className={`team-status status-${team.status.toLowerCase()}`}>
                        {team.status}
                      </span>
                    </li>
                  ))}
              </ul>
            </section>
          )}
        </aside>

        {/* Main Content */}
        <main className="sim-main">
          {!currentSimulation ? (
            <div className="empty-main">
              <p>Select a simulation or generate a new one</p>
            </div>
          ) : (
            <>
              {/* View Tabs */}
              <nav className="view-tabs">
                {(['overview', 'standings', 'roster', 'draft', 'transactions'] as ViewMode[]).map(
                  (mode) => (
                    <button
                      key={mode}
                      className={viewMode === mode ? 'active' : ''}
                      onClick={() => setViewMode(mode)}
                    >
                      {mode.charAt(0).toUpperCase() + mode.slice(1)}
                    </button>
                  )
                )}
              </nav>

              {/* View Content */}
              <div className="view-content">
                {isLoading && <div className="loading">Loading...</div>}

                {viewMode === 'overview' && <OverviewView simulation={currentSimulation} />}
                {viewMode === 'standings' && standings && <StandingsView standings={standings} />}
                {viewMode === 'roster' && selectedRoster && <RosterView roster={selectedRoster} />}
                {viewMode === 'roster' && !selectedRoster && (
                  <div className="empty-view">Select a team to view roster</div>
                )}
                {viewMode === 'draft' && draft && <DraftView draft={draft} />}
                {viewMode === 'transactions' && transactions && (
                  <TransactionsView transactions={transactions} />
                )}
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

// Sub-components

function OverviewView({ simulation }: { simulation: import('../../api/historyClient').FullSimulationData }) {
  return (
    <div className="overview-view">
      <div className="overview-stats">
        <div className="stat-card">
          <span className="stat-label">Teams</span>
          <span className="stat-value">{simulation.config.num_teams}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Seasons</span>
          <span className="stat-value">{simulation.summary.seasons_simulated}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Transactions</span>
          <span className="stat-value">{simulation.summary.total_transactions}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Years</span>
          <span className="stat-value">
            {simulation.summary.start_year} - {simulation.summary.end_year}
          </span>
        </div>
      </div>

      <h3>Season Summaries</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Season</th>
            <th>Transactions</th>
            <th>Draft Picks</th>
            <th>Avg Cap Usage</th>
          </tr>
        </thead>
        <tbody>
          {simulation.seasons.map((season) => (
            <tr key={season.season}>
              <td>{season.season}</td>
              <td>{season.total_transactions}</td>
              <td>{season.draft_picks}</td>
              <td>{season.avg_cap_usage.toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Team Overview</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Team</th>
            <th>Record</th>
            <th>Win%</th>
            <th>Roster</th>
            <th>Cap Used</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {simulation.teams
            .sort((a, b) => b.win_pct - a.win_pct)
            .map((team) => (
              <tr key={team.team_id}>
                <td>{team.team_name}</td>
                <td>
                  {team.wins}-{team.losses}
                </td>
                <td>{(team.win_pct * 100).toFixed(1)}%</td>
                <td>{team.roster_size}</td>
                <td>{team.cap_pct.toFixed(1)}%</td>
                <td className={`status-${team.status.toLowerCase()}`}>{team.status}</td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}

function StandingsView({ standings }: { standings: import('../../api/historyClient').StandingsData }) {
  return (
    <div className="standings-view">
      <h3>{standings.season} Standings</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Team</th>
            <th>W</th>
            <th>L</th>
            <th>Win%</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {standings.teams.map((team) => (
            <tr key={team.team_id}>
              <td>{team.rank}</td>
              <td>{team.team_name}</td>
              <td>{team.wins}</td>
              <td>{team.losses}</td>
              <td>{(team.win_pct * 100).toFixed(1)}%</td>
              <td className={`status-${team.status.toLowerCase()}`}>{team.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RosterView({ roster }: { roster: import('../../api/historyClient').TeamRoster }) {
  const formatMoney = (k: number) => `$${(k / 1000).toFixed(1)}M`;

  return (
    <div className="roster-view">
      <div className="roster-header">
        <h3>{roster.team_name} Roster</h3>
        <div className="cap-info">
          <span>Cap Used: {formatMoney(roster.cap_used)}</span>
          <span>Cap Remaining: {formatMoney(roster.cap_remaining)}</span>
        </div>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Pos</th>
            <th>OVR</th>
            <th>Age</th>
            <th>Exp</th>
            <th>Cap Hit</th>
            <th>Years</th>
            <th>Type</th>
          </tr>
        </thead>
        <tbody>
          {roster.players.map((player) => (
            <tr key={player.id}>
              <td>{player.full_name}</td>
              <td>{player.position}</td>
              <td className={`overall ovr-${Math.floor(player.overall / 10) * 10}`}>
                {player.overall}
              </td>
              <td>{player.age}</td>
              <td>{player.experience_years}</td>
              <td>{player.contract ? formatMoney(player.contract.cap_hit) : '-'}</td>
              <td>{player.contract?.years_remaining ?? '-'}</td>
              <td>{player.contract?.contract_type ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DraftView({ draft }: { draft: import('../../api/historyClient').DraftData }) {
  return (
    <div className="draft-view">
      <h3>{draft.season} Draft</h3>
      {draft.picks.length === 0 ? (
        <p className="empty-state">No draft data available for this season</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Pick</th>
              <th>Team</th>
              <th>Player</th>
              <th>Pos</th>
              <th>OVR</th>
            </tr>
          </thead>
          <tbody>
            {draft.picks.map((pick) => (
              <tr key={pick.overall}>
                <td>
                  Rd {pick.round}, #{pick.pick} ({pick.overall})
                </td>
                <td>{pick.team_name}</td>
                <td>{pick.player_name}</td>
                <td>{pick.position}</td>
                <td className={`overall ovr-${Math.floor(pick.overall_rating / 10) * 10}`}>
                  {pick.overall_rating}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function TransactionsView({ transactions }: { transactions: import('../../api/historyClient').TransactionLog }) {
  const typeColors: Record<string, string> = {
    DRAFT: 'type-draft',
    SIGNING: 'type-signing',
    CUT: 'type-cut',
    TRADE: 'type-trade',
  };

  return (
    <div className="transactions-view">
      <h3>Transactions ({transactions.total_count} total)</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Type</th>
            <th>Season</th>
            <th>Team</th>
            <th>Player</th>
            <th>Position</th>
          </tr>
        </thead>
        <tbody>
          {transactions.transactions.map((tx) => (
            <tr key={tx.id}>
              <td className={typeColors[tx.transaction_type] || ''}>{tx.transaction_type}</td>
              <td>{tx.season}</td>
              <td>{tx.team_name}</td>
              <td>{tx.player_name}</td>
              <td>{tx.player_position}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
