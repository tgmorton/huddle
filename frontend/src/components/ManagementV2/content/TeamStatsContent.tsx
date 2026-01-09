// TeamStatsContent.tsx - Dense spreadsheet view of all player stats on the team
// FOF9-style sortable stats table with position filtering

import React, { useState, useMemo, useEffect } from 'react';
import { ArrowUp, ArrowDown, Filter } from 'lucide-react';
import { adminApi } from '../../../api/adminClient';
import type { RosterPlayer } from '../../../types/admin';
import { useManagementStore, selectFranchiseId } from '../../../stores/managementStore';
import { generateMockSeasonStats } from '../../../utils/mockStats';
import type { PlayerSeasonRow, StatPositionGroup } from '../../../types/stats';
import { POSITION_TO_STAT_GROUP } from '../../../types/stats';
import { STAT_COLUMNS_COMPACT } from '../constants';

// Position group filter options
const POSITION_GROUPS: { value: StatPositionGroup | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'QB', label: 'QB' },
  { value: 'RB', label: 'RB' },
  { value: 'WR', label: 'WR' },
  { value: 'TE', label: 'TE' },
  { value: 'OL', label: 'OL' },
  { value: 'DL', label: 'DL' },
  { value: 'LB', label: 'LB' },
  { value: 'DB', label: 'DB' },
  { value: 'K', label: 'K' },
  { value: 'P', label: 'P' },
];

type SortConfig = {
  key: string;
  direction: 'asc' | 'desc';
};

interface PlayerWithStats {
  player: RosterPlayer;
  stats: PlayerSeasonRow;
}

// Get nested value from object using dot notation
function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  const parts = path.split('.');
  let value: unknown = obj;
  for (const part of parts) {
    if (value === null || value === undefined) return undefined;
    value = (value as Record<string, unknown>)[part];
  }
  return value;
}

