// StatsTable.tsx - Reusable stats table component
// Supports compact (420px sideview) and full (1440px pop-out) variants

import React from 'react';
import type { PlayerSeasonRow, StatColumnDef, StatPositionGroup } from '../../../types/stats';
import { STAT_COLUMNS_COMPACT, STAT_COLUMNS_FULL } from '../constants';
import { POSITION_TO_STAT_GROUP } from '../../../types/stats';

// === Helpers ===

function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  const parts = path.split('.');
  let value: unknown = obj;
  for (const part of parts) {
    if (value === null || value === undefined) return undefined;
    value = (value as Record<string, unknown>)[part];
  }
  return value;
}

function formatStatValue(
  value: unknown,
  format?: 'number' | 'pct' | 'decimal',
  decimals = 1
): string {
  if (value === null || value === undefined) return '-';

  const num = Number(value);
  if (isNaN(num)) return String(value);

  switch (format) {
    case 'pct':
      return `${num.toFixed(1)}%`;
    case 'decimal':
      return num.toFixed(decimals);
    default:
      return num.toLocaleString();
  }
}

// === StatsTable Component ===

interface StatsTableProps {
  /** Player career stats to display */
  seasons: PlayerSeasonRow[];
  /** Career totals row */
  careerTotals?: PlayerSeasonRow;
  /** Player position (e.g., 'QB', 'RB', 'WR') */
  position: string;
  /** Table variant - compact for sideview, full for pop-out */
  variant?: 'compact' | 'full';
  /** Optional maximum seasons to show (most recent first) */
  maxSeasons?: number;
  /** Show career row at bottom */
  showCareer?: boolean;
  /** Click handler for season row */
  onSeasonClick?: (season: PlayerSeasonRow) => void;
  /** Optional class name */
  className?: string;
}

export const StatsTable: React.FC<StatsTableProps> = ({
  seasons,
  careerTotals,
  position,
  variant = 'compact',
  maxSeasons,
  showCareer = true,
  onSeasonClick,
  className = '',
}) => {
  // Get stat group from position
  const statGroup = POSITION_TO_STAT_GROUP[position] as StatPositionGroup | undefined;
  if (!statGroup) {
    return (
      <div className="stats-table__empty">
        No stats available for position: {position}
      </div>
    );
  }

  // Get columns based on variant
  const columns = variant === 'full'
    ? STAT_COLUMNS_FULL[statGroup]
    : STAT_COLUMNS_COMPACT[statGroup];

  if (!columns) {
    return (
      <div className="stats-table__empty">
        No column definitions for: {statGroup}
      </div>
    );
  }

  // Filter and sort seasons (most recent first)
  const displaySeasons = [...seasons]
    .sort((a, b) => b.season - a.season)
    .slice(0, maxSeasons);

  return (
    <div className={`stats-table-container ${className}`}>
      <table className={`stats-table stats-table--${variant}`}>
        <thead>
          <tr>
            {variant === 'compact' && (
              <th className="stats-table__year">YR</th>
            )}
            {columns.map((col) => (
              <th
                key={col.key}
                style={{
                  width: col.width,
                  textAlign: col.align,
                }}
              >
                {col.abbr}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {displaySeasons.map((row) => (
            <tr
              key={row.season}
              className="stats-table__row"
              onClick={() => onSeasonClick?.(row)}
              style={{ cursor: onSeasonClick ? 'pointer' : undefined }}
            >
              {variant === 'compact' && (
                <td className="stats-table__year">{row.season}</td>
              )}
              {columns.map((col) => {
                const value = getNestedValue(row as unknown as Record<string, unknown>, col.key);
                return (
                  <td
                    key={col.key}
                    style={{ textAlign: col.align }}
                  >
                    {formatStatValue(value, col.format, col.decimals)}
                  </td>
                );
              })}
            </tr>
          ))}
          {showCareer && careerTotals && (
            <tr className="stats-table__career">
              {variant === 'compact' && (
                <td className="stats-table__year">CAR</td>
              )}
              {columns.map((col) => {
                // For career row in full variant, replace season with 'Career'
                if (col.key === 'season') {
                  return (
                    <td key={col.key} style={{ textAlign: col.align }}>
                      Career
                    </td>
                  );
                }
                // For team_abbr in career row, show empty or count
                if (col.key === 'team_abbr') {
                  const teamCount = new Set(seasons.map(s => s.team_abbr)).size;
                  return (
                    <td key={col.key} style={{ textAlign: col.align }}>
                      {teamCount > 1 ? `${teamCount} TM` : careerTotals.team_abbr}
                    </td>
                  );
                }
                const value = getNestedValue(careerTotals as unknown as Record<string, unknown>, col.key);
                return (
                  <td key={col.key} style={{ textAlign: col.align }}>
                    {formatStatValue(value, col.format, col.decimals)}
                  </td>
                );
              })}
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

// === League Leaders Table ===

interface LeagueLeader {
  rank: number;
  player_id: string;
  player_name: string;
  team_abbr: string;
  position: string;
  value: number;
  games_played: number;
}

interface LeagueLeadersTableProps {
  /** Category title (e.g., "PASSING YARDS") */
  title: string;
  /** List of leaders */
  leaders: LeagueLeader[];
  /** Value format */
  format?: 'number' | 'pct' | 'decimal';
  /** Click handler for player */
  onPlayerClick?: (playerId: string) => void;
  /** Optional limit (default 10) */
  limit?: number;
  /** Optional class name */
  className?: string;
}

export const LeagueLeadersTable: React.FC<LeagueLeadersTableProps> = ({
  title,
  leaders,
  format = 'number',
  onPlayerClick,
  limit = 10,
  className = '',
}) => {
  const displayLeaders = leaders.slice(0, limit);

  return (
    <div className={`league-leaders ${className}`}>
      <div className="league-leaders__title">{title}</div>
      <table className="league-leaders__table">
        <tbody>
          {displayLeaders.map((leader) => (
            <tr
              key={leader.player_id}
              className="league-leaders__row"
              onClick={() => onPlayerClick?.(leader.player_id)}
              style={{ cursor: onPlayerClick ? 'pointer' : undefined }}
            >
              <td className="league-leaders__rank">{leader.rank}.</td>
              <td className="league-leaders__name">{leader.player_name}</td>
              <td className="league-leaders__team">{leader.team_abbr}</td>
              <td className="league-leaders__pos">{leader.position}</td>
              <td className="league-leaders__value">
                {formatStatValue(leader.value, format)}
              </td>
              <td className="league-leaders__games">{leader.games_played} GP</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default StatsTable;
