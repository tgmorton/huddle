// FreeAgentsContent.tsx - Free agents list with tier badges, market values, and offer actions

import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, Filter, DollarSign, TrendingUp, Star, Users, ArrowUpDown, Gavel } from 'lucide-react';
import { managementApi } from '../../../api/managementClient';
import type { FreeAgentInfo } from '../../../api/managementClient';
import { useManagementStore, selectFranchiseId } from '../../../stores/managementStore';
import { getOverallColor } from '../../../types/admin';
import { PlayerView } from '../components';

// === Position filter options ===
const POSITION_FILTERS = [
  { value: '', label: 'All' },
  { value: 'OFF', label: 'Offense' },
  { value: 'DEF', label: 'Defense' },
  { value: 'QB', label: 'QB' },
  { value: 'RB', label: 'RB' },
  { value: 'WR', label: 'WR' },
  { value: 'TE', label: 'TE' },
  { value: 'OL', label: 'O-Line' },
  { value: 'DL', label: 'D-Line' },
  { value: 'LB', label: 'LB' },
  { value: 'DB', label: 'Secondary' },
];

const TIER_FILTERS = [
  { value: '', label: 'All Tiers' },
  { value: 'ELITE', label: 'Elite' },
  { value: 'STARTER', label: 'Starter' },
  { value: 'DEPTH', label: 'Depth' },
  { value: 'MINIMUM', label: 'Minimum' },
];

// Position group mappings
const OFFENSE_POSITIONS = ['QB', 'RB', 'FB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT', 'OL'];
const DEFENSE_POSITIONS = ['DE', 'DT', 'NT', 'MLB', 'ILB', 'OLB', 'CB', 'FS', 'SS', 'DL', 'LB', 'DB'];
const OL_POSITIONS = ['LT', 'LG', 'C', 'RG', 'RT'];
const DL_POSITIONS = ['DE', 'DT', 'NT'];
const DB_POSITIONS = ['CB', 'FS', 'SS'];
const LB_POSITIONS = ['MLB', 'ILB', 'OLB'];

// === Color Helpers ===
const getAgeColor = (age: number): string => {
  if (age <= 25) return 'var(--success)';
  if (age <= 28) return 'var(--text-secondary)';
  if (age <= 30) return 'var(--accent)';
  return 'var(--danger)';
};

const getTierColor = (tier: string): string => {
  switch (tier) {
    case 'ELITE': return 'var(--elite)';
    case 'STARTER': return 'var(--success)';
    case 'DEPTH': return 'var(--accent)';
    case 'MINIMUM': return 'var(--text-muted)';
    default: return 'var(--text-secondary)';
  }
};

const getTierIcon = (tier: string) => {
  switch (tier) {
    case 'ELITE': return Star;
    case 'STARTER': return TrendingUp;
    case 'DEPTH': return Users;
    default: return null;
  }
};