export const TeamStatsContent: React.FC = () => {
  const [roster, setRoster] = useState<RosterPlayer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [positionFilter, setPositionFilter] = useState<StatPositionGroup | 'all'>('all');
  const [sortConfig, setSortConfig] = useState<SortConfig>({ key: 'player.overall', direction: 'desc' });

  const franchiseId = useManagementStore(selectFranchiseId);

  // Fetch roster
  useEffect(() => {
    const fetchRoster = async () => {
      if (!franchiseId) {
        setError('No franchise selected');
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const data = await adminApi.getRoster(franchiseId);
        setRoster(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load roster');
      } finally {
        setLoading(false);
      }
    };
    fetchRoster();
  }, [franchiseId]);

  // Generate mock stats for each player
  const playersWithStats: PlayerWithStats[] = useMemo(() => {
    return roster.map(player => ({
      player,
      stats: generateMockSeasonStats(
        player.position,
        player.overall,
        player.experience,
        2024 // Current season
      ),
    }));
  }, [roster]);

  // Filter by position group
  const filteredPlayers = useMemo(() => {
    if (positionFilter === 'all') return playersWithStats;
    return playersWithStats.filter(p =>
      POSITION_TO_STAT_GROUP[p.player.position] === positionFilter
    );
  }, [playersWithStats, positionFilter]);

  // Sort players
  const sortedPlayers = useMemo(() => {
    return [...filteredPlayers].sort((a, b) => {
      let aVal: unknown;
      let bVal: unknown;

      if (sortConfig.key.startsWith('player.')) {
        const key = sortConfig.key.replace('player.', '') as keyof RosterPlayer;
        aVal = a.player[key];
        bVal = b.player[key];
      } else {
        aVal = getNestedValue(a.stats as unknown as Record<string, unknown>, sortConfig.key);
        bVal = getNestedValue(b.stats as unknown as Record<string, unknown>, sortConfig.key);
      }

      // Handle undefined values
      if (aVal === undefined && bVal === undefined) return 0;
      if (aVal === undefined) return 1;
      if (bVal === undefined) return -1;

      // Compare values
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
      }

      const aStr = String(aVal);
      const bStr = String(bVal);
      return sortConfig.direction === 'asc'
        ? aStr.localeCompare(bStr)
        : bStr.localeCompare(aStr);
    });
  }, [filteredPlayers, sortConfig]);

  // Handle sort column click
  const handleSort = (key: string) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc',
    }));
  };

  // Get stat columns for display based on position filter
  const getStatColumns = () => {
    if (positionFilter === 'all') {
      // Show generic columns when no position filter
      return [
        { key: 'games_played', label: 'Games', abbr: 'G', width: 32, align: 'right' as const },
        { key: 'games_started', label: 'Starts', abbr: 'GS', width: 32, align: 'right' as const },
      ];
    }
    return STAT_COLUMNS_COMPACT[positionFilter] || [];
  };

  const statColumns = getStatColumns();

  if (loading) {
    return <div className="team-stats-content team-stats-content--loading">Loading...</div>;
  }

  if (error) {
    return <div className="team-stats-content team-stats-content--error">{error}</div>;
  }

  return (
    <div className="team-stats-content">
      {/* Filter bar */}
      <div className="team-stats__filter-bar">
        <Filter size={14} />
        <div className="team-stats__filter-chips">
          {POSITION_GROUPS.map(group => (
            <button
              key={group.value}
              className={`team-stats__filter-chip ${positionFilter === group.value ? 'team-stats__filter-chip--active' : ''}`}
              onClick={() => setPositionFilter(group.value)}
            >
              {group.label}
            </button>
          ))}
        </div>
      </div>

      {/* Stats table */}
      <div className="team-stats__table-container">
        <table className="team-stats__table">
          <thead>
            <tr>
              <th
                className="team-stats__th team-stats__th--sortable team-stats__th--sticky"
                onClick={() => handleSort('player.full_name')}
              >
                Player
                {sortConfig.key === 'player.full_name' && (
                  sortConfig.direction === 'desc' ? <ArrowDown size={10} /> : <ArrowUp size={10} />
                )}
              </th>
              <th
                className="team-stats__th team-stats__th--sortable"
                onClick={() => handleSort('player.position')}
              >
                Pos
                {sortConfig.key === 'player.position' && (
                  sortConfig.direction === 'desc' ? <ArrowDown size={10} /> : <ArrowUp size={10} />
                )}
              </th>
              <th
                className="team-stats__th team-stats__th--sortable"
                onClick={() => handleSort('player.overall')}
              >
                OVR
                {sortConfig.key === 'player.overall' && (
                  sortConfig.direction === 'desc' ? <ArrowDown size={10} /> : <ArrowUp size={10} />
                )}
              </th>
              {statColumns.map(col => (
                <th
                  key={col.key}
                  className="team-stats__th team-stats__th--sortable"
                  style={{ width: col.width, textAlign: col.align }}
                  onClick={() => handleSort(col.key)}
                >
                  {col.abbr}
                  {sortConfig.key === col.key && (
                    sortConfig.direction === 'desc' ? <ArrowDown size={10} /> : <ArrowUp size={10} />
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedPlayers.map(({ player, stats }) => (
              <tr key={player.id} className="team-stats__tr">
                <td className="team-stats__td team-stats__td--name team-stats__td--sticky">
                  <span className="team-stats__jersey">#{player.jersey_number}</span>
                  {player.full_name}
                </td>
                <td className="team-stats__td team-stats__td--pos">{player.position}</td>
                <td className="team-stats__td team-stats__td--ovr">{player.overall}</td>
                {statColumns.map(col => {
                  const value = getNestedValue(stats as unknown as Record<string, unknown>, col.key);
                  const formatted = value === undefined || value === null
                    ? '-'
                    : typeof value === 'number'
                      ? (col.format === 'pct' || col.format === 'decimal')
                        ? value.toFixed(1)
                        : value.toLocaleString()
                      : String(value);
                  return (
                    <td
                      key={col.key}
                      className="team-stats__td"
                      style={{ textAlign: col.align }}
                    >
                      {formatted}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="team-stats__footer">
        <span>{sortedPlayers.length} players</span>
      </div>
    </div>
  );
};

export default TeamStatsContent;
