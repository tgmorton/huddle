/**
 * SituationStats - Game statistics and conversion rates panel
 *
 * Displays:
 * - Third down conversions
 * - Red zone efficiency
 * - Time of possession
 * - Total yards breakdown
 * - Turnover margin
 */

import React from 'react';
import { Activity, Clock, TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface GameStatsData {
  thirdDownAttempts: number;
  thirdDownConversions: number;
  redZoneAttempts: number;
  redZoneTDs: number;
  redZoneFGs: number;
  timeOfPossession: string;
  totalYards: number;
  passingYards: number;
  rushingYards: number;
  turnovers: number;
  opponentTurnovers: number;
  firstDowns?: number;
  penalties?: number;
  penaltyYards?: number;
}

interface SituationStatsProps {
  stats?: Partial<GameStatsData>;
  opponentStats?: Partial<GameStatsData>;
  showComparison?: boolean;
  className?: string;
}

// Default mock data
const DEFAULT_STATS: GameStatsData = {
  thirdDownAttempts: 7,
  thirdDownConversions: 4,
  redZoneAttempts: 3,
  redZoneTDs: 2,
  redZoneFGs: 0,
  timeOfPossession: '18:42',
  totalYards: 287,
  passingYards: 198,
  rushingYards: 89,
  turnovers: 1,
  opponentTurnovers: 2,
  firstDowns: 14,
  penalties: 4,
  penaltyYards: 35,
};

export const SituationStats: React.FC<SituationStatsProps> = ({
  stats = DEFAULT_STATS,
  opponentStats,
  showComparison = false,
  className = '',
}) => {
  const thirdDownPct = stats.thirdDownAttempts
    ? Math.round((stats.thirdDownConversions || 0) / stats.thirdDownAttempts * 100)
    : 0;

  const redZonePct = stats.redZoneAttempts
    ? Math.round(((stats.redZoneTDs || 0) + (stats.redZoneFGs || 0)) / stats.redZoneAttempts * 100)
    : 0;

  const turnoverMargin = (stats.opponentTurnovers || 0) - (stats.turnovers || 0);

  return (
    <div className={`situation-stats ${className}`}>
      {/* Efficiency Section */}
      <div className="situation-stats__section">
        <h4 className="situation-stats__section-title">
          <Activity size={12} />
          EFFICIENCY
        </h4>

        {/* Third Down */}
        <div className="situation-stats__stat">
          <span className="situation-stats__stat-label">3rd Down</span>
          <div className="situation-stats__stat-detail">
            <span className="situation-stats__stat-value">
              {stats.thirdDownConversions || 0}/{stats.thirdDownAttempts || 0}
            </span>
            <span className={`situation-stats__stat-pct ${thirdDownPct >= 50 ? 'good' : thirdDownPct >= 35 ? 'average' : 'poor'}`}>
              ({thirdDownPct}%)
            </span>
            <EfficiencyIcon percentage={thirdDownPct} threshold={40} />
          </div>
        </div>

        {/* Red Zone */}
        <div className="situation-stats__stat">
          <span className="situation-stats__stat-label">Red Zone</span>
          <div className="situation-stats__stat-detail">
            <span className="situation-stats__stat-value">
              {stats.redZoneTDs || 0} TD, {stats.redZoneFGs || 0} FG / {stats.redZoneAttempts || 0}
            </span>
            <span className={`situation-stats__stat-pct ${redZonePct >= 70 ? 'good' : redZonePct >= 50 ? 'average' : 'poor'}`}>
              ({redZonePct}%)
            </span>
          </div>
        </div>
      </div>

      {/* Possession Section */}
      <div className="situation-stats__section">
        <h4 className="situation-stats__section-title">
          <Clock size={12} />
          POSSESSION
        </h4>

        <div className="situation-stats__stat">
          <span className="situation-stats__stat-label">Time of Poss</span>
          <span className="situation-stats__stat-value">{stats.timeOfPossession || '0:00'}</span>
        </div>

        {stats.firstDowns !== undefined && (
          <div className="situation-stats__stat">
            <span className="situation-stats__stat-label">First Downs</span>
            <span className="situation-stats__stat-value">{stats.firstDowns}</span>
          </div>
        )}
      </div>

      {/* Yardage Section */}
      <div className="situation-stats__section">
        <h4 className="situation-stats__section-title">YARDAGE</h4>

        <div className="situation-stats__stat">
          <span className="situation-stats__stat-label">Total Yards</span>
          <span className="situation-stats__stat-value situation-stats__stat-value--large">
            {stats.totalYards || 0}
          </span>
        </div>

        <div className="situation-stats__yards-breakdown">
          <div className="situation-stats__yards-bar">
            <div
              className="situation-stats__yards-pass"
              style={{ width: `${((stats.passingYards || 0) / (stats.totalYards || 1)) * 100}%` }}
              title={`Passing: ${stats.passingYards || 0}`}
            />
            <div
              className="situation-stats__yards-rush"
              style={{ width: `${((stats.rushingYards || 0) / (stats.totalYards || 1)) * 100}%` }}
              title={`Rushing: ${stats.rushingYards || 0}`}
            />
          </div>
          <div className="situation-stats__yards-labels">
            <span>Pass: {stats.passingYards || 0}</span>
            <span>Rush: {stats.rushingYards || 0}</span>
          </div>
        </div>
      </div>

      {/* Turnover Section */}
      <div className="situation-stats__section">
        <h4 className="situation-stats__section-title">TURNOVERS</h4>

        <div className="situation-stats__stat">
          <span className="situation-stats__stat-label">TO Margin</span>
          <span className={`situation-stats__stat-value situation-stats__stat-value--margin ${turnoverMargin > 0 ? 'positive' : turnoverMargin < 0 ? 'negative' : ''}`}>
            {turnoverMargin > 0 ? '+' : ''}{turnoverMargin}
          </span>
        </div>

        <div className="situation-stats__turnover-detail">
          <span>Lost: {stats.turnovers || 0}</span>
          <span>Forced: {stats.opponentTurnovers || 0}</span>
        </div>
      </div>

      {/* Penalties (if tracked) */}
      {stats.penalties !== undefined && (
        <div className="situation-stats__section">
          <h4 className="situation-stats__section-title">PENALTIES</h4>
          <div className="situation-stats__stat">
            <span className="situation-stats__stat-value">
              {stats.penalties}-{stats.penaltyYards || 0}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

const EfficiencyIcon: React.FC<{ percentage: number; threshold: number }> = ({ percentage, threshold }) => {
  if (percentage >= threshold + 15) {
    return <TrendingUp size={12} className="situation-stats__icon situation-stats__icon--up" />;
  }
  if (percentage < threshold - 10) {
    return <TrendingDown size={12} className="situation-stats__icon situation-stats__icon--down" />;
  }
  return <Minus size={12} className="situation-stats__icon situation-stats__icon--neutral" />;
};

export default SituationStats;
