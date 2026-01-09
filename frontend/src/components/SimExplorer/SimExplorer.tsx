/**
 * SimExplorer - Historical Simulation Explorer
 *
 * Allows exploring simulated league history:
 * - Generate new simulations
 * - Browse teams, rosters, standings
 * - View draft results and transactions
 * - Analyze AI decision-making (GM archetypes, cap allocation, FA strategy)
 */

import { useEffect, useState } from 'react';
import { useSimExplorerStore } from '../../stores/simExplorerStore';
import type { ViewMode } from '../../stores/simExplorerStore';
import * as historyClient from '../../api/historyClient';
import './SimExplorer.css';

// GM Archetype colors and labels
const GM_ARCHETYPE_STYLES: Record<string, { color: string; label: string }> = {
  analytics: { color: '#3b82f6', label: 'Analytics' },
  old_school: { color: '#f59e0b', label: 'Old School' },
  cap_wizard: { color: '#10b981', label: 'Cap Wizard' },
  win_now: { color: '#ef4444', label: 'Win Now' },
  balanced: { color: '#6b7280', label: 'Balanced' },
};

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
                  .map((team) => {
                    const gmStyle = GM_ARCHETYPE_STYLES[team.gm_archetype || 'balanced'];
                    return (
                      <li
                        key={team.team_id}
                        className={selectedTeamId === team.team_id ? 'selected' : ''}
                        onClick={() => selectTeam(team.team_id)}
                      >
                        <span className="team-name">{team.team_name}</span>
                        <span className="team-record">
                          {team.wins}-{team.losses}
                        </span>
                        {team.gm_archetype && (
                          <span
                            className="gm-badge"
                            style={{ backgroundColor: gmStyle.color }}
                            title={gmStyle.label}
                          >
                            {gmStyle.label.charAt(0)}
                          </span>
                        )}
                        <span className={`team-status status-${team.status.toLowerCase()}`}>
                          {team.status}
                        </span>
                      </li>
                    );
                  })}
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
                {(['overview', 'standings', 'roster', 'draft', 'transactions', 'profile', 'strategy'] as ViewMode[]).map(
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

                {viewMode === 'overview' && (
                  <OverviewView
                    simulation={currentSimulation}
                    standings={standings}
                    selectedSeason={selectedSeason}
                  />
                )}
                {viewMode === 'standings' && standings && <StandingsView standings={standings} />}
                {viewMode === 'roster' && selectedRoster && <RosterView roster={selectedRoster} />}
                {viewMode === 'roster' && !selectedRoster && (
                  <div className="empty-view">Select a team to view roster</div>
                )}
                {viewMode === 'draft' && draft && <DraftView draft={draft} />}
                {viewMode === 'transactions' && transactions && (
                  <TransactionsView transactions={transactions} />
                )}
                {viewMode === 'profile' && selectedTeamId && currentSimulation && selectedSeason && (
                  <TeamProfileView
                    simId={currentSimulation.sim_id}
                    teamId={selectedTeamId}
                    season={selectedSeason}
                  />
                )}
                {viewMode === 'profile' && !selectedTeamId && (
                  <div className="empty-view">Select a team to view profile</div>
                )}
                {viewMode === 'strategy' && selectedTeamId && currentSimulation && selectedSeason && (
                  <StrategyView
                    simId={currentSimulation.sim_id}
                    teamId={selectedTeamId}
                    season={selectedSeason}
                  />
                )}
                {viewMode === 'strategy' && !selectedTeamId && currentSimulation && selectedSeason && (
                  <GMComparisonView
                    simId={currentSimulation.sim_id}
                    season={selectedSeason}
                  />
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

function OverviewView({
  simulation,
  standings,
  selectedSeason,
}: {
  simulation: import('../../api/historyClient').FullSimulationData;
  standings: import('../../api/historyClient').StandingsData | null;
  selectedSeason: number | null;
}) {
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
          <span className="stat-label">Viewing</span>
          <span className="stat-value">{selectedSeason ?? '-'}</span>
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
            <tr key={season.season} className={season.season === selectedSeason ? 'selected-row' : ''}>
              <td>{season.season}</td>
              <td>{season.total_transactions}</td>
              <td>{season.draft_picks}</td>
              <td>{season.avg_cap_usage.toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>{selectedSeason} Standings</h3>
      {standings ? (
        <table className="data-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Team</th>
              <th>Record</th>
              <th>Win%</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {standings.teams.map((team) => (
              <tr key={team.team_id}>
                <td>{team.rank}</td>
                <td>{team.team_name}</td>
                <td>
                  {team.wins}-{team.losses}
                </td>
                <td>{(team.win_pct * 100).toFixed(1)}%</td>
                <td className={`status-${team.status.toLowerCase()}`}>{team.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty-state">Loading standings...</p>
      )}
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
      <p className="view-description">
        Position Value: Research-backed draft value (1.0 = best to draft, 0.1 = sign in FA).
        GM Adj: Archetype modifier.
      </p>
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
              <th>Pos Value</th>
              <th>GM Adj</th>
              <th>Draft?</th>
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
                <td className={pick.position_value && pick.position_value >= 0.5 ? 'value-high' : 'value-low'}>
                  {pick.position_value?.toFixed(2) ?? '-'}
                </td>
                <td className={pick.gm_adjustment && pick.gm_adjustment > 0 ? 'adj-positive' : pick.gm_adjustment && pick.gm_adjustment < 0 ? 'adj-negative' : ''}>
                  {pick.gm_adjustment ? (pick.gm_adjustment > 0 ? '+' : '') + pick.gm_adjustment.toFixed(2) : '-'}
                </td>
                <td>
                  {pick.is_draft_priority !== undefined && (
                    <span className={pick.is_draft_priority ? 'priority-yes' : 'priority-no'}>
                      {pick.is_draft_priority ? '✓' : '✗'}
                    </span>
                  )}
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


// =============================================================================
// New AI Visibility Views
// =============================================================================

function TeamProfileView({ simId, teamId, season }: { simId: string; teamId: string; season: number }) {
  const [profile, setProfile] = useState<historyClient.TeamProfile | null>(null);
  const [allocation, setAllocation] = useState<historyClient.CapAllocationData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      historyClient.getTeamProfile(simId, teamId, season),
      historyClient.getTeamAllocation(simId, teamId, season),
    ])
      .then(([p, a]) => {
        setProfile(p);
        setAllocation(a);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [simId, teamId, season]);

  if (loading) return <div className="loading">Loading profile...</div>;
  if (!profile) return <div className="empty-state">No profile data available</div>;

  const gmStyle = GM_ARCHETYPE_STYLES[profile.gm_archetype] || GM_ARCHETYPE_STYLES.balanced;

  return (
    <div className="profile-view">
      <div className="profile-header">
        <h3>{profile.team_name}</h3>
        <span className="gm-badge-large" style={{ backgroundColor: gmStyle.color }}>
          {gmStyle.label} GM
        </span>
      </div>

      <div className="profile-section">
        <h4>GM Philosophy</h4>
        <p className="gm-description">{profile.gm_description}</p>
        <div className="profile-stats">
          <div className="stat">
            <span className="stat-label">Rookie Premium</span>
            <span className="stat-value">{profile.rookie_premium}x</span>
          </div>
          <div className="stat">
            <span className="stat-label">Draft Philosophy</span>
            <span className="stat-value">{profile.draft_philosophy.replace('_', ' ')}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Spending Style</span>
            <span className="stat-value">{profile.spending_style}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Status</span>
            <span className="stat-value">{profile.status}</span>
          </div>
        </div>
      </div>

      {Object.keys(profile.position_preferences).length > 0 && (
        <div className="profile-section">
          <h4>Position Preferences</h4>
          <div className="position-prefs">
            {Object.entries(profile.position_preferences)
              .sort((a, b) => b[1] - a[1])
              .map(([pos, adj]) => (
                <span
                  key={pos}
                  className={`pref-badge ${adj > 1 ? 'pref-high' : adj < 1 ? 'pref-low' : ''}`}
                >
                  {pos}: {adj > 1 ? '+' : ''}{((adj - 1) * 100).toFixed(0)}%
                </span>
              ))}
          </div>
        </div>
      )}

      {allocation && (
        <div className="profile-section">
          <h4>Cap Allocation vs Optimal</h4>
          <p className="section-description">
            Gap: positive = under-invested, negative = over-invested
          </p>
          <div className="allocation-grid">
            <div className="allocation-side">
              <h5>Offense</h5>
              {allocation.offense_allocation.map((pos) => (
                <div key={pos.position} className="allocation-row">
                  <span className="pos-name">{pos.position}</span>
                  <div className="allocation-bar-container">
                    <div
                      className="allocation-bar actual"
                      style={{ width: `${Math.min(100, pos.actual_pct * 3)}%` }}
                    />
                    <div
                      className="allocation-bar target"
                      style={{ width: `${Math.min(100, pos.target_pct * 3)}%` }}
                    />
                  </div>
                  <span className={`gap ${pos.gap > 0 ? 'gap-under' : pos.gap < 0 ? 'gap-over' : ''}`}>
                    {pos.gap > 0 ? '+' : ''}{pos.gap.toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
            <div className="allocation-side">
              <h5>Defense</h5>
              {allocation.defense_allocation.map((pos) => (
                <div key={pos.position} className="allocation-row">
                  <span className="pos-name">{pos.position}</span>
                  <div className="allocation-bar-container">
                    <div
                      className="allocation-bar actual"
                      style={{ width: `${Math.min(100, pos.actual_pct * 3)}%` }}
                    />
                    <div
                      className="allocation-bar target"
                      style={{ width: `${Math.min(100, pos.target_pct * 3)}%` }}
                    />
                  </div>
                  <span className={`gap ${pos.gap > 0 ? 'gap-under' : pos.gap < 0 ? 'gap-over' : ''}`}>
                    {pos.gap > 0 ? '+' : ''}{pos.gap.toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="allocation-legend">
            <span><span className="legend-actual" /> Actual</span>
            <span><span className="legend-target" /> Target</span>
          </div>
        </div>
      )}
    </div>
  );
}

function StrategyView({ simId, teamId, season }: { simId: string; teamId: string; season: number }) {
  const [rosterPlan, setRosterPlan] = useState<historyClient.RosterPlan | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    historyClient.getRosterPlan(simId, teamId, season)
      .then(setRosterPlan)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [simId, teamId, season]);

  if (loading) return <div className="loading">Loading roster plan...</div>;
  if (!rosterPlan) return <div className="empty-state">No roster plan data available</div>;

  const formatMoney = (k: number) => `$${(k / 1000).toFixed(1)}M`;
  const gmStyle = GM_ARCHETYPE_STYLES[rosterPlan.gm_archetype] || GM_ARCHETYPE_STYLES.balanced;

  const renderPositionPlan = (plan: historyClient.PositionPlan) => (
    <div key={plan.position} className="position-plan">
      <div className="position-plan-header">
        <span className="position-name">{plan.position}</span>
        <span className={`need-level need-${plan.need_level > 0.7 ? 'high' : plan.need_level > 0.4 ? 'medium' : 'low'}`}>
          {(plan.need_level * 100).toFixed(0)}% need
        </span>
        <span className={`research-rec rec-${plan.research_recommendation === 'Draft' ? 'draft' : 'fa'}`}>
          {plan.research_recommendation}
        </span>
      </div>
      <div className="position-plan-reason">{plan.need_reason}</div>
      {plan.current_starter && (
        <div className="current-starter">
          Current: {plan.current_starter} ({plan.current_overall} OVR, age {plan.current_age})
          {plan.current_contract_years && <span className="contract-years">{plan.current_contract_years}yr left</span>}
        </div>
      )}
      <div className="position-options">
        {plan.options.map((opt, idx) => (
          <div key={idx} className={`option-row option-${opt.option_type.toLowerCase()}`}>
            <div className="option-prob">
              <span className="prob-bar" style={{ width: `${opt.probability}%` }} />
              <span className="prob-text">{opt.probability.toFixed(0)}%</span>
            </div>
            <div className="option-info">
              <span className="option-name">{opt.player_name}</span>
              <span className="option-details">
                {opt.overall} OVR, {opt.age}yo
                {opt.projected_cost && ` - ${formatMoney(opt.projected_cost)}/yr`}
              </span>
            </div>
            <span className={`option-type type-${opt.option_type.toLowerCase()}`}>
              {opt.option_type}
            </span>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="strategy-view roster-plan-view">
      <div className="strategy-header">
        <h3>{rosterPlan.team_name} Roster Plan ({season})</h3>
        <span className="gm-badge-large" style={{ backgroundColor: gmStyle.color }}>
          {gmStyle.label} GM
        </span>
      </div>

      <div className="roster-plan-summary">
        <div className="summary-stat">
          <span className="stat-label">Cap Space</span>
          <span className="stat-value">{formatMoney(rosterPlan.cap_space)}</span>
        </div>
        <div className="summary-stat">
          <span className="stat-label">Total Needs</span>
          <span className="stat-value">{rosterPlan.total_needs}</span>
        </div>
        <div className="summary-stat">
          <span className="stat-label">FA Targets</span>
          <span className="stat-value">{rosterPlan.fa_targets}</span>
        </div>
        <div className="summary-stat">
          <span className="stat-label">Draft Targets</span>
          <span className="stat-value">{rosterPlan.draft_targets}</span>
        </div>
      </div>

      <div className="draft-picks-info">
        <h4>Draft Capital</h4>
        <div className="picks-list">
          {rosterPlan.draft_picks.map((pick, idx) => (
            <span key={idx} className="pick-badge">{pick}</span>
          ))}
        </div>
      </div>

      <div className="position-plans-grid">
        <div className="plans-column">
          <h4>Offense</h4>
          {rosterPlan.offense_plans.map(renderPositionPlan)}
        </div>
        <div className="plans-column">
          <h4>Defense</h4>
          {rosterPlan.defense_plans.map(renderPositionPlan)}
        </div>
      </div>
    </div>
  );
}

function GMComparisonView({ simId, season }: { simId: string; season: number }) {
  const [comparison, setComparison] = useState<historyClient.GMComparisonData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    historyClient.getGMComparison(simId, season)
      .then(setComparison)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [simId, season]);

  if (loading) return <div className="loading">Loading comparison...</div>;
  if (!comparison) return <div className="empty-state">No comparison data available</div>;

  return (
    <div className="gm-comparison-view">
      <h3>GM Archetype Performance ({season})</h3>
      <p className="view-description">
        Compare how different GM philosophies performed this season.
        Select a team to see detailed strategy.
      </p>

      <table className="data-table comparison-table">
        <thead>
          <tr>
            <th>Archetype</th>
            <th>Teams</th>
            <th>Avg Wins</th>
            <th>Win %</th>
            <th>Playoffs</th>
            <th>Champs</th>
          </tr>
        </thead>
        <tbody>
          {comparison.archetypes.map((entry) => {
            const style = GM_ARCHETYPE_STYLES[entry.archetype] || GM_ARCHETYPE_STYLES.balanced;
            return (
              <tr key={entry.archetype}>
                <td>
                  <span className="gm-badge" style={{ backgroundColor: style.color }}>
                    {style.label}
                  </span>
                </td>
                <td>{entry.team_count}</td>
                <td>{entry.avg_wins.toFixed(1)}</td>
                <td>{(entry.avg_win_pct * 100).toFixed(1)}%</td>
                <td>{entry.playoffs_made}</td>
                <td>{entry.championships}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
