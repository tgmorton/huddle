/**
 * SchedulePanel - Season schedule display
 *
 * Design Philosophy:
 * - Context is king - rival games, division games should feel different
 * - Show what's at stake, not just dates
 * - Let the schedule tell a story
 */

import React, { useState, useEffect } from 'react';
import './SchedulePanel.css';

interface ScheduleGame {
  game_id: string;
  week: number;
  home_team: string;
  away_team: string;
  home_score: number | null;
  away_score: number | null;
  is_played: boolean;
  day_of_week?: string;
  time?: string;
  is_overtime?: boolean;
}

interface SchedulePanelProps {
  teamAbbr: string;
  currentWeek?: number;
}

export const SchedulePanel: React.FC<SchedulePanelProps> = ({
  teamAbbr,
  currentWeek = 1,
}) => {
  const [games, setGames] = useState<ScheduleGame[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSchedule = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/v1/admin/schedule?team=${teamAbbr}`);
        if (!response.ok) {
          throw new Error('Failed to load schedule');
        }
        const data = await response.json();
        setGames(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    if (teamAbbr) {
      fetchSchedule();
    }
  }, [teamAbbr]);

  if (loading) {
    return (
      <div className="schedule-panel schedule-panel--loading">
        <div className="schedule-panel__loader">Loading schedule...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="schedule-panel schedule-panel--error">
        <div className="schedule-panel__error">{error}</div>
      </div>
    );
  }

  // Calculate record
  const record = games.reduce(
    (acc, game) => {
      if (!game.is_played) return acc;
      const isHome = game.home_team === teamAbbr;
      const ourScore = isHome ? game.home_score : game.away_score;
      const theirScore = isHome ? game.away_score : game.home_score;
      if (ourScore === null || theirScore === null) return acc;
      if (ourScore > theirScore) acc.wins++;
      else if (ourScore < theirScore) acc.losses++;
      else acc.ties++;
      return acc;
    },
    { wins: 0, losses: 0, ties: 0 }
  );

  return (
    <div className="schedule-panel">
      {/* Header */}
      <div className="schedule-panel__header">
        <div className="schedule-panel__title">
          <span className="schedule-panel__team">{teamAbbr}</span>
          <span className="schedule-panel__label">Schedule</span>
        </div>
        <div className="schedule-panel__record">
          {record.wins}-{record.losses}
          {record.ties > 0 ? `-${record.ties}` : ''}
        </div>
      </div>

      {/* Games List */}
      <div className="schedule-panel__games">
        {games.map((game) => (
          <GameRow
            key={game.game_id}
            game={game}
            teamAbbr={teamAbbr}
            isCurrent={game.week === currentWeek}
          />
        ))}
      </div>
    </div>
  );
};

interface GameRowProps {
  game: ScheduleGame;
  teamAbbr: string;
  isCurrent: boolean;
}

const GameRow: React.FC<GameRowProps> = ({ game, teamAbbr, isCurrent }) => {
  const isHome = game.home_team === teamAbbr;
  const opponent = isHome ? game.away_team : game.home_team;
  const ourScore = isHome ? game.home_score : game.away_score;
  const theirScore = isHome ? game.away_score : game.home_score;

  let result: 'W' | 'L' | 'T' | null = null;
  if (game.is_played && ourScore !== null && theirScore !== null) {
    if (ourScore > theirScore) result = 'W';
    else if (ourScore < theirScore) result = 'L';
    else result = 'T';
  }

  return (
    <div className={`game-row ${isCurrent ? 'game-row--current' : ''} ${game.is_played ? 'game-row--played' : ''}`}>
      <div className="game-row__week">WK {game.week}</div>

      <div className="game-row__matchup">
        <span className="game-row__venue">{isHome ? 'vs' : '@'}</span>
        <span className="game-row__opponent">{opponent}</span>
      </div>

      {game.is_played ? (
        <div className="game-row__result">
          <span className={`game-row__outcome game-row__outcome--${result?.toLowerCase()}`}>
            {result}
          </span>
          <span className="game-row__score">
            {ourScore}-{theirScore}
            {game.is_overtime && <span className="game-row__ot">OT</span>}
          </span>
        </div>
      ) : (
        <div className="game-row__upcoming">
          <span className="game-row__day">{game.day_of_week || 'SUN'}</span>
          <span className="game-row__time">{game.time || '1:00 PM'}</span>
        </div>
      )}
    </div>
  );
};

export default SchedulePanel;
