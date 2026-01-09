// NegotiationPane.tsx - Full contract negotiation UI

import React, { useState, useEffect, useCallback } from 'react';
import { X, DollarSign, TrendingUp, TrendingDown, AlertTriangle, CheckCircle, MessageSquare, Frown, Smile, Meh } from 'lucide-react';
import { managementApi } from '../../../../api/managementClient';
import type {
  StartNegotiationResponse,
  SubmitOfferResponse,
  ContractOffer,
  NegotiationResult,
  NegotiationTone,
} from '../../../../api/managementClient';
import { useManagementStore, selectFranchiseId } from '../../../../stores/managementStore';
import { getOverallColor } from '../../../../types/admin';

// === Helpers ===

const formatSalary = (value: number): string => {
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}M`;
  }
  return `$${value}K`;
};

const getToneIcon = (tone: NegotiationTone) => {
  switch (tone) {
    case 'ENTHUSIASTIC': return Smile;
    case 'PROFESSIONAL': return Meh;
    case 'DEMANDING': return Frown;
    case 'INSULTED': return AlertTriangle;
    default: return MessageSquare;
  }
};

const getToneColor = (tone: NegotiationTone): string => {
  switch (tone) {
    case 'ENTHUSIASTIC': return 'var(--success)';
    case 'PROFESSIONAL': return 'var(--text-secondary)';
    case 'DEMANDING': return 'var(--accent)';
    case 'INSULTED': return 'var(--danger)';
    default: return 'var(--text-muted)';
  }
};

const getResultColor = (result: NegotiationResult): string => {
  switch (result) {
    case 'ACCEPTED': return 'var(--success)';
    case 'COUNTER_OFFER': return 'var(--accent)';
    case 'REJECTED': return 'var(--warning)';
    case 'WALK_AWAY': return 'var(--danger)';
    default: return 'var(--text-muted)';
  }
};

const getPatienceColor = (patience: number): string => {
  if (patience > 0.7) return 'var(--success)';
  if (patience > 0.4) return 'var(--accent)';
  if (patience > 0.2) return 'var(--warning)';
  return 'var(--danger)';
};

// === Types ===

interface OfferHistoryEntry {
  round: number;
  offer: ContractOffer;
  response: SubmitOfferResponse;
}

interface NegotiationPaneProps {
  playerId: string;
  onComplete?: () => void;
  onSigned?: (playerId: string, contract: ContractOffer) => void;
}

export const NegotiationPane: React.FC<NegotiationPaneProps> = ({
  playerId,
  onComplete,
  onSigned,
}) => {
  const franchiseId = useManagementStore(selectFranchiseId);
  const bumpJournalVersion = useManagementStore(state => state.bumpJournalVersion);

  // Negotiation state
  const [negotiation, setNegotiation] = useState<StartNegotiationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Offer builder state
  const [years, setYears] = useState(3);
  const [salary, setSalary] = useState(0);
  const [signingBonus, setSigningBonus] = useState(0);

  // History and current response
  const [history, setHistory] = useState<OfferHistoryEntry[]>([]);
  const [latestResponse, setLatestResponse] = useState<SubmitOfferResponse | null>(null);
  const [isComplete, setIsComplete] = useState(false);

  // Computed values
  const totalValue = salary * years + signingBonus;
  const guaranteed = signingBonus + Math.floor(salary / 2);
  const marketValue = negotiation?.market_value;
  const offerPct = marketValue ? (totalValue / marketValue.total_value) * 100 : 0;

  // Start negotiation on mount
  useEffect(() => {
    if (!franchiseId || !playerId) return;

    const startNegotiation = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await managementApi.startNegotiation(franchiseId, playerId);
        setNegotiation(result);

        // Initialize offer builder with market values
        setYears(result.market_value.years);
        setSalary(result.market_value.base_salary);
        setSigningBonus(result.market_value.signing_bonus);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to start negotiation');
      } finally {
        setLoading(false);
      }
    };

    startNegotiation();
  }, [franchiseId, playerId]);

  // Submit an offer
  const handleSubmitOffer = useCallback(async () => {
    if (!franchiseId || !playerId || submitting || isComplete) return;

    setSubmitting(true);
    try {
      const response = await managementApi.submitOffer(franchiseId, playerId, {
        years,
        salary,
        signing_bonus: signingBonus,
      });

      // Add to history
      const offerEntry: OfferHistoryEntry = {
        round: history.length + 1,
        offer: {
          years,
          salary,
          signing_bonus: signingBonus,
          total_value: totalValue,
          guaranteed,
        },
        response,
      };
      setHistory(prev => [...prev, offerEntry]);
      setLatestResponse(response);

      // Check if negotiation is over
      if (response.result === 'ACCEPTED') {
        setIsComplete(true);
        if (onSigned && response.agreed_contract) {
          onSigned(playerId, response.agreed_contract);
        }
        // Log to journal
        if (franchiseId && negotiation && response.agreed_contract) {
          try {
            await managementApi.addJournalEntry(franchiseId, {
              category: 'transaction',
              title: 'Contract Signed',
              effect: `${response.agreed_contract.years}yr / ${formatSalary(response.agreed_contract.salary)} per year`,
              detail: `Signed ${negotiation.player_name} to a ${formatSalary(response.agreed_contract.total_value)} contract`,
              player: { name: negotiation.player_name, position: negotiation.player_position, number: 0 },
            });
            bumpJournalVersion();
          } catch (journalErr) {
            console.error('Failed to log journal entry:', journalErr);
          }
        }
      } else if (response.result === 'WALK_AWAY') {
        setIsComplete(true);
        // Log to journal
        if (franchiseId && negotiation) {
          try {
            await managementApi.addJournalEntry(franchiseId, {
              category: 'transaction',
              title: 'Negotiation Failed',
              effect: 'Player walked away',
              detail: `${negotiation.player_name} ended contract negotiations`,
              player: { name: negotiation.player_name, position: negotiation.player_position, number: 0 },
            });
            bumpJournalVersion();
          } catch (journalErr) {
            console.error('Failed to log journal entry:', journalErr);
          }
        }
      } else if (response.counter_offer) {
        // Pre-fill with counter offer for convenience
        setSalary(response.counter_offer.salary);
        setSigningBonus(response.counter_offer.signing_bonus);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit offer');
    } finally {
      setSubmitting(false);
    }
  }, [franchiseId, playerId, years, salary, signingBonus, submitting, isComplete, history.length, totalValue, guaranteed, onSigned]);

  // Cancel negotiation
  const handleCancel = useCallback(async () => {
    if (!franchiseId || !playerId) return;

    try {
      await managementApi.cancelNegotiation(franchiseId, playerId);
      if (onComplete) onComplete();
    } catch (err) {
      // Ignore errors on cancel
      if (onComplete) onComplete();
    }
  }, [franchiseId, playerId, onComplete]);

  if (loading) {
    return (
      <div className="negotiation-pane negotiation-pane--loading">
        <div className="negotiation-pane__loader">Starting negotiation...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="negotiation-pane negotiation-pane--error">
        <div className="negotiation-pane__error">
          <AlertTriangle size={24} />
          <p>{error}</p>
          <button onClick={onComplete}>Close</button>
        </div>
      </div>
    );
  }

  if (!negotiation) return null;

  return (
    <div className="negotiation-pane">
      {/* Player Header */}
      <div className="negotiation-header">
        <div className="negotiation-header__info">
          <h2 className="negotiation-header__name">{negotiation.player_name}</h2>
          <div className="negotiation-header__meta">
            <span className="negotiation-header__position">{negotiation.player_position}</span>
            <span className="negotiation-header__overall" style={{ color: getOverallColor(negotiation.player_overall) }}>
              {negotiation.player_overall} OVR
            </span>
            <span className="negotiation-header__age">{negotiation.player_age} yrs</span>
          </div>
        </div>
        <div className="negotiation-header__market">
          <div className="negotiation-header__market-label">Market Value</div>
          <div className="negotiation-header__market-value">{formatSalary(marketValue?.total_value || 0)}</div>
          <div className="negotiation-header__market-tier" data-tier={marketValue?.tier}>
            {marketValue?.tier}
          </div>
        </div>
      </div>

      {/* Patience Indicator */}
      {latestResponse && (
        <div className="negotiation-patience">
          <div className="negotiation-patience__label">
            Agent Patience
            {latestResponse.walk_away_chance > 0 && (
              <span className="negotiation-patience__warning">
                <AlertTriangle size={12} />
                {Math.round(latestResponse.walk_away_chance * 100)}% walk-away risk
              </span>
            )}
          </div>
          <div className="negotiation-patience__bar">
            <div
              className="negotiation-patience__fill"
              style={{
                width: `${latestResponse.patience * 100}%`,
                background: getPatienceColor(latestResponse.patience),
              }}
            />
          </div>
        </div>
      )}

      {/* Latest Response */}
      {latestResponse && (
        <div className={`negotiation-response negotiation-response--${latestResponse.result.toLowerCase()}`}>
          <div className="negotiation-response__header">
            {React.createElement(getToneIcon(latestResponse.tone), {
              size: 18,
              style: { color: getToneColor(latestResponse.tone) },
            })}
            <span className="negotiation-response__result" style={{ color: getResultColor(latestResponse.result) }}>
              {latestResponse.result.replace('_', ' ')}
            </span>
            <span className="negotiation-response__round">Round {latestResponse.rounds}</span>
          </div>
          <p className="negotiation-response__message">{latestResponse.message}</p>
          {latestResponse.counter_offer && latestResponse.result !== 'ACCEPTED' && (
            <div className="negotiation-response__counter">
              <span className="negotiation-response__counter-label">Counter Offer:</span>
              <span className="negotiation-response__counter-value">
                {latestResponse.counter_offer.years}yr / {formatSalary(latestResponse.counter_offer.salary)}/yr
                ({formatSalary(latestResponse.counter_offer.total_value)} total)
              </span>
            </div>
          )}
        </div>
      )}

      {/* Offer Builder */}
      {!isComplete && (
        <div className="negotiation-builder">
          <h3 className="negotiation-builder__title">Your Offer</h3>

          <div className="negotiation-builder__field">
            <label>Contract Length</label>
            <div className="negotiation-builder__years">
              {[1, 2, 3, 4, 5, 6, 7].map(y => (
                <button
                  key={y}
                  className={`negotiation-builder__year-btn ${years === y ? 'active' : ''}`}
                  onClick={() => setYears(y)}
                >
                  {y}yr
                </button>
              ))}
            </div>
          </div>

          <div className="negotiation-builder__field">
            <label>Annual Salary</label>
            <div className="negotiation-builder__input-row">
              <input
                type="range"
                min={0}
                max={Math.max((marketValue?.base_salary || 1000) * 1.5, 1000)}
                step={50}
                value={salary}
                onChange={(e) => setSalary(parseInt(e.target.value))}
              />
              <input
                type="number"
                value={salary}
                onChange={(e) => setSalary(parseInt(e.target.value) || 0)}
                className="negotiation-builder__input"
              />
              <span className="negotiation-builder__unit">K/yr</span>
            </div>
            <div className="negotiation-builder__comparison">
              Market: {formatSalary(marketValue?.base_salary || 0)}/yr
            </div>
          </div>

          <div className="negotiation-builder__field">
            <label>Signing Bonus</label>
            <div className="negotiation-builder__input-row">
              <input
                type="range"
                min={0}
                max={Math.max((marketValue?.signing_bonus || 500) * 2, 500)}
                step={25}
                value={signingBonus}
                onChange={(e) => setSigningBonus(parseInt(e.target.value))}
              />
              <input
                type="number"
                value={signingBonus}
                onChange={(e) => setSigningBonus(parseInt(e.target.value) || 0)}
                className="negotiation-builder__input"
              />
              <span className="negotiation-builder__unit">K total</span>
            </div>
          </div>

          {/* Offer Summary */}
          <div className="negotiation-builder__summary">
            <div className="negotiation-builder__summary-row">
              <span>Total Value</span>
              <span className="negotiation-builder__summary-value">{formatSalary(totalValue)}</span>
            </div>
            <div className="negotiation-builder__summary-row">
              <span>Guaranteed</span>
              <span>{formatSalary(guaranteed)}</span>
            </div>
            <div className="negotiation-builder__summary-row">
              <span>vs Market</span>
              <span style={{
                color: offerPct >= 95 ? 'var(--success)' : offerPct >= 80 ? 'var(--accent)' : 'var(--danger)'
              }}>
                {offerPct >= 100 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                {offerPct.toFixed(0)}%
              </span>
            </div>
          </div>

          {/* Submit Button */}
          <button
            className="negotiation-builder__submit"
            onClick={handleSubmitOffer}
            disabled={submitting || salary === 0}
          >
            {submitting ? 'Submitting...' : history.length === 0 ? 'Make Initial Offer' : 'Submit Counter'}
          </button>
        </div>
      )}

      {/* Completion State */}
      {isComplete && latestResponse && (
        <div className={`negotiation-complete negotiation-complete--${latestResponse.result.toLowerCase()}`}>
          {latestResponse.result === 'ACCEPTED' ? (
            <>
              <CheckCircle size={32} />
              <h3>Contract Agreed!</h3>
              <p>{negotiation.player_name} has signed for {formatSalary(latestResponse.agreed_contract?.total_value || 0)}</p>
            </>
          ) : (
            <>
              <X size={32} />
              <h3>Negotiations Failed</h3>
              <p>{negotiation.player_name} has walked away from the table.</p>
            </>
          )}
          <button className="negotiation-complete__close" onClick={onComplete}>
            Close
          </button>
        </div>
      )}

      {/* History */}
      {history.length > 0 && !isComplete && (
        <div className="negotiation-history">
          <h4 className="negotiation-history__title">Offer History</h4>
          <div className="negotiation-history__list">
            {history.map((entry, idx) => (
              <div key={idx} className="negotiation-history__entry">
                <div className="negotiation-history__round">Round {entry.round}</div>
                <div className="negotiation-history__offer">
                  {entry.offer.years}yr / {formatSalary(entry.offer.salary)}/yr
                </div>
                <div
                  className="negotiation-history__result"
                  style={{ color: getResultColor(entry.response.result) }}
                >
                  {entry.response.result.replace('_', ' ')}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cancel Button */}
      {!isComplete && (
        <button className="negotiation-cancel" onClick={handleCancel}>
          Walk Away
        </button>
      )}
    </div>
  );
};

export default NegotiationPane;
