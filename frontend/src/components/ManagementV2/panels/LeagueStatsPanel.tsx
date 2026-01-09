// LeagueStatsPanel.tsx - League leaders and stats reference panel
// Wide panel (640px) with category tabs for stat leaders

import React, { useState, useMemo } from 'react';
import { generateMockLeagueLeaders } from '../../../utils/mockStats';
import { LeagueLeadersTable } from '../components/StatsTable';
import type { StatCategory } from '../../../types/stats';

type LeagueTab = 'passing' | 'rushing' | 'receiving' | 'defense' | 'kicking';

interface LeagueStatsPanelProps {
  onAddPlayerToWorkspace?: (player: { id: string; name: string; position: string; overall: number }) => void;
}

// Category titles for display
const CATEGORY_TITLES: Record<StatCategory, string[]> = {
  passing: ['PASSING YARDS', 'PASSING TOUCHDOWNS', 'PASSER RATING', 'COMPLETIONS'],
  rushing: ['RUSHING YARDS', 'RUSHING TOUCHDOWNS', 'YARDS PER CARRY'],
  receiving: ['RECEIVING YARDS', 'RECEPTIONS', 'RECEIVING TOUCHDOWNS'],
  defense: ['TACKLES', 'SACKS', 'INTERCEPTIONS', 'PASSES DEFENDED'],
  kicking: ['FIELD GOAL %', 'FIELD GOALS MADE', 'POINTS'],
};

export const LeagueStatsPanel: React.FC<LeagueStatsPanelProps> = ({
  onAddPlayerToWorkspace,
}) => {
  const [tab, setTab] = useState<LeagueTab>('passing');

  // Generate mock league leaders (memoized)
  const leagueLeaders = useMemo(() => {
    return generateMockLeagueLeaders();
  }, []);

  // Get leaders for current category
  const categoryLeaders = leagueLeaders.filter(l => l.category === tab);

  // Handle player click - open player pane
  const handlePlayerClick = (playerId: string) => {
    // Find player info from leaders data
    for (const category of leagueLeaders) {
      const leader = category.leaders.find(l => l.player_id === playerId);
      if (leader && onAddPlayerToWorkspace) {
        onAddPlayerToWorkspace({
          id: playerId,
          name: leader.player_name,
          position: leader.position,
          overall: 85, // Placeholder - in real implementation would fetch actual overall
        });
        break;
      }
    }
  };

  return (
    <div className="tabbed-panel tabbed-panel--league">
      <div className="tabbed-panel__tabs tabbed-panel__tabs--scrollable">
        <button
          className={`tabbed-panel__tab ${tab === 'passing' ? 'tabbed-panel__tab--active' : ''}`}
          onClick={() => setTab('passing')}
        >
          Passing
        </button>
        <button
          className={`tabbed-panel__tab ${tab === 'rushing' ? 'tabbed-panel__tab--active' : ''}`}
          onClick={() => setTab('rushing')}
        >
          Rushing
        </button>
        <button
          className={`tabbed-panel__tab ${tab === 'receiving' ? 'tabbed-panel__tab--active' : ''}`}
          onClick={() => setTab('receiving')}
        >
          Receiving
        </button>
        <button
          className={`tabbed-panel__tab ${tab === 'defense' ? 'tabbed-panel__tab--active' : ''}`}
          onClick={() => setTab('defense')}
        >
          Defense
        </button>
        <button
          className={`tabbed-panel__tab ${tab === 'kicking' ? 'tabbed-panel__tab--active' : ''}`}
          onClick={() => setTab('kicking')}
        >
          Kicking
        </button>
      </div>
      <div className="tabbed-panel__content league-stats-content">
        {categoryLeaders.length > 0 ? (
          categoryLeaders.map((category, idx) => (
            <LeagueLeadersTable
              key={`${category.category}-${category.stat}-${idx}`}
              title={CATEGORY_TITLES[tab]?.[idx] || category.stat_label}
              leaders={category.leaders}
              format={category.stat.includes('pct') || category.stat.includes('rating') ? 'decimal' : 'number'}
              onPlayerClick={handlePlayerClick}
              limit={10}
            />
          ))
        ) : (
          <div className="league-stats-empty">
            No stats available for this category
          </div>
        )}
      </div>
    </div>
  );
};

export default LeagueStatsPanel;
