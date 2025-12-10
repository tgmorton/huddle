/**
 * StatsPanel - Display team and game statistics
 */

import { useEffect, useState } from 'react';
import { useGameStore } from '../../stores/gameStore';
import { gamesApi } from '../../api/client';
import './StatsPanel.css';

interface TeamStats {
  plays: number;
  total_yards: number;
  passing_yards: number;
  rushing_yards: number;
  first_downs: number;
  third_down_conversions: number;
  third_down_attempts: number;
  fourth_down_conversions: number;
  fourth_down_attempts: number;
  turnovers: number;
  penalties: number;
  penalty_yards: number;
  time_of_possession: string;
}

interface StatsData {
  home: TeamStats;
  away: TeamStats;
}

const defaultStats: TeamStats = {
  plays: 0,
  total_yards: 0,
  passing_yards: 0,
  rushing_yards: 0,
  first_downs: 0,
  third_down_conversions: 0,
  third_down_attempts: 0,
  fourth_down_conversions: 0,
  fourth_down_attempts: 0,
  turnovers: 0,
  penalties: 0,
  penalty_yards: 0,
  time_of_possession: '0:00',
};

export function StatsPanel() {
  const { gameId, homeTeam, awayTeam, playLog } = useGameStore();
  const [stats, setStats] = useState<StatsData | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch stats when play count changes
  useEffect(() => {
    if (!gameId) return;

    const fetchStats = async () => {
      setIsLoading(true);
      try {
        const data = await gamesApi.getTeamStats(gameId);
        setStats(data as unknown as StatsData);
      } catch (err) {
        console.error('Failed to fetch stats:', err);
      } finally {
        setIsLoading(false);
      }
    };

    // Debounce - only fetch every 5 plays or so
    if (playLog.length % 5 === 0 || playLog.length <= 1) {
      fetchStats();
    }
  }, [gameId, playLog.length]);

  if (!homeTeam || !awayTeam) {
    return (
      <div className="stats-panel stats-panel--loading">
        <p>Waiting for game...</p>
      </div>
    );
  }

  const homeStats = stats?.home || defaultStats;
  const awayStats = stats?.away || defaultStats;

  const statRows = [
    { label: 'Total Yards', home: homeStats.total_yards, away: awayStats.total_yards },
    { label: 'Passing Yards', home: homeStats.passing_yards, away: awayStats.passing_yards },
    { label: 'Rushing Yards', home: homeStats.rushing_yards, away: awayStats.rushing_yards },
    { label: 'First Downs', home: homeStats.first_downs, away: awayStats.first_downs },
    {
      label: '3rd Down',
      home: `${homeStats.third_down_conversions}/${homeStats.third_down_attempts}`,
      away: `${awayStats.third_down_conversions}/${awayStats.third_down_attempts}`,
      isRatio: true,
    },
    { label: 'Turnovers', home: homeStats.turnovers, away: awayStats.turnovers, inverse: true },
    { label: 'Penalties', home: `${homeStats.penalties} (${homeStats.penalty_yards} yds)`, away: `${awayStats.penalties} (${awayStats.penalty_yards} yds)`, isRatio: true },
    { label: 'Plays', home: homeStats.plays, away: awayStats.plays },
  ];

  return (
    <div className="stats-panel">
      <div className="stats-panel__header">
        <span>Team Stats</span>
        {isLoading && <span className="stats-panel__loading">Updating...</span>}
      </div>

      <div className="stats-panel__teams">
        <div
          className="stats-panel__team-header"
          style={{ '--team-color': homeTeam.primary_color } as React.CSSProperties}
        >
          {homeTeam.abbreviation}
        </div>
        <div className="stats-panel__stat-label"></div>
        <div
          className="stats-panel__team-header"
          style={{ '--team-color': awayTeam.primary_color } as React.CSSProperties}
        >
          {awayTeam.abbreviation}
        </div>
      </div>

      <div className="stats-panel__rows">
        {statRows.map((row) => {
          const homeVal = typeof row.home === 'number' ? row.home : 0;
          const awayVal = typeof row.away === 'number' ? row.away : 0;
          const total = homeVal + awayVal;
          const homePercent = total > 0 ? (homeVal / total) * 100 : 50;

          return (
            <div key={row.label} className="stats-panel__row">
              <div className="stats-panel__value stats-panel__value--home">
                {row.home}
              </div>
              <div className="stats-panel__stat-info">
                <div className="stats-panel__stat-label">{row.label}</div>
                {!row.isRatio && (
                  <div className="stats-panel__bar">
                    <div
                      className="stats-panel__bar-fill stats-panel__bar-fill--home"
                      style={{
                        width: `${homePercent}%`,
                        backgroundColor: homeTeam.primary_color,
                      }}
                    />
                    <div
                      className="stats-panel__bar-fill stats-panel__bar-fill--away"
                      style={{
                        width: `${100 - homePercent}%`,
                        backgroundColor: awayTeam.primary_color,
                      }}
                    />
                  </div>
                )}
              </div>
              <div className="stats-panel__value stats-panel__value--away">
                {row.away}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
