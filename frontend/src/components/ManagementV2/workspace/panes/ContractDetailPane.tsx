// ContractDetailPane.tsx - Player contract detail pane for workspace

import React, { useEffect, useState, useCallback } from 'react';
import { ChevronDown, ChevronRight, DollarSign, Scissors, AlertTriangle, X } from 'lucide-react';
import { managementApi } from '../../../../api/managementClient';
import type { ContractDetailInfo, RestructureContractResponse, CutPlayerResponse } from '../../../../api/managementClient';
import { PlayerPortrait } from '../../components';
import { useManagementStore, selectFranchiseId, selectLeagueId } from '../../../../stores/managementStore';

// === Helpers ===

const formatSalary = (value: number): string => {
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}M`;
  }
  return `$${value}K`;
};

const getOvrColor = (ovr: number): string => {
  if (ovr >= 85) return 'var(--success)';
  if (ovr >= 75) return 'var(--accent)';
  if (ovr >= 65) return 'var(--text-secondary)';
  return 'var(--text-muted)';
};

// === Component ===

interface ContractDetailPaneProps {
  playerId: string;
  onComplete: () => void;
}

export const ContractDetailPane: React.FC<ContractDetailPaneProps> = ({ playerId, onComplete }) => {
  const franchiseId = useManagementStore(selectFranchiseId);
  const leagueId = useManagementStore(selectLeagueId);
  const bumpJournalVersion = useManagementStore(state => state.bumpJournalVersion);

  const [contract, setContract] = useState<ContractDetailInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Collapsible section states
  const [sections, setSections] = useState({
    yearByYear: true,
    deadMoney: false,
    actions: true,
  });

  // Modal states
  const [showRestructure, setShowRestructure] = useState(false);
  const [showCut, setShowCut] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionResult, setActionResult] = useState<{ type: 'restructure' | 'cut'; result: RestructureContractResponse | CutPlayerResponse } | null>(null);

  const toggleSection = (section: keyof typeof sections) => {
    setSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const loadContract = useCallback(async () => {
    if (!franchiseId) {
      setError('No franchise selected');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await managementApi.getPlayerContract(franchiseId, playerId);
      setContract(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load contract');
    } finally {
      setLoading(false);
    }
  }, [franchiseId, playerId]);

  useEffect(() => {
    loadContract();
  }, [loadContract]);

  // Action handlers
  const handleRestructure = async (amount: number) => {
    if (!franchiseId || !contract) return;
    setActionLoading(true);
    try {
      const result = await managementApi.restructureContract(franchiseId, playerId, amount);
      setActionResult({ type: 'restructure', result });
      setShowRestructure(false);

      // Log to journal
      try {
        await managementApi.addJournalEntry(franchiseId, {
          category: 'transaction',
          title: 'Contract Restructured',
          effect: `Cap savings: ${formatSalary(result.cap_savings)}`,
          detail: `Converted ${formatSalary(amount)} salary to signing bonus for ${contract.name}`,
          player: { name: contract.name, position: contract.position, number: 0 },
        });
        bumpJournalVersion();
      } catch (journalErr) {
        console.error('Failed to log journal entry:', journalErr);
      }

      await loadContract(); // Reload
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restructure');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCut = async (june1: boolean) => {
    if (!franchiseId || !contract) return;
    setActionLoading(true);
    try {
      const result = await managementApi.cutPlayer(franchiseId, playerId, june1);
      setActionResult({ type: 'cut', result });
      setShowCut(false);

      // Log to journal
      try {
        await managementApi.addJournalEntry(franchiseId, {
          category: 'transaction',
          title: 'Player Released',
          effect: `Dead money: ${formatSalary(result.dead_money_this_year)}${june1 ? ' (June 1)' : ''}`,
          detail: `Released ${contract.name}. Cap savings: ${formatSalary(result.cap_savings)}`,
          player: { name: contract.name, position: contract.position, number: 0 },
        });
        bumpJournalVersion();
      } catch (journalErr) {
        console.error('Failed to log journal entry:', journalErr);
      }

      // Player is gone, close pane after delay
      setTimeout(onComplete, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cut player');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return null;

  if (error || !contract) {
    return (
      <div className="pane pane--no-header">
        <div className="pane__body pane__body--placeholder">
          <p>{error || 'Contract Not Found'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="pane pane--no-header">
      <div className="pane__body">
        {/* Player Header */}
        <div className="contract-header">
          <div className="contract-header__portrait">
            <PlayerPortrait
              playerId={playerId}
              leagueId={leagueId || undefined}
              size="lg"
              bracketed
            />
          </div>
          <div className="contract-header__info">
            <div className="contract-header__name">{contract.name}</div>
            <div className="contract-header__top">
              <span className="contract-header__position">{contract.position}</span>
              <span className="contract-header__ovr" style={{ color: getOvrColor(contract.overall) }}>
                {contract.overall} OVR
              </span>
            </div>
            <div className="contract-header__bio">
              {contract.age} yrs · {contract.experience} exp
            </div>
            <div className="contract-header__summary">
              <span>{contract.years_remaining} yr{contract.years_remaining !== 1 ? 's' : ''} left</span>
              <span className="contract-header__value">{formatSalary(contract.total_value)}</span>
            </div>
          </div>
        </div>

        {/* Contract Overview */}
        <div className="pane-section">
          <div className="ctrl-result">
            <span className="ctrl-result__label">Total Value</span>
            <span className="ctrl-result__value">{formatSalary(contract.total_value)}</span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Guaranteed</span>
            <span className="ctrl-result__value" style={{ color: 'var(--warning)' }}>
              {formatSalary(contract.total_guaranteed)}
            </span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Signing Bonus</span>
            <span className="ctrl-result__value ctrl-result__value--muted">
              {formatSalary(contract.signing_bonus)}
            </span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Years</span>
            <span className="ctrl-result__value">
              Yr {contract.current_year} of {contract.years_total}
            </span>
          </div>
          {contract.is_restructured && (
            <div className="ctrl-result">
              <span className="ctrl-result__label">Restructured</span>
              <span className="ctrl-result__value" style={{ color: 'var(--accent)' }}>
                {contract.restructure_count}x
              </span>
            </div>
          )}
        </div>

        {/* Year-by-Year Breakdown - collapsible */}
        <div className="pane-section pane-section--collapsible">
          <button
            className="pane-section__header pane-section__header--toggle"
            onClick={() => toggleSection('yearByYear')}
          >
            <span>Year-by-Year Cap Hits</span>
            {sections.yearByYear ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
          {sections.yearByYear && (
            <div className="contract-years">
              <div className="contract-years__header">
                <span>Yr</span>
                <span>Base</span>
                <span>Bonus</span>
                <span>Cap Hit</span>
              </div>
              {contract.years.map((year) => (
                <div
                  key={year.year}
                  className={`contract-years__row ${year.is_current ? 'contract-years__row--current' : ''}`}
                >
                  <span className="contract-years__yr">{year.year}</span>
                  <span className="contract-years__val">{formatSalary(year.base_salary)}</span>
                  <span className="contract-years__val contract-years__val--muted">
                    {formatSalary(year.signing_bonus_proration)}
                  </span>
                  <span className="contract-years__val contract-years__val--primary">
                    {formatSalary(year.cap_hit)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Dead Money Scenarios - collapsible */}
        <div className="pane-section pane-section--collapsible">
          <button
            className="pane-section__header pane-section__header--toggle"
            onClick={() => toggleSection('deadMoney')}
          >
            <span>Dead Money Scenarios</span>
            <span className="pane-section__preview">
              {sections.deadMoney ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </span>
          </button>
          {sections.deadMoney && (
            <>
              <div className="ctrl-result">
                <span className="ctrl-result__label">
                  <AlertTriangle size={10} /> Cut Now - Dead Money
                </span>
                <span className="ctrl-result__value" style={{ color: 'var(--danger)' }}>
                  {formatSalary(contract.dead_money_if_cut)}
                </span>
              </div>
              <div className="ctrl-result">
                <span className="ctrl-result__label">Cut Now - Cap Savings</span>
                <span className="ctrl-result__value" style={{ color: 'var(--success)' }}>
                  {formatSalary(contract.cap_savings_if_cut)}
                </span>
              </div>
              <div className="ctrl-result">
                <span className="ctrl-result__label">June 1 - This Year</span>
                <span className="ctrl-result__value" style={{ color: 'var(--warning)' }}>
                  {formatSalary(contract.dead_money_june1_this_year)}
                </span>
              </div>
              <div className="ctrl-result">
                <span className="ctrl-result__label">June 1 - Next Year</span>
                <span className="ctrl-result__value" style={{ color: 'var(--warning)' }}>
                  {formatSalary(contract.dead_money_june1_next_year)}
                </span>
              </div>
            </>
          )}
        </div>

        {/* Actions - collapsible */}
        <div className="pane-section pane-section--collapsible">
          <button
            className="pane-section__header pane-section__header--toggle"
            onClick={() => toggleSection('actions')}
          >
            <span>Actions</span>
            {sections.actions ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
          {sections.actions && (
            <div className="contract-actions">
              {contract.can_restructure && (
                <button
                  className="contract-actions__btn contract-actions__btn--restructure"
                  onClick={() => setShowRestructure(true)}
                >
                  <DollarSign size={14} />
                  <span>Restructure</span>
                </button>
              )}
              <button
                className="contract-actions__btn contract-actions__btn--cut"
                onClick={() => setShowCut(true)}
              >
                <Scissors size={14} />
                <span>Cut Player</span>
              </button>
            </div>
          )}
        </div>

        {/* Result Toast */}
        {actionResult && (
          <div className="contract-toast" onClick={() => setActionResult(null)}>
            {actionResult.type === 'restructure' ? (
              <p>
                Restructured. Cap savings: {formatSalary((actionResult.result as RestructureContractResponse).cap_savings)}
              </p>
            ) : (
              <p>
                Released {(actionResult.result as CutPlayerResponse).player_name}.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Restructure Modal */}
      {showRestructure && contract && (
        <div className="contracts-modal-overlay" onClick={() => setShowRestructure(false)}>
          <div className="contracts-modal" onClick={(e) => e.stopPropagation()}>
            <div className="contracts-modal__header">
              <h3>Restructure Contract</h3>
              <button className="contracts-modal__close" onClick={() => setShowRestructure(false)}>
                <X size={16} />
              </button>
            </div>
            <div className="contracts-modal__body">
              <p className="contracts-modal__player">{contract.name}</p>
              <div className="contracts-modal__info">
                <div className="contracts-modal__info-row">
                  <span>Current Base Salary</span>
                  <span>{formatSalary(contract.years[contract.current_year - 1]?.base_salary || 0)}</span>
                </div>
                <div className="contracts-modal__info-row">
                  <span>Years Remaining</span>
                  <span>{contract.years_remaining}</span>
                </div>
              </div>
              <p className="contracts-modal__help">
                Converting salary to signing bonus creates immediate cap savings but adds future dead money.
              </p>
              <div className="contracts-modal__input-group">
                <label>Amount to Convert</label>
                <div className="contracts-modal__presets">
                  {[0.25, 0.5, 0.75].map((pct) => {
                    const base = contract.years[contract.current_year - 1]?.base_salary || 0;
                    const amount = Math.floor(base * pct);
                    return (
                      <button
                        key={pct}
                        disabled={actionLoading}
                        onClick={() => handleRestructure(amount)}
                      >
                        {pct * 100}% ({formatSalary(amount)})
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Cut Modal */}
      {showCut && contract && (
        <div className="contracts-modal-overlay" onClick={() => setShowCut(false)}>
          <div className="contracts-modal contracts-modal--danger" onClick={(e) => e.stopPropagation()}>
            <div className="contracts-modal__header">
              <h3>Cut Player</h3>
              <button className="contracts-modal__close" onClick={() => setShowCut(false)}>
                <X size={16} />
              </button>
            </div>
            <div className="contracts-modal__body">
              <p className="contracts-modal__player">{contract.name}</p>
              <div className="contracts-modal__info contracts-modal__info--warning">
                <div className="contracts-modal__info-row">
                  <span>Dead Money</span>
                  <span style={{ color: 'var(--warning)' }}>{formatSalary(contract.dead_money_if_cut)}</span>
                </div>
                <div className="contracts-modal__info-row">
                  <span>Cap Savings</span>
                  <span style={{ color: 'var(--success)' }}>{formatSalary(contract.cap_savings_if_cut)}</span>
                </div>
              </div>
              <div className="contracts-modal__buttons">
                <button
                  className="contracts-modal__btn contracts-modal__btn--danger"
                  disabled={actionLoading}
                  onClick={() => handleCut(false)}
                >
                  Cut Now
                </button>
                <button
                  className="contracts-modal__btn contracts-modal__btn--secondary"
                  disabled={actionLoading}
                  onClick={() => handleCut(true)}
                  title="Split dead money between this year and next"
                >
                  June 1 Designation
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ContractDetailPane;