const formatSalary = (value: number): string => {
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}M`;
  }
  return `$${value}K`;
};

// === Sort Types ===
type SortField = 'name' | 'position' | 'overall' | 'age' | 'tier' | 'market_value';
type SortDirection = 'asc' | 'desc';

const TIER_ORDER: Record<string, number> = {
  'ELITE': 0,
  'STARTER': 1,
  'DEPTH': 2,
  'MINIMUM': 3,
};

// === View Type ===
type FreeAgentView = { type: 'list' } | { type: 'player'; playerId: string };

// === Main Component ===
interface FreeAgentsContentProps {
  onAddToWorkspace?: (player: { id: string; name: string; position: string; overall: number }) => void;
  onStartNegotiation?: (player: FreeAgentInfo) => void;
  onStartAuction?: (player: FreeAgentInfo) => void;
}

export const FreeAgentsContent: React.FC<FreeAgentsContentProps> = ({ onAddToWorkspace, onStartNegotiation, onStartAuction }) => {
  const franchiseId = useManagementStore(selectFranchiseId);
  const [players, setPlayers] = useState<FreeAgentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [positionFilter, setPositionFilter] = useState('');
  const [tierFilter, setTierFilter] = useState('');
  const [view, setView] = useState<FreeAgentView>({ type: 'list' });

  // Sort state
  const [sortField, setSortField] = useState<SortField>('overall');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const loadFreeAgents = useCallback(async () => {
    if (!franchiseId) return;

    setLoading(true);
    setError(null);
    try {
      const data = await managementApi.getFreeAgents(franchiseId);
      setPlayers(data.free_agents);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load free agents');
    } finally {
      setLoading(false);
    }
  }, [franchiseId]);

  useEffect(() => {
    loadFreeAgents();
  }, [loadFreeAgents]);

  // Filter players
  const filteredPlayers = players.filter(player => {
    // Position filter
    if (positionFilter) {
      if (positionFilter === 'OFF' && !OFFENSE_POSITIONS.includes(player.position)) return false;
      if (positionFilter === 'DEF' && !DEFENSE_POSITIONS.includes(player.position)) return false;
      if (positionFilter === 'OL' && !OL_POSITIONS.includes(player.position)) return false;
      if (positionFilter === 'DL' && !DL_POSITIONS.includes(player.position)) return false;
      if (positionFilter === 'DB' && !DB_POSITIONS.includes(player.position)) return false;
      if (positionFilter === 'LB' && !LB_POSITIONS.includes(player.position)) return false;
      if (!['OFF', 'DEF', 'OL', 'DL', 'DB', 'LB'].includes(positionFilter) && player.position !== positionFilter) return false;
    }

    // Tier filter
    if (tierFilter && player.tier !== tierFilter) return false;

    return true;
  });

  // Sort players
  const sortedPlayers = [...filteredPlayers].sort((a, b) => {
    let comparison = 0;
    switch (sortField) {
      case 'name':
        comparison = a.name.localeCompare(b.name);
        break;
      case 'position':
        comparison = a.position.localeCompare(b.position);
        break;
      case 'overall':
        comparison = a.overall - b.overall;
        break;
      case 'age':
        comparison = a.age - b.age;
        break;
      case 'tier':
        comparison = TIER_ORDER[a.tier] - TIER_ORDER[b.tier];
        break;
      case 'market_value':
        comparison = a.market_value - b.market_value;
        break;
    }
    return sortDirection === 'asc' ? comparison : -comparison;
  });

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Calculate summary stats
  const tierCounts = {
    ELITE: players.filter(p => p.tier === 'ELITE').length,
    STARTER: players.filter(p => p.tier === 'STARTER').length,
    DEPTH: players.filter(p => p.tier === 'DEPTH').length,
    MINIMUM: players.filter(p => p.tier === 'MINIMUM').length,
  };

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

  if (!franchiseId) {
    return (
      <div className="ref-content">
        <div className="ref-content__empty">Load a franchise to view free agents</div>
      </div>
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
    <div className="ref-content free-agents-content">
      {/* Summary badges */}
      <div className="free-agents-summary">
        <div className="free-agents-summary__total">
          <span className="free-agents-summary__count">{players.length}</span>
          <span className="free-agents-summary__label">Free Agents</span>
        </div>
        <div className="free-agents-summary__tiers">
          {tierCounts.ELITE > 0 && (
            <button
              className={`free-agents-tier-badge free-agents-tier-badge--elite ${tierFilter === 'ELITE' ? 'active' : ''}`}
              onClick={() => setTierFilter(tierFilter === 'ELITE' ? '' : 'ELITE')}
            >
              <Star size={10} />
              <span>{tierCounts.ELITE}</span>
            </button>
          )}
          <button
            className={`free-agents-tier-badge free-agents-tier-badge--starter ${tierFilter === 'STARTER' ? 'active' : ''}`}
            onClick={() => setTierFilter(tierFilter === 'STARTER' ? '' : 'STARTER')}
          >
            <TrendingUp size={10} />
            <span>{tierCounts.STARTER}</span>
          </button>
          <button
            className={`free-agents-tier-badge free-agents-tier-badge--depth ${tierFilter === 'DEPTH' ? 'active' : ''}`}
            onClick={() => setTierFilter(tierFilter === 'DEPTH' ? '' : 'DEPTH')}
          >
            <span>{tierCounts.DEPTH}</span>
          </button>
          <button
            className={`free-agents-tier-badge free-agents-tier-badge--minimum ${tierFilter === 'MINIMUM' ? 'active' : ''}`}
            onClick={() => setTierFilter(tierFilter === 'MINIMUM' ? '' : 'MINIMUM')}
          >
            <span>{tierCounts.MINIMUM}</span>
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="free-agents-filters">
        <div className="free-agents-filters__group">
          <Filter size={12} />
          <select
            value={positionFilter}
            onChange={(e) => setPositionFilter(e.target.value)}
            className="free-agents-filters__select"
          >
            {POSITION_FILTERS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div className="free-agents-filters__group">
          <select
            value={tierFilter}
            onChange={(e) => setTierFilter(e.target.value)}
            className="free-agents-filters__select"
          >
            {TIER_FILTERS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Results count */}
      <div className="free-agents-count">
        Showing {sortedPlayers.length} of {players.length}
      </div>

      {/* Player table */}
      {sortedPlayers.length === 0 ? (
        <div className="ref-content__empty">No free agents match filters</div>
      ) : (
        <div className="free-agents-table">
          <div className="free-agents-table__header">
            <button className="free-agents-table__th free-agents-table__th--name" onClick={() => handleSort('name')}>
              Player {sortField === 'name' && <ArrowUpDown size={10} />}
            </button>
            <button className="free-agents-table__th" onClick={() => handleSort('position')}>
              Pos {sortField === 'position' && <ArrowUpDown size={10} />}
            </button>
            <button className="free-agents-table__th" onClick={() => handleSort('overall')}>
              OVR {sortField === 'overall' && <ArrowUpDown size={10} />}
            </button>
            <button className="free-agents-table__th" onClick={() => handleSort('age')}>
              Age {sortField === 'age' && <ArrowUpDown size={10} />}
            </button>
            <button className="free-agents-table__th" onClick={() => handleSort('market_value')}>
              Value {sortField === 'market_value' && <ArrowUpDown size={10} />}
            </button>
            <span className="free-agents-table__th free-agents-table__th--action"></span>
          </div>

          <div className="free-agents-table__body">
            {sortedPlayers.map(player => {
              const TierIcon = getTierIcon(player.tier);
              return (
                <div key={player.player_id} className="free-agents-table__row-wrapper">
                  <button
                    className="free-agents-table__row"
                    onClick={() => setView({ type: 'player', playerId: player.player_id })}
                  >
                    <span className="free-agents-table__name">
                      <span
                        className="free-agents-table__tier-dot"
                        style={{ background: getTierColor(player.tier) }}
                        title={player.tier}
                      />
                      {player.name}
                      {TierIcon && player.tier === 'ELITE' && (
                        <TierIcon size={12} className="free-agents-table__tier-icon" style={{ color: getTierColor(player.tier) }} />
                      )}
                    </span>
                    <span className="free-agents-table__cell">{player.position}</span>
                    <span className="free-agents-table__cell" style={{ color: getOverallColor(player.overall) }}>
                      {player.overall}
                    </span>
                    <span className="free-agents-table__cell" style={{ color: getAgeColor(player.age) }}>
                      {player.age}
                    </span>
                    <span className="free-agents-table__cell free-agents-table__cell--value">
                      {formatSalary(player.market_value)}
                    </span>
                  </button>
                  {/* Elite/Starter tier = auction, others = direct negotiation */}
                  {(player.tier === 'ELITE' || player.tier === 'STARTER') ? (
                    <button
                      className="free-agents-table__offer-btn free-agents-table__offer-btn--auction"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (onStartAuction) {
                          onStartAuction(player);
                        }
                      }}
                      title="Start Auction"
                    >
                      <Gavel size={14} />
                    </button>
                  ) : (
                    <button
                      className="free-agents-table__offer-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (onStartNegotiation) {
                          onStartNegotiation(player);
                        }
                      }}
                      title="Make Offer"
                    >
                      <DollarSign size={14} />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default FreeAgentsContent;
