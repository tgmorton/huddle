// SalaryCapContent.tsx - Salary cap overview with 6-year projection chart

import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, ChevronDown, ChevronRight, TrendingUp, AlertTriangle, CheckCircle, ExternalLink } from 'lucide-react';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  CartesianGrid,
} from 'recharts';
import { adminApi } from '../../../api/adminClient';
import type { TeamCapSummary, TeamCapPlayers, PlayerCapData } from '../../../types/admin';
import { useManagementStore } from '../../../stores/managementStore';
import { getOverallColor } from '../../../types/admin';

// === Helpers ===

const formatSalary = (value: number): string => {
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}M`;
  }
  return `$${value}K`;
};

const formatSalaryShort = (value: number): string => {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(0)}M`;
  }
  return `${value}K`;
};

const getCapHealthColor = (capSpace: number, cap: number): string => {
  const ratio = capSpace / cap;
  if (ratio > 0.15) return 'var(--success)';
  if (ratio > 0.05) return 'var(--accent)';
  return 'var(--danger)';
};

const getCapHealthStatus = (capSpace: number, cap: number): { icon: React.ReactNode; label: string; color: string } => {
  const ratio = capSpace / cap;
  if (ratio > 0.15) return { icon: <CheckCircle size={12} />, label: 'Healthy', color: 'var(--success)' };
  if (ratio > 0.05) return { icon: <TrendingUp size={12} />, label: 'Tight', color: 'var(--accent)' };
  return { icon: <AlertTriangle size={12} />, label: 'Critical', color: 'var(--danger)' };
};

// === Custom Tooltip ===

interface TooltipProps {
  active?: boolean;
  payload?: Array<{ payload: { year: number; committed: number; projected_cap: number; cap_space: number } }>;
}

const CustomTooltip: React.FC<TooltipProps> = ({ active, payload }) => {
  if (!active || !payload || !payload[0]) return null;
  const data = payload[0].payload;

  return (
    <div className="cap-chart__tooltip">
      <div className="cap-chart__tooltip-year">{data.year}</div>
      <div className="cap-chart__tooltip-row">
        <span>Committed:</span>
        <span style={{ color: getCapHealthColor(data.cap_space, data.projected_cap) }}>
          {formatSalary(data.committed)}
        </span>
      </div>
      <div className="cap-chart__tooltip-row">
        <span>Cap:</span>
        <span>{formatSalary(data.projected_cap)}</span>
      </div>
      <div className="cap-chart__tooltip-row">
        <span>Space:</span>
        <span style={{ color: getCapHealthColor(data.cap_space, data.projected_cap) }}>
          {formatSalary(data.cap_space)}
        </span>
      </div>
    </div>
  );
};

// === Player List Section ===

interface PlayerListProps {
  title: string;
  players: PlayerCapData[];
  isExpanded: boolean;
  onToggle: () => void;
  showDeadMoney?: boolean;
  showCutSavings?: boolean;
  onPlayerClick?: (playerId: string, playerName: string, position: string, overall: number) => void;
}

