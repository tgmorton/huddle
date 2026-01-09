// AuctionPane.tsx - Competitive bidding UI for elite free agents

import React, { useState, useEffect, useCallback } from 'react';
import { X, DollarSign, TrendingUp, TrendingDown, AlertTriangle, CheckCircle, Users, Crown, Timer, Flag } from 'lucide-react';
import { managementApi } from '../../../../api/managementClient';
import type {
  StartAuctionResponse,
  SubmitAuctionBidResponse,
  FinalizeAuctionResponse,
  AuctionBid,
  CompetingTeamBid,
  AuctionPhase,
  AuctionResult,
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

const getInterestColor = (interest: string): string => {
  switch (interest) {
    case 'HIGH': return 'var(--danger)';
    case 'MEDIUM': return 'var(--accent)';
    case 'LOW': return 'var(--text-muted)';
    default: return 'var(--text-secondary)';
  }
};

const getPhaseColor = (phase: AuctionPhase): string => {
  switch (phase) {
    case 'BIDDING': return 'var(--success)';
    case 'FINAL_CALL': return 'var(--warning)';
    case 'CLOSED': return 'var(--text-muted)';
    default: return 'var(--text-secondary)';
  }
};

const getResultColor = (result: AuctionResult): string => {
  switch (result) {
    case 'WON': return 'var(--success)';
    case 'OUTBID': return 'var(--danger)';
    case 'WITHDREW': return 'var(--text-muted)';
    case 'NO_BID': return 'var(--accent)';
    default: return 'var(--text-secondary)';
  }
};

// === Types ===

interface AuctionPaneProps {
  playerId: string;
  onComplete?: () => void;
  onWon?: (playerId: string, bid: AuctionBid) => void;
}

export const AuctionPane: React.FC<AuctionPaneProps> = ({
  playerId,
  onComplete,
  onWon,
}) => {
  const franchiseId = useManagementStore(selectFranchiseId);
  const bumpJournalVersion = useManagementStore(state => state.bumpJournalVersion);

  // Auction state
  const [auction, setAuction] = useState<StartAuctionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Bid builder state
  const [years, setYears] = useState(3);
  const [salary, setSalary] = useState(0);
  const [signingBonus, setSigningBonus] = useState(0);

  // Current auction state
  const [phase, setPhase] = useState<AuctionPhase>('BIDDING');
  const [round, setRound] = useState(1);
  const [maxRounds, setMaxRounds] = useState(3);
  const [yourBid, setYourBid] = useState<AuctionBid | null>(null);
  const [isTopBid, setIsTopBid] = useState(false);
  const [competingTeams, setCompetingTeams] = useState<CompetingTeamBid[]>([]);
  const [topBidRange, setTopBidRange] = useState<string | null>(null);
  const [message, setMessage] = useState<string>('');

  // Finalized result
  const [finalResult, setFinalResult] = useState<FinalizeAuctionResponse | null>(null);

  // Computed values
  const totalValue = salary * years + signingBonus;
  const guaranteed = signingBonus + Math.floor(salary / 2);
  const marketValue = auction?.market_value;
  const offerPct = marketValue ? (totalValue / marketValue.total_value) * 100 : 0;

  // Start auction on mount
  useEffect(() => {
    if (!franchiseId || !playerId) return;

    const startAuction = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await managementApi.startAuction(franchiseId, playerId);
        setAuction(result);
        setPhase(result.phase);
        setRound(result.round);
        setMaxRounds(result.max_rounds);
        setCompetingTeams(result.competing_teams);
        setMessage(result.message);

        // Initialize offer builder with floor bid
        setYears(result.floor_bid.years);
        setSalary(result.floor_bid.salary);
        setSigningBonus(result.floor_bid.signing_bonus);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to start auction');
      } finally {
        setLoading(false);
      }
    };

    startAuction();
  }, [franchiseId, playerId]);

  // Submit a bid
  const handleSubmitBid = useCallback(async () => {
    if (!franchiseId || !playerId || submitting || phase === 'CLOSED') return;

    setSubmitting(true);
    try {
      const response = await managementApi.submitAuctionBid(franchiseId, playerId, {
        years,
        salary,
        signing_bonus: signingBonus,
      });

      setPhase(response.phase);
      setRound(response.round);
      setYourBid(response.your_bid);
      setIsTopBid(response.is_top_bid);
      setCompetingTeams(response.competing_teams);
      setTopBidRange(response.top_bid_range);
      setMessage(response.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit bid');
    } finally {
      setSubmitting(false);
    }
  }, [franchiseId, playerId, years, salary, signingBonus, submitting, phase]);

  // Advance to next round
  const handleAdvanceRound = useCallback(async () => {
    if (!franchiseId || !playerId || submitting) return;

    setSubmitting(true);
    try {
      const response = await managementApi.advanceAuctionRound(franchiseId, playerId);

      setPhase(response.phase);
      setRound(response.round);
      setYourBid(response.your_bid);
      setIsTopBid(response.is_top_bid);
      setCompetingTeams(response.competing_teams);
      setTopBidRange(response.top_bid_range);
      setMessage(response.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to advance round');
    } finally {
      setSubmitting(false);
    }
  }, [franchiseId, playerId, submitting]);

  // Finalize auction
  const handleFinalize = useCallback(async () => {
    if (!franchiseId || !playerId || submitting || !auction) return;

    setSubmitting(true);
    try {
      const result = await managementApi.finalizeAuction(franchiseId, playerId);
      setFinalResult(result);
      setPhase('CLOSED');

      if (result.result === 'WON' && result.winning_bid && onWon) {
        onWon(playerId, result.winning_bid);
      }

      // Log to journal
      try {
        if (result.result === 'WON' && result.winning_bid) {
          await managementApi.addJournalEntry(franchiseId, {
            category: 'transaction',
            title: 'Free Agent Signed (Auction)',
            effect: `${result.winning_bid.years}yr / ${formatSalary(result.winning_bid.salary)}/yr`,
            detail: `Won auction for ${auction.player_name}. Total: ${formatSalary(result.winning_bid.total_value)}`,
            player: { name: auction.player_name, position: auction.player_position, number: 0 },
          });
        } else if (result.result === 'OUTBID') {
          await managementApi.addJournalEntry(franchiseId, {
            category: 'transaction',
            title: 'Auction Lost',
            effect: `Outbid by ${result.winning_team}`,
            detail: `${auction.player_name} signed with ${result.winning_team}`,
            player: { name: auction.player_name, position: auction.player_position, number: 0 },
          });
        }
        bumpJournalVersion();
      } catch (journalErr) {
        console.error('Failed to log journal entry:', journalErr);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to finalize auction');
    } finally {
      setSubmitting(false);
    }
  }, [franchiseId, playerId, submitting, auction, onWon, bumpJournalVersion]);

  // Withdraw from auction
  const handleWithdraw = useCallback(async () => {
    if (!franchiseId || !playerId) return;

    try {
      await managementApi.withdrawFromAuction(franchiseId, playerId);
      if (onComplete) onComplete();
    } catch (err) {
      if (onComplete) onComplete();
    }
  }, [franchiseId, playerId, onComplete]);

  if (loading) {
    return (
      <div className="auction-pane auction-pane--loading">
        <div className="auction-pane__loader">Starting auction...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="auction-pane auction-pane--error">
        <div className="auction-pane__error">
          <AlertTriangle size={24} />
          <p>{error}</p>
          <button onClick={onComplete}>Close</button>
        </div>
      </div>
    );
  }

  if (!auction) return null;

  // Show finalized result
  if (finalResult) {
    return (
      <div className="auction-pane">
        <div className={`auction-complete auction-complete--${finalResult.result.toLowerCase()}`}>
          {finalResult.result === 'WON' ? (
            <>
              <Crown size={32} className="auction-complete__icon" />
              <h3>Auction Won!</h3>
              <p>You've signed {auction.player_name} for {formatSalary(finalResult.winning_bid?.total_value || 0)}!</p>
              <div className="auction-complete__details">
                <span>{finalResult.winning_bid?.years}yr / {formatSalary(finalResult.winning_bid?.salary || 0)}/yr</span>
                <span>+ {formatSalary(finalResult.winning_bid?.signing_bonus || 0)} bonus</span>
              </div>
            </>
          ) : finalResult.result === 'OUTBID' ? (
            <>
              <X size={32} className="auction-complete__icon" />
              <h3>Outbid</h3>
              <p>{auction.player_name} has signed with the {finalResult.winning_team}.</p>
            </>
          ) : (
            <>
              <AlertTriangle size={32} className="auction-complete__icon" />
              <h3>No Deal</h3>
              <p>{finalResult.message}</p>
            </>
          )}
          <button className="auction-complete__close" onClick={onComplete}>
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="auction-pane">
      {/* Player Header */}
      <div className="auction-header">
        <div className="auction-header__info">
          <h2 className="auction-header__name">{auction.player_name}</h2>
          <div className="auction-header__meta">
            <span className="auction-header__position">{auction.player_position}</span>
            <span className="auction-header__overall" style={{ color: getOverallColor(auction.player_overall) }}>
              {auction.player_overall} OVR
            </span>
            <span className="auction-header__age">{auction.player_age} yrs</span>
          </div>
        </div>
        <div className="auction-header__market">
          <div className="auction-header__market-label">Market Value</div>
          <div className="auction-header__market-value">{formatSalary(marketValue?.total_value || 0)}</div>
          <div className="auction-header__market-tier" data-tier={marketValue?.tier}>
            {marketValue?.tier}
          </div>
        </div>
      </div>

      {/* Auction Status */}
      <div className="auction-status">
        <div className="auction-status__phase" style={{ color: getPhaseColor(phase) }}>
          <Timer size={14} />
          <span>{phase.replace('_', ' ')}</span>
        </div>
        <div className="auction-status__round">
          Round {round} of {maxRounds}
        </div>
        {isTopBid && yourBid && (
          <div className="auction-status__leading">
            <Crown size={14} />
            <span>You're leading!</span>
          </div>
        )}
      </div>

      {/* Message */}
      {message && (
        <div className="auction-message">
          <p>{message}</p>
        </div>
      )}

      {/* Competing Teams */}
      <div className="auction-teams">
        <h4 className="auction-teams__title">
          <Users size={14} />
          Competing Teams ({competingTeams.length})
        </h4>
        <div className="auction-teams__list">
          {competingTeams.map(team => (
            <div
              key={team.team_id}
              className={`auction-teams__team ${team.is_top_bid ? 'auction-teams__team--leading' : ''}`}
            >
              <div className="auction-teams__team-info">
                <span className="auction-teams__team-abbrev">{team.team_abbrev}</span>
                <span className="auction-teams__team-name">{team.team_name}</span>
              </div>
              <div className="auction-teams__team-status">
                <span
                  className="auction-teams__interest"
                  style={{ color: getInterestColor(team.interest_level) }}
                >
                  {team.interest_level}
                </span>
                {team.has_bid && (
                  <span className="auction-teams__bid-range">
                    {team.bid_range}
                  </span>
                )}
                {team.is_top_bid && (
                  <Crown size={12} className="auction-teams__crown" />
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Your Bid Status */}
      {yourBid && (
        <div className={`auction-your-bid ${isTopBid ? 'auction-your-bid--leading' : 'auction-your-bid--behind'}`}>
          <div className="auction-your-bid__header">
            <span>Your Bid</span>
            {isTopBid ? (
              <span className="auction-your-bid__status auction-your-bid__status--leading">
                <Crown size={12} /> Leading
              </span>
            ) : (
              <span className="auction-your-bid__status auction-your-bid__status--behind">
                <TrendingDown size={12} /> Outbid
              </span>
            )}
          </div>
          <div className="auction-your-bid__details">
            <span>{yourBid.years}yr / {formatSalary(yourBid.salary)}/yr</span>
            <span className="auction-your-bid__total">{formatSalary(yourBid.total_value)} total</span>
          </div>
          {!isTopBid && topBidRange && (
            <div className="auction-your-bid__top-range">
              Top bid: {topBidRange}
            </div>
          )}
        </div>
      )}

      {/* Bid Builder */}
      {phase !== 'CLOSED' && (
        <div className="auction-builder">
          <h3 className="auction-builder__title">
            {yourBid ? 'Raise Your Bid' : 'Place Your Bid'}
          </h3>

          <div className="auction-builder__field">
            <label>Contract Length</label>
            <div className="auction-builder__years">
              {[1, 2, 3, 4, 5, 6, 7].map(y => (
                <button
                  key={y}
                  className={`auction-builder__year-btn ${years === y ? 'active' : ''}`}
                  onClick={() => setYears(y)}
                >
                  {y}yr
                </button>
              ))}
            </div>
          </div>

          <div className="auction-builder__field">
            <label>Annual Salary</label>
            <div className="auction-builder__input-row">
              <input
                type="range"
                min={auction.floor_bid.salary}
                max={Math.max((marketValue?.base_salary || 1000) * 1.5, auction.floor_bid.salary * 1.5)}
                step={50}
                value={salary}
                onChange={(e) => setSalary(parseInt(e.target.value))}
              />
              <input
                type="number"
                value={salary}
                onChange={(e) => setSalary(parseInt(e.target.value) || 0)}
                className="auction-builder__input"
              />
              <span className="auction-builder__unit">K/yr</span>
            </div>
            <div className="auction-builder__comparison">
              Floor: {formatSalary(auction.floor_bid.salary)}/yr
            </div>
          </div>

          <div className="auction-builder__field">
            <label>Signing Bonus</label>
            <div className="auction-builder__input-row">
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
                className="auction-builder__input"
              />
              <span className="auction-builder__unit">K total</span>
            </div>
          </div>

          {/* Offer Summary */}
          <div className="auction-builder__summary">
            <div className="auction-builder__summary-row">
              <span>Total Value</span>
              <span className="auction-builder__summary-value">{formatSalary(totalValue)}</span>
            </div>
            <div className="auction-builder__summary-row">
              <span>Guaranteed</span>
              <span>{formatSalary(guaranteed)}</span>
            </div>
            <div className="auction-builder__summary-row">
              <span>vs Market</span>
              <span style={{
                color: offerPct >= 100 ? 'var(--success)' : offerPct >= 90 ? 'var(--accent)' : 'var(--danger)'
              }}>
                {offerPct >= 100 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                {offerPct.toFixed(0)}%
              </span>
            </div>
          </div>

          {/* Submit Button */}
          <button
            className="auction-builder__submit"
            onClick={handleSubmitBid}
            disabled={submitting || salary < auction.floor_bid.salary}
          >
            {submitting ? 'Submitting...' : yourBid ? 'Raise Bid' : 'Place Bid'}
          </button>
        </div>
      )}

      {/* Round Controls */}
      {phase !== 'CLOSED' && yourBid && (
        <div className="auction-controls">
          {phase === 'FINAL_CALL' ? (
            <button
              className="auction-controls__finalize"
              onClick={handleFinalize}
              disabled={submitting}
            >
              <Flag size={14} />
              {submitting ? 'Finalizing...' : 'Finalize Auction'}
            </button>
          ) : round < maxRounds && (
            <button
              className="auction-controls__advance"
              onClick={handleAdvanceRound}
              disabled={submitting}
            >
              <Timer size={14} />
              {submitting ? 'Advancing...' : `Advance to Round ${round + 1}`}
            </button>
          )}
        </div>
      )}

      {/* Withdraw Button */}
      {phase !== 'CLOSED' && (
        <button className="auction-withdraw" onClick={handleWithdraw}>
          Withdraw from Auction
        </button>
      )}
    </div>
  );
};

export default AuctionPane;
