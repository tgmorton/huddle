// ContractsContent.tsx - Full team contracts list with filtering and year-by-year breakdown

import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, ChevronDown, ChevronRight, Filter, ArrowUpDown, ExternalLink } from 'lucide-react';
import { adminApi } from '../../../api/adminClient';
import type { PlayerSummary } from '../../../types/admin';
import { useManagementStore } from '../../../stores/managementStore';
import { getOverallColor } from '../../../types/admin';

// === Helpers ===

const formatSalary = (value: number | null | undefined): string => {
  if (!value) return '—';
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}M`;
  }
  return `$${value}K`;
};

const getYearsColor = (years: number | null | undefined): string => {
  if (!years) return 'var(--text-muted)';
  if (years === 1) return 'var(--danger)';
  if (years === 2) return 'var(--accent)';
  return 'var(--text-secondary)';
};

// Position filter options
const POSITION_FILTERS = [
  { value: '', label: 'All Positions' },
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

const OFFENSE_POSITIONS = ['QB', 'RB', 'FB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT'];
const DEFENSE_POSITIONS = ['DE', 'DT', 'NT', 'MLB', 'ILB', 'OLB', 'CB', 'FS', 'SS'];
const OL_POSITIONS = ['LT', 'LG', 'C', 'RG', 'RT'];
const DL_POSITIONS = ['DE', 'DT', 'NT'];
const DB_POSITIONS = ['CB', 'FS', 'SS'];
const LB_POSITIONS = ['MLB', 'ILB', 'OLB'];

type SortField = 'name' | 'position' | 'overall' | 'salary' | 'years';
type SortDirection = 'asc' | 'desc';

// === Main Component ===

interface ContractsContentProps {
  teamAbbr?: string;
  onPlayerClick?: (playerId: string, playerName: string, position: string, overall: number) => void;
}

export const ContractsContent: React.FC<ContractsContentProps> = ({ teamAbbr: propTeamAbbr, onPlayerClick }) => {
  const [players, setPlayers] = useState<PlayerSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [positionFilter, setPositionFilter] = useState('');
  const [expiringOnly, setExpiringOnly] = useState(false);

  // Sort
  const [sortField, setSortField] = useState<SortField>('salary');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  // Expanded rows
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  // Get team abbr from management store if not provided
  const { state } = useManagementStore();
  const [teamAbbr, setTeamAbbr] = useState<string>(propTeamAbbr || 'BUF');

  const loadContracts = useCallback(async () => {
    if (!teamAbbr) return;

    setLoading(true);
    setError(null);
    try {
      const roster = await adminApi.getTeamRoster(teamAbbr);
      setPlayers(roster);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load contracts');
    } finally {
      setLoading(false);
    }
  }, [teamAbbr]);

  useEffect(() => {
    loadContracts();
  }, [loadContracts]);

  // Try to get team abbr from franchise state
  useEffect(() => {
    if (!propTeamAbbr && state?.player_team_id) {
      adminApi.listTeams().then(teams => {
        const team = teams.find(t => t.id === state.player_team_id);
        if (team) {
          setTeamAbbr(team.abbreviation);
        }
      }).catch(() => {});
    }
  }, [propTeamAbbr, state?.player_team_id]);

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

    // Expiring filter
    if (expiringOnly && (player.contract_year_remaining || 0) > 1) return false;

    return true;
  });

  // Sort players
  const sortedPlayers = [...filteredPlayers].sort((a, b) => {
    let comparison = 0;
    switch (sortField) {
      case 'name':
        comparison = a.full_name.localeCompare(b.full_name);
        break;
      case 'position':
        comparison = a.position.localeCompare(b.position);
        break;
      case 'overall':
        comparison = a.overall - b.overall;
        break;
      case 'salary':
        comparison = (a.salary || 0) - (b.salary || 0);
        break;
      case 'years':
        comparison = (a.contract_year_remaining || 0) - (b.contract_year_remaining || 0);
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

  const toggleRow = (playerId: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(playerId)) {
      newExpanded.delete(playerId);
    } else {
      newExpanded.add(playerId);
    }
    setExpandedRows(newExpanded);
  };

  // Calculate totals
  const totalSalary = sortedPlayers.reduce((sum, p) => sum + (p.salary || 0), 0);
  const expiringCount = sortedPlayers.filter(p => (p.contract_year_remaining || 0) === 1).length;

  if (loading) return null;

  if (error) {
    return (
      <div className="ref-content">
        <div className="ref-content__error">{error}</div>
        <button className="ref-content__retry" onClick={loadContracts}>
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="ref-content contracts-content">
      {/* Summary */}
      <div className="contracts-summary">
        <div className="contracts-summary__item">
          <span className="contracts-summary__label">Contracts</span>
          <span className="contracts-summary__value">{sortedPlayers.length}</span>
        </div>
        <div className="contracts-summary__item">
          <span className="contracts-summary__label">Total</span>
          <span className="contracts-summary__value">{formatSalary(totalSalary)}</span>
        </div>
        <div className="contracts-summary__item">
          <span className="contracts-summary__label">Expiring</span>
          <span className="contracts-summary__value" style={{ color: expiringCount > 0 ? 'var(--accent)' : 'var(--text-muted)' }}>
            {expiringCount}
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="contracts-filters">
        <div className="contracts-filters__group">
          <Filter size={12} />
          <select
            value={positionFilter}
            onChange={(e) => setPositionFilter(e.target.value)}
            className="contracts-filters__select"
          >
            {POSITION_FILTERS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <label className="contracts-filters__checkbox">
          <input
            type="checkbox"
            checked={expiringOnly}
            onChange={(e) => setExpiringOnly(e.target.checked)}
          />
          <span>Expiring only</span>
        </label>
      </div>

      {/* Table */}
      <div className="contracts-table">
        <div className="contracts-table__header">
          <button className="contracts-table__th contracts-table__th--name" onClick={() => handleSort('name')}>
            Player {sortField === 'name' && <ArrowUpDown size={10} />}
          </button>
          <button className="contracts-table__th" onClick={() => handleSort('position')}>
            Pos {sortField === 'position' && <ArrowUpDown size={10} />}
          </button>
          <button className="contracts-table__th" onClick={() => handleSort('overall')}>
            OVR {sortField === 'overall' && <ArrowUpDown size={10} />}
          </button>
          <button className="contracts-table__th" onClick={() => handleSort('salary')}>
            Salary {sortField === 'salary' && <ArrowUpDown size={10} />}
          </button>
          <button className="contracts-table__th" onClick={() => handleSort('years')}>
            Yrs {sortField === 'years' && <ArrowUpDown size={10} />}
          </button>
        </div>

        <div className="contracts-table__body">
          {sortedPlayers.map(player => (
            <div key={player.id} className="contracts-table__row-group">
              <button
                className="contracts-table__row"
                onClick={() => toggleRow(player.id)}
              >
                <span className="contracts-table__name">
                  {expandedRows.has(player.id) ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  {player.full_name}
                </span>
                <span className="contracts-table__cell">{player.position}</span>
                <span className="contracts-table__cell" style={{ color: getOverallColor(player.overall) }}>
                  {player.overall}
                </span>
                <span className="contracts-table__cell contracts-table__cell--mono">
                  {formatSalary(player.salary)}
                </span>
                <span className="contracts-table__cell contracts-table__cell--mono" style={{ color: getYearsColor(player.contract_year_remaining) }}>
                  {player.contract_year_remaining || '—'}
                </span>
              </button>

              {/* Expanded detail */}
              {expandedRows.has(player.id) && (
                <div className="contracts-table__detail">
                  <div className="contracts-detail">
                    <div className="contracts-detail__row">
                      <span className="contracts-detail__label">Annual Salary</span>
                      <span className="contracts-detail__value">{formatSalary(player.salary)}</span>
                    </div>
                    <div className="contracts-detail__row">
                      <span className="contracts-detail__label">Years Remaining</span>
                      <span className="contracts-detail__value">{player.contract_year_remaining || 0}</span>
                    </div>
                    <div className="contracts-detail__row">
                      <span className="contracts-detail__label">Total Remaining</span>
                      <span className="contracts-detail__value">
                        {formatSalary((player.salary || 0) * (player.contract_year_remaining || 0))}
                      </span>
                    </div>
                    <div className="contracts-detail__row">
                      <span className="contracts-detail__label">Age</span>
                      <span className="contracts-detail__value">{player.age}</span>
                    </div>
                    <div className="contracts-detail__row">
                      <span className="contracts-detail__label">Experience</span>
                      <span className="contracts-detail__value">{player.experience} yr{player.experience !== 1 ? 's' : ''}</span>
                    </div>
                  </div>
                  {onPlayerClick && (
                    <button
                      className="contracts-detail__popout"
                      onClick={(e) => {
                        e.stopPropagation();
                        onPlayerClick(player.id, player.full_name, player.position, player.overall);
                      }}
                      title="Open in workspace"
                    >
                      <ExternalLink size={12} />
                      <span>Open</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {sortedPlayers.length === 0 && (
        <div className="contracts-empty">No contracts match filters</div>
      )}
    </div>
  );
};

export default ContractsContent;