const PlayerList: React.FC<PlayerListProps> = ({ title, players, isExpanded, onToggle, showDeadMoney, showCutSavings, onPlayerClick }) => {
  const totalValue = players.reduce((sum, p) => sum + p.cap_hit, 0);

  // Build grid template based on which columns are shown
  const gridCols = `1fr 36px 36px 56px 32px${showDeadMoney ? ' 56px' : ''}${showCutSavings ? ' 56px' : ''}`;

  return (
    <div className="cap-players__section">
      <button className="cap-players__header" onClick={onToggle}>
        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <span className="cap-players__title">{title}</span>
        <span className="cap-players__count">({players.length})</span>
        <span className="cap-players__total">{formatSalary(totalValue)}</span>
      </button>
      {isExpanded && players.length > 0 && (
        <div className="cap-players__list">
          <div className="cap-players__table-header" style={{ gridTemplateColumns: gridCols }}>
            <span>Player</span>
            <span>Pos</span>
            <span>OVR</span>
            <span>Cap Hit</span>
            <span>Yrs</span>
            {showDeadMoney && <span>Dead $</span>}
            {showCutSavings && <span>Save</span>}
          </div>
          {players.map(player => (
            <div
              key={player.player_id}
              className="cap-players__row"
              style={{ gridTemplateColumns: gridCols }}
            >
              <span className="cap-players__name">
                {player.full_name}
                {onPlayerClick && (
                  <button
                    className="cap-players__popout"
                    onClick={() => onPlayerClick(player.player_id, player.full_name, player.position, player.overall)}
                    title="Open in workspace"
                  >
                    <ExternalLink size={10} />
                  </button>
                )}
              </span>
              <span className="cap-players__pos">{player.position}</span>
              <span className="cap-players__ovr" style={{ color: getOverallColor(player.overall) }}>
                {player.overall}
              </span>
              <span className="cap-players__salary">{formatSalary(player.cap_hit)}</span>
              <span className="cap-players__years" style={{
                color: player.years_remaining <= 1 ? 'var(--danger)' : 'var(--text-secondary)'
              }}>
                {player.years_remaining}
              </span>
              {showDeadMoney && (
                <span className="cap-players__dead" style={{ color: 'var(--danger)' }}>
                  {formatSalary(player.dead_money)}
                </span>
              )}
              {showCutSavings && (
                <span className="cap-players__save" style={{ color: 'var(--success)' }}>
                  {formatSalary(player.cut_savings)}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
      {isExpanded && players.length === 0 && (
        <div className="cap-players__empty">No players in this category</div>
      )}
    </div>
  );
};

// === Main Component ===

interface SalaryCapContentProps {
  teamAbbr?: string;
  onPlayerClick?: (playerId: string, playerName: string, position: string, overall: number) => void;
}

export const SalaryCapContent: React.FC<SalaryCapContentProps> = ({ teamAbbr: propTeamAbbr, onPlayerClick }) => {
  const [capSummary, setCapSummary] = useState<TeamCapSummary | null>(null);
  const [capPlayers, setCapPlayers] = useState<TeamCapPlayers | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Expanded states for player lists
  const [topEarnersExpanded, setTopEarnersExpanded] = useState(true);
  const [expiringExpanded, setExpiringExpanded] = useState(false);
  const [cuttableExpanded, setCuttableExpanded] = useState(false);

  // Get team abbr from management store if not provided
  const { state } = useManagementStore();
  const [teamAbbr, setTeamAbbr] = useState<string>(propTeamAbbr || 'BUF');

  const loadCapData = useCallback(async () => {
    if (!teamAbbr) return;

    setLoading(true);
    setError(null);
    try {
      const [summary, players] = await Promise.all([
        adminApi.getTeamCapSummary(teamAbbr),
        adminApi.getTeamCapPlayers(teamAbbr),
      ]);
      setCapSummary(summary);
      setCapPlayers(players);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cap data');
    } finally {
      setLoading(false);
    }
  }, [teamAbbr]);

  useEffect(() => {
    loadCapData();
  }, [loadCapData]);

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

  if (loading) return null;

  if (error) {
    return (
      <div className="ref-content">
        <div className="ref-content__error">{error}</div>
        <button className="ref-content__retry" onClick={loadCapData}>
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    );
  }

  if (!capSummary) {
    return (
      <div className="ref-content">
        <div className="ref-content__empty">No cap data available</div>
      </div>
    );
  }

  const capUsedPercent = Math.round((capSummary.cap_committed / capSummary.salary_cap) * 100);
  const healthStatus = getCapHealthStatus(capSummary.cap_space, capSummary.salary_cap);

  return (
    <div className="ref-content cap-content">
      {/* Cap Summary Header */}
      <div className="cap-summary">
        <div className="cap-summary__header">
          <span className="cap-summary__label">CAP SPACE</span>
          <span className="cap-summary__value" style={{ color: healthStatus.color }}>
            {formatSalary(capSummary.cap_space)}
          </span>
        </div>
        <div className="cap-summary__bar">
          <div
            className="cap-summary__bar-fill"
            style={{
              width: `${capUsedPercent}%`,
              backgroundColor: healthStatus.color,
            }}
          />
        </div>
        <div className="cap-summary__details">
          <div className="cap-summary__item">
            <span className="cap-summary__item-label">Committed</span>
            <span className="cap-summary__item-value">{formatSalary(capSummary.cap_committed)}</span>
          </div>
          <div className="cap-summary__item">
            <span className="cap-summary__item-label">Cap</span>
            <span className="cap-summary__item-value">{formatSalary(capSummary.salary_cap)}</span>
          </div>
          {capSummary.dead_money > 0 && (
            <div className="cap-summary__item">
              <span className="cap-summary__item-label">Dead $</span>
              <span className="cap-summary__item-value" style={{ color: 'var(--danger)' }}>
                {formatSalary(capSummary.dead_money)}
              </span>
            </div>
          )}
        </div>
        <div className="cap-summary__status" style={{ color: healthStatus.color }}>
          {healthStatus.icon}
          <span>{healthStatus.label}</span>
        </div>
      </div>

      {/* 6-Year Projection Chart */}
      <div className="cap-chart">
        <div className="cap-chart__header">6-YEAR OUTLOOK</div>
        <div className="cap-chart__container">
          <ResponsiveContainer width="100%" height={160}>
            <ComposedChart
              data={capSummary.projections}
              margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
              barGap={0}
              barCategoryGap="15%"
            >
              <CartesianGrid
                horizontal={true}
                vertical={false}
                stroke="#27272a"
                strokeWidth={1}
              />
              <XAxis
                dataKey="year"
                tickFormatter={(year) => `'${String(year).slice(-2)}`}
                tick={{ fill: '#71717a', fontSize: 9, fontFamily: 'Berkeley Mono, monospace' }}
                axisLine={{ stroke: '#27272a', strokeWidth: 1 }}
                tickLine={false}
                tickMargin={4}
              />
              <YAxis
                tickFormatter={(val) => `${Math.round(val / 1000)}M`}
                tick={{ fill: '#52525b', fontSize: 8, fontFamily: 'Berkeley Mono, monospace' }}
                axisLine={false}
                tickLine={false}
                domain={[0, 300000]}
                ticks={[0, 100000, 200000, 300000]}
                width={32}
              />
              <Tooltip
                content={<CustomTooltip />}
                cursor={{ fill: 'rgba(255,255,255,0.03)' }}
              />
              <Bar
                dataKey="committed"
                radius={0}
                maxBarSize={48}
              >
                {capSummary.projections.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={getCapHealthColor(entry.cap_space, entry.projected_cap)}
                  />
                ))}
              </Bar>
              <Line
                type="linear"
                dataKey="projected_cap"
                stroke="#52525b"
                strokeWidth={1}
                strokeDasharray="3 3"
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <div className="cap-chart__values">
          {capSummary.projections.map((proj) => (
            <span key={proj.year} className="cap-chart__value" style={{ color: getCapHealthColor(proj.cap_space, proj.projected_cap) }}>
              {formatSalaryShort(proj.committed)}
            </span>
          ))}
        </div>
      </div>

      {/* Player Lists */}
      {capPlayers && (
        <div className="cap-players">
          <PlayerList
            title="Top Earners"
            players={capPlayers.top_earners}
            isExpanded={topEarnersExpanded}
            onToggle={() => setTopEarnersExpanded(!topEarnersExpanded)}
            showDeadMoney
            showCutSavings
            onPlayerClick={onPlayerClick}
          />
          <PlayerList
            title="Expiring Contracts"
            players={capPlayers.expiring}
            isExpanded={expiringExpanded}
            onToggle={() => setExpiringExpanded(!expiringExpanded)}
            onPlayerClick={onPlayerClick}
          />
          <PlayerList
            title="Cuttable Savings"
            players={capPlayers.cuttable}
            isExpanded={cuttableExpanded}
            onToggle={() => setCuttableExpanded(!cuttableExpanded)}
            showCutSavings
            onPlayerClick={onPlayerClick}
          />
        </div>
      )}
    </div>
  );
};

export default SalaryCapContent;
