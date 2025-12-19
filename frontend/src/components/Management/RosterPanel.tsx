/**
 * RosterPanel - Displays team roster with player cards
 *
 * Design Philosophy:
 * - Players are people with stories, not stat bundles
 * - Lead with narrative/context, stats accessible but not dominant
 * - Surface things that create decisions (contract year, rookie, injury)
 */

import React, { useState, useEffect, useMemo } from 'react';
import type {
  PlayerSummary,
  PositionGroup
} from '../../types/management';
import {
  POSITION_GROUPS,
  POSITION_GROUP_NAMES
} from '../../types/management';
import './RosterPanel.css';

interface RosterPanelProps {
  teamAbbr: string;
}

export const RosterPanel: React.FC<RosterPanelProps> = ({ teamAbbr }) => {
  const [players, setPlayers] = useState<PlayerSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<PositionGroup | 'ALL'>('ALL');
  const [sortBy, setSortBy] = useState<'depth_chart' | 'overall' | 'age'>('depth_chart');

  useEffect(() => {
    const fetchRoster = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(
          `/api/v1/admin/teams/${teamAbbr}/roster?sort_by=${sortBy}`
        );
        if (!response.ok) {
          throw new Error('Failed to load roster');
        }
        const data = await response.json();
        setPlayers(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    if (teamAbbr) {
      fetchRoster();
    }
  }, [teamAbbr, sortBy]);

  // Group players by position group
  const groupedPlayers = useMemo(() => {
    const groups: Record<PositionGroup, PlayerSummary[]> = {
      QB: [], RB: [], WR: [], TE: [], OL: [], DL: [], LB: [], DB: [], ST: []
    };

    players.forEach(player => {
      for (const [group, positions] of Object.entries(POSITION_GROUPS)) {
        if (positions.includes(player.position)) {
          groups[group as PositionGroup].push(player);
          break;
        }
      }
    });

    return groups;
  }, [players]);

  // Filter based on selected group
  const displayPlayers = useMemo(() => {
    if (selectedGroup === 'ALL') {
      return players;
    }
    return groupedPlayers[selectedGroup];
  }, [players, groupedPlayers, selectedGroup]);

  if (loading) {
    return (
      <div className="roster-panel roster-panel--loading">
        <div className="roster-panel__loader">Loading roster...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="roster-panel roster-panel--error">
        <div className="roster-panel__error">{error}</div>
      </div>
    );
  }

  const positionGroups: (PositionGroup | 'ALL')[] = ['ALL', 'QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'DB', 'ST'];

  return (
    <div className="roster-panel">
      {/* Header with team info */}
      <div className="roster-panel__header">
        <div className="roster-panel__title">
          <span className="roster-panel__team">{teamAbbr}</span>
          <span className="roster-panel__count">{players.length} Players</span>
        </div>

        {/* Sort dropdown */}
        <select
          className="roster-panel__sort"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
        >
          <option value="depth_chart">By Position</option>
          <option value="overall">By Overall</option>
          <option value="age">By Age</option>
        </select>
      </div>

      {/* Position group filter */}
      <div className="roster-panel__filters">
        {positionGroups.map(group => (
          <button
            key={group}
            className={`roster-panel__filter ${selectedGroup === group ? 'active' : ''}`}
            onClick={() => setSelectedGroup(group)}
          >
            {group === 'ALL' ? 'All' : group}
            <span className="roster-panel__filter-count">
              {group === 'ALL' ? players.length : groupedPlayers[group].length}
            </span>
          </button>
        ))}
      </div>

      {/* Player list */}
      <div className="roster-panel__list">
        {selectedGroup === 'ALL' ? (
          // Show grouped view when ALL selected
          Object.entries(groupedPlayers).map(([group, groupPlayers]) => {
            if (groupPlayers.length === 0) return null;
            return (
              <div key={group} className="roster-panel__group">
                <div className="roster-panel__group-header">
                  {POSITION_GROUP_NAMES[group as PositionGroup]}
                  <span className="roster-panel__group-count">({groupPlayers.length})</span>
                </div>
                <div className="roster-panel__group-players">
                  {groupPlayers.map(player => (
                    <PlayerCard key={player.id} player={player} />
                  ))}
                </div>
              </div>
            );
          })
        ) : (
          // Show flat list for specific position group
          <div className="roster-panel__group-players">
            {displayPlayers.map(player => (
              <PlayerCard key={player.id} player={player} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

interface PlayerCardProps {
  player: PlayerSummary;
}

const PlayerCard: React.FC<PlayerCardProps> = ({ player }) => {
  // Determine player "tags" - things that make them notable
  const tags: { label: string; type: 'info' | 'warning' | 'success' | 'danger' }[] = [];

  if (player.experience === 0) {
    tags.push({ label: 'Rookie', type: 'info' });
  } else if (player.experience >= 10) {
    tags.push({ label: 'Veteran', type: 'success' });
  }

  if (player.potential > player.overall + 5) {
    tags.push({ label: 'High Ceiling', type: 'info' });
  }

  if (player.age >= 32) {
    tags.push({ label: 'Aging', type: 'warning' });
  }

  // Overall rating color
  const getOverallClass = (ovr: number) => {
    if (ovr >= 85) return 'elite';
    if (ovr >= 75) return 'starter';
    if (ovr >= 65) return 'backup';
    return 'depth';
  };

  return (
    <div className="player-card">
      <div className="player-card__jersey">#{player.jersey_number}</div>

      <div className="player-card__info">
        <div className="player-card__name">
          {player.first_name} <span className="player-card__lastname">{player.last_name}</span>
        </div>
        <div className="player-card__meta">
          <span className="player-card__position">{player.position}</span>
          <span className="player-card__separator">•</span>
          <span className="player-card__age">{player.age} yrs</span>
          <span className="player-card__separator">•</span>
          <span className="player-card__exp">
            {player.experience === 0 ? 'R' : `${player.experience} yr${player.experience > 1 ? 's' : ''}`}
          </span>
        </div>
        {tags.length > 0 && (
          <div className="player-card__tags">
            {tags.map((tag, i) => (
              <span key={i} className={`player-card__tag player-card__tag--${tag.type}`}>
                {tag.label}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="player-card__ratings">
        <div className={`player-card__overall player-card__overall--${getOverallClass(player.overall)}`}>
          {player.overall}
        </div>
        <div className="player-card__potential" title="Potential">
          {player.potential}
        </div>
      </div>
    </div>
  );
};

export default RosterPanel;
