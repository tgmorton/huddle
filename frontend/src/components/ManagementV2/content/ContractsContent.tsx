// ContractsContent.tsx - Full team contracts list with filtering and year-by-year breakdown

import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, ChevronDown, ChevronRight, Filter, ArrowUpDown, ExternalLink, AlertTriangle, Scissors, DollarSign, X } from 'lucide-react';
import { managementApi } from '../../../api/managementClient';
import type { PlayerContractInfo, RestructureContractResponse, CutPlayerResponse } from '../../../api/managementClient';
import { useManagementStore, selectFranchiseId } from '../../../stores/managementStore';
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
  onPlayerClick?: (playerId: string, playerName: string, position: string, overall: number) => void;
  onContractClick?: (playerId: string, playerName: string, position: string, salary: number) => void;
}

export const ContractsContent: React.FC<ContractsContentProps> = ({ onPlayerClick, onContractClick }) => {
  const franchiseId = useManagementStore(selectFranchiseId);
  const [contracts, setContracts] = useState<PlayerContractInfo[]>([]);
  const [totalSalary, setTotalSalary] = useState(0);
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

  // Modal state
  const [restructureTarget, setRestructureTarget] = useState<PlayerContractInfo | null>(null);
  const [cutTarget, setCutTarget] = useState<PlayerContractInfo | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionResult, setActionResult] = useState<{ type: 'restructure' | 'cut'; result: RestructureContractResponse | CutPlayerResponse } | null>(null);

  const loadContracts = useCallback(async () => {
    if (!franchiseId) return;

    setLoading(true);
    setError(null);
    try {
      const data = await managementApi.getContracts(franchiseId);
      setContracts(data.contracts);
      setTotalSalary(data.total_salary);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load contracts');
    } finally {
      setLoading(false);
    }
  }, [franchiseId]);

  useEffect(() => {
    loadContracts();
  }, [loadContracts]);

  // Filter contracts
  const filteredContracts = contracts.filter(contract => {
    // Position filter
    if (positionFilter) {
      if (positionFilter === 'OFF' && !OFFENSE_POSITIONS.includes(contract.position)) return false;
      if (positionFilter === 'DEF' && !DEFENSE_POSITIONS.includes(contract.position)) return false;
      if (positionFilter === 'OL' && !OL_POSITIONS.includes(contract.position)) return false;
      if (positionFilter === 'DL' && !DL_POSITIONS.includes(contract.position)) return false;
      if (positionFilter === 'DB' && !DB_POSITIONS.includes(contract.position)) return false;
      if (positionFilter === 'LB' && !LB_POSITIONS.includes(contract.position)) return false;
      if (!['OFF', 'DEF', 'OL', 'DL', 'DB', 'LB'].includes(positionFilter) && contract.position !== positionFilter) return false;
    }

    // Expiring filter
    if (expiringOnly && contract.years_remaining > 1) return false;

    return true;
  });

  // Sort contracts
  const sortedContracts = [...filteredContracts].sort((a, b) => {
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
      case 'salary':
        comparison = a.salary - b.salary;
        break;
      case 'years':
        comparison = a.years_remaining - b.years_remaining;
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

  // Contract action handlers
  const handleRestructure = async (playerId: string, amount: number) => {
    if (!franchiseId) return;
    setActionLoading(true);
    try {
      const result = await managementApi.restructureContract(franchiseId, playerId, amount);
      setActionResult({ type: 'restructure', result });
      setRestructureTarget(null);
      // Reload contracts
      await loadContracts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restructure contract');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCut = async (playerId: string, june1: boolean) => {
    if (!franchiseId) return;
    setActionLoading(true);
    try {
      const result = await managementApi.cutPlayer(franchiseId, playerId, june1);
      setActionResult({ type: 'cut', result });
      setCutTarget(null);
      // Reload contracts
      await loadContracts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cut player');
    } finally {
      setActionLoading(false);
    }
  };

  // Calculate totals from filtered/sorted contracts
  const expiringCount = sortedContracts.filter(c => c.years_remaining === 1).length;
  const displayedSalary = sortedContracts.reduce((sum, c) => sum + c.salary, 0);

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
          <span className="contracts-summary__value">{sortedContracts.length}</span>
        </div>
        <div className="contracts-summary__item">
          <span className="contracts-summary__label">Total Cap</span>
          <span className="contracts-summary__value">{formatSalary(totalSalary)}</span>
        </div>
        <div className="contracts-summary__item">
          <span className="contracts-summary__label">Showing</span>
          <span className="contracts-summary__value">{formatSalary(displayedSalary)}</span>
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
          {sortedContracts.map(contract => (
            <div key={contract.player_id} className="contracts-table__row-group">
              <button
                className="contracts-table__row"
                onClick={() => toggleRow(contract.player_id)}
              >
                <span className="contracts-table__name">
                  {expandedRows.has(contract.player_id) ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  {contract.name}
                </span>
                <span className="contracts-table__cell">{contract.position}</span>
                <span className="contracts-table__cell" style={{ color: getOverallColor(contract.overall) }}>
                  {contract.overall}
                </span>
                <span className="contracts-table__cell contracts-table__cell--mono">
                  {formatSalary(contract.salary)}
                </span>
                <span className="contracts-table__cell contracts-table__cell--mono" style={{ color: getYearsColor(contract.years_remaining) }}>
                  {contract.years_remaining || '—'}
                </span>
              </button>

              {/* Expanded detail */}
              {expandedRows.has(contract.player_id) && (
                <div className="contracts-table__detail">
                  <div className="contracts-detail">
                    <div className="contracts-detail__row">
                      <span className="contracts-detail__label">Annual Salary</span>
                      <span className="contracts-detail__value">{formatSalary(contract.salary)}</span>
                    </div>
                    <div className="contracts-detail__row">
                      <span className="contracts-detail__label">Signing Bonus</span>
                      <span className="contracts-detail__value">{formatSalary(contract.signing_bonus)}</span>
                    </div>
                    <div className="contracts-detail__row">
                      <span className="contracts-detail__label">Years Remaining</span>
                      <span className="contracts-detail__value">{contract.years_remaining} of {contract.years_total}</span>
                    </div>
                    <div className="contracts-detail__row">
                      <span className="contracts-detail__label">Total Remaining</span>
                      <span className="contracts-detail__value">
                        {formatSalary(contract.salary * contract.years_remaining)}
                      </span>
                    </div>
                    <div className="contracts-detail__row">
                      <span className="contracts-detail__label">Age</span>
                      <span className="contracts-detail__value">{contract.age}</span>
                    </div>
                    <div className="contracts-detail__row contracts-detail__row--warning">
                      <span className="contracts-detail__label">
                        <AlertTriangle size={10} /> Dead Money if Cut
                      </span>
                      <span className="contracts-detail__value" style={{ color: contract.dead_money_if_cut > 0 ? 'var(--warning)' : 'var(--text-muted)' }}>
                        {formatSalary(contract.dead_money_if_cut)}
                      </span>
                    </div>
                  </div>
                  <div className="contracts-detail__actions">
                    {onContractClick && (
                      <button
                        className="contracts-detail__action contracts-detail__action--primary"
                        onClick={(e) => {
                          e.stopPropagation();
                          onContractClick(contract.player_id, contract.name, contract.position, contract.salary);
                        }}
                        title="Open contract details"
                      >
                        <ExternalLink size={12} />
                        <span>Details</span>
                      </button>
                    )}
                    {contract.years_remaining >= 2 && (
                      <button
                        className="contracts-detail__action contracts-detail__action--restructure"
                        onClick={(e) => {
                          e.stopPropagation();
                          setRestructureTarget(contract);
                        }}
                        title="Restructure contract"
                      >
                        <DollarSign size={12} />
                        <span>Restructure</span>
                      </button>
                    )}
                    <button
                      className="contracts-detail__action contracts-detail__action--cut"
                      onClick={(e) => {
                        e.stopPropagation();
                        setCutTarget(contract);
                      }}
                      title="Cut player"
                    >
                      <Scissors size={12} />
                      <span>Cut</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {sortedContracts.length === 0 && (
        <div className="contracts-empty">No contracts match filters</div>
      )}

      {/* Restructure Modal */}
      {restructureTarget && (
        <div className="contracts-modal-overlay" onClick={() => setRestructureTarget(null)}>
          <div className="contracts-modal" onClick={(e) => e.stopPropagation()}>
            <div className="contracts-modal__header">
              <h3>Restructure Contract</h3>
              <button className="contracts-modal__close" onClick={() => setRestructureTarget(null)}>
                <X size={16} />
              </button>
            </div>
            <div className="contracts-modal__body">
              <p className="contracts-modal__player">{restructureTarget.name} ({restructureTarget.position})</p>
              <div className="contracts-modal__info">
                <div className="contracts-modal__info-row">
                  <span>Current Salary</span>
                  <span>{formatSalary(restructureTarget.salary)}</span>
                </div>
                <div className="contracts-modal__info-row">
                  <span>Years Remaining</span>
                  <span>{restructureTarget.years_remaining}</span>
                </div>
              </div>
              <p className="contracts-modal__help">
                Converting salary to signing bonus creates immediate cap savings but increases future dead money risk.
              </p>
              <div className="contracts-modal__input-group">
                <label>Amount to Convert</label>
                <div className="contracts-modal__presets">
                  <button
                    disabled={actionLoading}
                    onClick={() => handleRestructure(restructureTarget.player_id, Math.floor(restructureTarget.salary * 0.25))}
                  >
                    25% ({formatSalary(Math.floor(restructureTarget.salary * 0.25))})
                  </button>
                  <button
                    disabled={actionLoading}
                    onClick={() => handleRestructure(restructureTarget.player_id, Math.floor(restructureTarget.salary * 0.5))}
                  >
                    50% ({formatSalary(Math.floor(restructureTarget.salary * 0.5))})
                  </button>
                  <button
                    disabled={actionLoading}
                    onClick={() => handleRestructure(restructureTarget.player_id, Math.floor(restructureTarget.salary * 0.75))}
                  >
                    75% ({formatSalary(Math.floor(restructureTarget.salary * 0.75))})
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Cut Modal */}
      {cutTarget && (
        <div className="contracts-modal-overlay" onClick={() => setCutTarget(null)}>
          <div className="contracts-modal contracts-modal--danger" onClick={(e) => e.stopPropagation()}>
            <div className="contracts-modal__header">
              <h3>Cut Player</h3>
              <button className="contracts-modal__close" onClick={() => setCutTarget(null)}>
                <X size={16} />
              </button>
            </div>
            <div className="contracts-modal__body">
              <p className="contracts-modal__player">{cutTarget.name} ({cutTarget.position})</p>
              <div className="contracts-modal__info contracts-modal__info--warning">
                <div className="contracts-modal__info-row">
                  <span>Dead Money</span>
                  <span style={{ color: 'var(--warning)' }}>{formatSalary(cutTarget.dead_money_if_cut)}</span>
                </div>
                <div className="contracts-modal__info-row">
                  <span>Cap Savings</span>
                  <span style={{ color: 'var(--success)' }}>{formatSalary(cutTarget.salary - cutTarget.dead_money_if_cut)}</span>
                </div>
              </div>
              <div className="contracts-modal__buttons">
                <button
                  className="contracts-modal__btn contracts-modal__btn--danger"
                  disabled={actionLoading}
                  onClick={() => handleCut(cutTarget.player_id, false)}
                >
                  Cut Now
                </button>
                <button
                  className="contracts-modal__btn contracts-modal__btn--secondary"
                  disabled={actionLoading}
                  onClick={() => handleCut(cutTarget.player_id, true)}
                  title="Split dead money between this year and next"
                >
                  June 1 Designation
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Result Toast */}
      {actionResult && (
        <div className="contracts-toast" onClick={() => setActionResult(null)}>
          {actionResult.type === 'restructure' ? (
            <p>
              Restructured {(actionResult.result as RestructureContractResponse).player_name}.
              Cap savings: {formatSalary((actionResult.result as RestructureContractResponse).cap_savings)}
            </p>
          ) : (
            <p>
              Released {(actionResult.result as CutPlayerResponse).player_name}.
              Dead money: {formatSalary((actionResult.result as CutPlayerResponse).dead_money_this_year)}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default ContractsContent;
