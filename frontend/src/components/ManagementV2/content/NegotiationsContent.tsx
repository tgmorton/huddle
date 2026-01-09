// NegotiationsContent.tsx - Active negotiations list for FinancesPanel

import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, MessageSquare, X, AlertTriangle } from 'lucide-react';
import { managementApi } from '../../../api/managementClient';
import type { ActiveNegotiationInfo } from '../../../api/managementClient';
import { useManagementStore, selectFranchiseId } from '../../../stores/managementStore';
import { getOverallColor } from '../../../types/admin';

// === Helpers ===

const formatSalary = (value: number): string => {
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}M`;
  }
  return `$${value}K`;
};

const getPatienceColor = (patience: number): string => {
  if (patience >= 70) return 'var(--success)';
  if (patience >= 40) return 'var(--accent)';
  if (patience >= 20) return 'var(--warning)';
  return 'var(--danger)';
};

const getPatienceLabel = (patience: number): string => {
  if (patience >= 70) return 'Patient';
  if (patience >= 40) return 'Interested';
  if (patience >= 20) return 'Impatient';
  return 'Walking Away';
};

// === Component ===

interface NegotiationsContentProps {
  onResumeNegotiation?: (playerId: string, playerName: string, position: string, overall: number) => void;
}

export const NegotiationsContent: React.FC<NegotiationsContentProps> = ({ onResumeNegotiation }) => {
  const franchiseId = useManagementStore(selectFranchiseId);
  const [negotiations, setNegotiations] = useState<ActiveNegotiationInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  const loadNegotiations = useCallback(async () => {
    if (!franchiseId) return;

    setLoading(true);
    setError(null);
    try {
      const data = await managementApi.getActiveNegotiations(franchiseId);
      setNegotiations(data.negotiations);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load negotiations');
    } finally {
      setLoading(false);
    }
  }, [franchiseId]);

  useEffect(() => {
    loadNegotiations();
  }, [loadNegotiations]);

  const handleCancel = async (playerId: string) => {
    if (!franchiseId) return;
    setCancellingId(playerId);
    try {
      await managementApi.cancelNegotiation(franchiseId, playerId);
      setNegotiations(prev => prev.filter(n => n.player_id !== playerId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel negotiation');
    } finally {
      setCancellingId(null);
    }
  };

  if (!franchiseId) {
    return (
      <div className="ref-content">
        <div className="ref-content__empty">Load a franchise to view negotiations</div>
      </div>
    );
  }

  if (loading) return null;

  if (error) {
    return (
      <div className="ref-content">
        <div className="ref-content__error">{error}</div>
        <button className="ref-content__retry" onClick={loadNegotiations}>
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    );
  }

  if (negotiations.length === 0) {
    return (
      <div className="ref-content negotiations-content">
        <div className="negotiations-empty">
          <MessageSquare size={24} className="negotiations-empty__icon" />
          <p className="negotiations-empty__text">No active negotiations</p>
          <p className="negotiations-empty__hint">Start a negotiation from the Free Agents list</p>
        </div>
      </div>
    );
  }

  return (
    <div className="ref-content negotiations-content">
      <div className="negotiations-header">
        <span className="negotiations-header__count">{negotiations.length} Active</span>
        <button className="negotiations-header__refresh" onClick={loadNegotiations} title="Refresh">
          <RefreshCw size={12} />
        </button>
      </div>

      <div className="negotiations-list">
        {negotiations.map(neg => (
          <div key={neg.negotiation_id} className="negotiations-item">
            <button
              className="negotiations-item__main"
              onClick={() => onResumeNegotiation?.(neg.player_id, neg.player_name, neg.player_position, neg.player_overall)}
            >
              <div className="negotiations-item__player">
                <span className="negotiations-item__name">{neg.player_name}</span>
                <span className="negotiations-item__pos">{neg.player_position}</span>
                <span className="negotiations-item__ovr" style={{ color: getOverallColor(neg.player_overall) }}>
                  {neg.player_overall}
                </span>
              </div>

              <div className="negotiations-item__status">
                <div className="negotiations-item__rounds">
                  Round {neg.rounds}
                </div>
                <div
                  className="negotiations-item__patience"
                  style={{ color: getPatienceColor(neg.patience) }}
                >
                  {neg.patience < 30 && <AlertTriangle size={10} />}
                  {getPatienceLabel(neg.patience)}
                </div>
              </div>

              <div className="negotiations-item__offers">
                {neg.last_offer && (
                  <div className="negotiations-item__offer">
                    <span className="negotiations-item__offer-label">Your Offer</span>
                    <span className="negotiations-item__offer-value">
                      {neg.last_offer.years}yr / {formatSalary(neg.last_offer.salary)}
                    </span>
                  </div>
                )}
                {neg.current_demand && (
                  <div className="negotiations-item__offer negotiations-item__offer--demand">
                    <span className="negotiations-item__offer-label">Asking</span>
                    <span className="negotiations-item__offer-value">
                      {neg.current_demand.years}yr / {formatSalary(neg.current_demand.salary)}
                    </span>
                  </div>
                )}
              </div>
            </button>

            <button
              className="negotiations-item__cancel"
              onClick={() => handleCancel(neg.player_id)}
              disabled={cancellingId === neg.player_id}
              title="Cancel Negotiation"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default NegotiationsContent;
