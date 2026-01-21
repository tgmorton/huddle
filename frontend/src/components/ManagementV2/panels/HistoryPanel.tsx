// HistoryPanel.tsx - Historical simulation data: Standings, Drafts, Transactions

import React, { useState, useEffect } from 'react';
import { History, Trophy, Users, ArrowLeftRight, Loader2 } from 'lucide-react';
import { useManagementStore, selectSimId } from '../../../stores/managementStore';
import {
  getStandings,
  getDraft,
  getTransactions,
  type StandingsData,
  type DraftData,
  type TransactionLog,
} from '../../../api/historyClient';

type HistoryTab = 'standings' | 'drafts' | 'transactions';

// ============================================================================
// Sub-components for each tab
// ============================================================================

const StandingsTab: React.FC<{ simId: string; season: number }> = ({ simId, season }) => {
  const [data, setData] = useState<StandingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedSeason, setSelectedSeason] = useState(season);

  useEffect(() => {
    setLoading(true);
    getStandings(simId, selectedSeason)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [simId, selectedSeason]);

  if (loading) {
    return (
      <div className="history-panel__loading">
        <Loader2 size={16} className="spinning" />
        Loading standings...
      </div>
    );
  }

  if (!data) return <div className="history-panel__empty">No standings data available</div>;

  return (
    <div className="history-panel__standings">
      <div className="history-panel__season-select">
        <label>Season:</label>
        <select value={selectedSeason} onChange={(e) => setSelectedSeason(Number(e.target.value))}>
          {Array.from({ length: 5 }, (_, i) => season - i).map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>
      <table className="history-panel__table">
        <thead>
          <tr>
            <th>#</th>
            <th>Team</th>
            <th>W</th>
            <th>L</th>
            <th>Pct</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {data.teams.map((team, i) => (
            <tr key={team.team_id}>
              <td>{i + 1}</td>
              <td>{team.team_name}</td>
              <td>{team.wins}</td>
              <td>{team.losses}</td>
              <td>{team.win_pct.toFixed(3)}</td>
              <td className="history-panel__status">{team.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const DraftsTab: React.FC<{ simId: string; season: number }> = ({ simId, season }) => {
  const [data, setData] = useState<DraftData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedSeason, setSelectedSeason] = useState(season);

  useEffect(() => {
    setLoading(true);
    getDraft(simId, selectedSeason)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [simId, selectedSeason]);

  if (loading) {
    return (
      <div className="history-panel__loading">
        <Loader2 size={16} className="spinning" />
        Loading draft data...
      </div>
    );
  }

  if (!data) return <div className="history-panel__empty">No draft data available</div>;

  return (
    <div className="history-panel__drafts">
      <div className="history-panel__season-select">
        <label>Season:</label>
        <select value={selectedSeason} onChange={(e) => setSelectedSeason(Number(e.target.value))}>
          {Array.from({ length: 5 }, (_, i) => season - i).map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>
      <table className="history-panel__table">
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
          {data.picks.slice(0, 50).map((pick) => (
            <tr key={`${pick.round}-${pick.pick}`}>
              <td>R{pick.round} P{pick.pick}</td>
              <td>{pick.team_name}</td>
              <td>{pick.player_name}</td>
              <td>{pick.position}</td>
              <td>{pick.overall_rating}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const TransactionsTab: React.FC<{ simId: string; season: number }> = ({ simId, season }) => {
  const [data, setData] = useState<TransactionLog | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedSeason, setSelectedSeason] = useState<number | undefined>(undefined);
  const [selectedType, setSelectedType] = useState<string | undefined>(undefined);

  useEffect(() => {
    setLoading(true);
    getTransactions(simId, {
      season: selectedSeason,
      transaction_type: selectedType,
      limit: 100,
    })
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [simId, selectedSeason, selectedType]);

  if (loading) {
    return (
      <div className="history-panel__loading">
        <Loader2 size={16} className="spinning" />
        Loading transactions...
      </div>
    );
  }

  if (!data) return <div className="history-panel__empty">No transaction data available</div>;

  return (
    <div className="history-panel__transactions">
      <div className="history-panel__filters">
        <div className="history-panel__season-select">
          <label>Season:</label>
          <select
            value={selectedSeason ?? 'all'}
            onChange={(e) => setSelectedSeason(e.target.value === 'all' ? undefined : Number(e.target.value))}
          >
            <option value="all">All</option>
            {Array.from({ length: 5 }, (_, i) => season - i).map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
        <div className="history-panel__type-select">
          <label>Type:</label>
          <select
            value={selectedType ?? 'all'}
            onChange={(e) => setSelectedType(e.target.value === 'all' ? undefined : e.target.value)}
          >
            <option value="all">All</option>
            <option value="DRAFT">Draft</option>
            <option value="SIGNING">Signing</option>
            <option value="CUT">Cut</option>
            <option value="TRADE">Trade</option>
          </select>
        </div>
      </div>
      <table className="history-panel__table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Type</th>
            <th>Team</th>
            <th>Player</th>
            <th>Pos</th>
          </tr>
        </thead>
        <tbody>
          {data.transactions.map((tx) => (
            <tr key={tx.id}>
              <td>{tx.season}</td>
              <td className={`history-panel__tx-type history-panel__tx-type--${tx.transaction_type.toLowerCase()}`}>
                {tx.transaction_type}
              </td>
              <td>{tx.team_name}</td>
              <td>{tx.player_name}</td>
              <td>{tx.player_position}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="history-panel__count">{data.total_count} total transactions</div>
    </div>
  );
};

// ============================================================================
// Main HistoryPanel
// ============================================================================

export const HistoryPanel: React.FC = () => {
  const [tab, setTab] = useState<HistoryTab>('standings');
  const simId = useManagementStore(selectSimId);

  // Get current season from state if available, otherwise use a default
  const state = useManagementStore((s) => s.state);
  const currentSeason = state?.calendar?.season_year ?? 2024;

  if (!simId) {
    return (
      <div className="history-panel history-panel--empty">
        <div className="history-panel__no-sim">
          <History size={32} />
          <h3>No Historical Data</h3>
          <p>Start from a historical simulation to view league history.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="history-panel">
      <div className="tabbed-panel__tabs">
        <button
          className={`tabbed-panel__tab ${tab === 'standings' ? 'tabbed-panel__tab--active' : ''}`}
          onClick={() => setTab('standings')}
        >
          <Trophy size={12} />
          Standings
        </button>
        <button
          className={`tabbed-panel__tab ${tab === 'drafts' ? 'tabbed-panel__tab--active' : ''}`}
          onClick={() => setTab('drafts')}
        >
          <Users size={12} />
          Drafts
        </button>
        <button
          className={`tabbed-panel__tab ${tab === 'transactions' ? 'tabbed-panel__tab--active' : ''}`}
          onClick={() => setTab('transactions')}
        >
          <ArrowLeftRight size={12} />
          Transactions
        </button>
      </div>
      <div className="tabbed-panel__content">
        {tab === 'standings' && <StandingsTab simId={simId} season={currentSeason} />}
        {tab === 'drafts' && <DraftsTab simId={simId} season={currentSeason} />}
        {tab === 'transactions' && <TransactionsTab simId={simId} season={currentSeason} />}
      </div>
    </div>
  );
};

export default HistoryPanel;
