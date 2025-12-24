// DevelopmentContent.tsx - Weekly development gains view
// Shows players who improved this week through practice

import React, { useState, useEffect } from 'react';
import { TrendingUp } from 'lucide-react';
import { PlayerPortrait } from '../components';
import { useManagementStore, selectLeagueId, selectFranchiseId } from '../../../stores/managementStore';
import { managementApi } from '../../../api/managementClient';
import type { PlayerWeeklyGain } from '../../../api/managementClient';

// === Helpers ===

// Format attribute name for display
const formatAttrName = (attr: string): string => {
  return attr
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

// Sort gains by value descending
const sortGains = (gains: Record<string, number>): [string, number][] => {
  return Object.entries(gains).sort(([, a], [, b]) => b - a);
};

// === Components ===

interface GainCardProps {
  player: PlayerWeeklyGain;
  leagueId?: string;
}

const GainCard: React.FC<GainCardProps> = ({ player, leagueId }) => {
  const sortedGains = sortGains(player.gains);
  const totalGain = Object.values(player.gains).reduce((sum, g) => sum + g, 0);

  return (
    <div className="gain-card">
      <div className="gain-card__player">
        <PlayerPortrait
          playerId={player.player_id}
          leagueId={leagueId}
          size="roster"
        />
        <div className="gain-card__info">
          <span className="gain-card__name">{player.name}</span>
          <span className="gain-card__meta">{player.position}</span>
        </div>
      </div>
      <div className="gain-card__gains">
        {sortedGains.map(([attr, value]) => (
          <span key={attr} className="gain-card__gain">
            <TrendingUp size={12} className="gain-card__gain-icon" />
            +{value.toFixed(1)} {formatAttrName(attr)}
          </span>
        ))}
      </div>
      <div className="gain-card__total">
        <span className="gain-card__total-value">+{totalGain.toFixed(1)}</span>
      </div>
    </div>
  );
};

// === Main Component ===

export const DevelopmentContent: React.FC = () => {
  const [players, setPlayers] = useState<PlayerWeeklyGain[]>([]);
  const [week, setWeek] = useState(0);
  const [loading, setLoading] = useState(true);

  const leagueId = useManagementStore(selectLeagueId);
  const franchiseId = useManagementStore(selectFranchiseId);

  useEffect(() => {
    if (!franchiseId) {
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      try {
        const data = await managementApi.getWeeklyDevelopment(franchiseId);
        setPlayers(data.players);
        setWeek(data.week);
      } catch (err) {
        console.error('Failed to fetch weekly development data:', err);
        setPlayers([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [franchiseId]);

  if (loading) {
    return <div className="ref-content development-content">Loading...</div>;
  }

  // Calculate summary stats
  const totalPoints = players.reduce(
    (sum, p) => sum + Object.values(p.gains).reduce((s, g) => s + g, 0),
    0
  );

  // Sort by total gains (most improved first)
  const sortedPlayers = [...players].sort((a, b) => {
    const totalA = Object.values(a.gains).reduce((s, g) => s + g, 0);
    const totalB = Object.values(b.gains).reduce((s, g) => s + g, 0);
    return totalB - totalA;
  });

  return (
    <div className="ref-content development-content">
      {/* Week Header */}
      <div className="development-content__header">
        <span className="development-content__week">Week {week}</span>
      </div>

      {/* Summary Stats */}
      {players.length > 0 && (
        <div className="development-content__summary">
          <div className="development-content__stat">
            <span className="development-content__stat-value">{players.length}</span>
            <span className="development-content__stat-label">Players Improved</span>
          </div>
          <div className="development-content__stat">
            <span className="development-content__stat-value">+{totalPoints.toFixed(1)}</span>
            <span className="development-content__stat-label">Total Points</span>
          </div>
        </div>
      )}

      {/* Player Cards */}
      {sortedPlayers.length > 0 && (
        <div className="development-content__list">
          {sortedPlayers.map(player => (
            <GainCard
              key={player.player_id}
              player={player}
              leagueId={leagueId || undefined}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {players.length === 0 && !loading && (
        <div className="development-content__empty">
          <p>No development this week</p>
          <p className="development-content__hint">
            Run practice with Development focus to improve players.
          </p>
        </div>
      )}
    </div>
  );
};

export default DevelopmentContent;
