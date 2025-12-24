// FreeAgentsContent.tsx - Free agents list (uses shared PlayerView)

import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, Filter } from 'lucide-react';
import { adminApi } from '../../../api/adminClient';
import type { PlayerSummary } from '../../../types/admin';
import { getOverallColor } from '../../../types/admin';
import { PlayerView } from '../components';

// === Position filter options ===
const POSITION_FILTERS = [
  { value: '', label: 'All' },
  { value: 'QB', label: 'QB' },
  { value: 'RB', label: 'RB' },
  { value: 'WR', label: 'WR' },
  { value: 'TE', label: 'TE' },
  { value: 'OL', label: 'OL' },
  { value: 'DL', label: 'DL' },
  { value: 'LB', label: 'LB' },
  { value: 'CB', label: 'CB' },
  { value: 'S', label: 'S' },
];

// === Color Helpers ===
const getAgeColor = (age: number): string => {
  if (age <= 25) return 'var(--success)';
  if (age <= 28) return 'var(--text-secondary)';
  if (age <= 30) return 'var(--accent)';
  return 'var(--danger)';
};

// === View Type ===
type FreeAgentView = { type: 'list' } | { type: 'player'; playerId: string };

// === Main Component ===
interface FreeAgentsContentProps {
  onAddToWorkspace?: (player: { id: string; name: string; position: string; overall: number }) => void;
}

export const FreeAgentsContent: React.FC<FreeAgentsContentProps> = ({ onAddToWorkspace }) => {
  const [players, setPlayers] = useState<PlayerSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [positionFilter, setPositionFilter] = useState('');
  const [minOverall, setMinOverall] = useState<number>(60);
  const [view, setView] = useState<FreeAgentView>({ type: 'list' });

  const loadFreeAgents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminApi.getFreeAgents(
        positionFilter || undefined,
        minOverall || undefined,
        100 // limit
      );
      setPlayers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load free agents');
    } finally {
      setLoading(false);
    }
  }, [positionFilter, minOverall]);

  useEffect(() => {
    loadFreeAgents();
  }, [loadFreeAgents]);

  // Show player detail view using shared component
  if (view.type === 'player') {
    return (
      <PlayerView
        playerId={view.playerId}
        variant="sideview"
        onPopOut={onAddToWorkspace}
        onBack={() => setView({ type: 'list' })}
      />
    );
  }

  if (loading) return null;

  if (error) {
    return (
      <div className="ref-content">
        <div className="ref-content__error">{error}</div>
        <button className="ref-content__retry" onClick={loadFreeAgents}>
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="ref-content">
      {/* Filters */}
      <div className="ref-content__filters">
        <div className="ref-content__filter-group">
          <Filter size={12} />
          <select
            value={positionFilter}
            onChange={(e) => setPositionFilter(e.target.value)}
            className="ref-content__select"
          >
            {POSITION_FILTERS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div className="ref-content__filter-group">
          <span className="ref-content__filter-label">Min:</span>
          <input
            type="number"
            value={minOverall}
            onChange={(e) => setMinOverall(parseInt(e.target.value) || 0)}
            min={0}
            max={99}
            className="ref-content__input ref-content__input--small"
          />
        </div>
      </div>

      {/* Results count */}
      <div className="ref-content__count">
        {players.length} free agent{players.length !== 1 ? 's' : ''}
      </div>

      {/* Player list */}
      {players.length === 0 ? (
        <div className="ref-content__empty">No free agents match filters</div>
      ) : (
        <div className="stat-table stat-table--free-agents">
          <div className="stat-table__header stat-table__header--sticky">
            <span className="stat-table__header-pos">Player</span>
            <span className="stat-table__header-attr">Pos</span>
            <span className="stat-table__header-attr">OVR</span>
            <span className="stat-table__header-attr">POT</span>
            <span className="stat-table__header-attr">Age</span>
          </div>
          {players.map(player => (
            <button
              key={player.id}
              className="stat-table__row"
              onClick={() => setView({ type: 'player', playerId: player.id })}
            >
              <span className="stat-table__name">{player.full_name}</span>
              <span className="stat-table__stat" style={{ color: 'var(--text-secondary)' }}>
                {player.position}
              </span>
              <span className="stat-table__stat" style={{ color: getOverallColor(player.overall) }}>
                {player.overall}
              </span>
              <span className="stat-table__stat" style={{ color: player.potential > player.overall ? 'var(--success)' : 'var(--text-muted)' }}>
                {player.potential}
              </span>
              <span className="stat-table__stat" style={{ color: getAgeColor(player.age) }}>
                {player.age}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default FreeAgentsContent;
