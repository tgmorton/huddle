/**
 * Scoreboard - AWS Next Gen Stats style scoreboard bar
 *
 * Displays:
 * - Team abbreviations and scores
 * - Quarter and time
 * - Down and distance
 * - Possession indicator
 */

import React from 'react';
import type { TeamInfo } from './types';

interface ScoreboardProps {
  homeTeam: TeamInfo;
  awayTeam: TeamInfo;
  homeScore: number;
  awayScore: number;
  quarter: number;
  timeRemaining: string;
  down: number;
  distance: number;
  possessionHome: boolean;
}

export const Scoreboard: React.FC<ScoreboardProps> = ({
  homeTeam,
  awayTeam,
  homeScore,
  awayScore,
  quarter,
  timeRemaining,
  down,
  distance,
  possessionHome,
}) => {
  const formatDown = (d: number, dist: number): string => {
    const suffix = d === 1 ? 'st' : d === 2 ? 'nd' : d === 3 ? 'rd' : 'th';
    return `${d}${suffix} & ${dist}`;
  };

  const formatQuarter = (q: number): string => {
    if (q <= 4) return `${q}Q`;
    return 'OT';
  };

  return (
    <div className="broadcast-scoreboard">
      {/* Away team (left) */}
      <div className={`broadcast-scoreboard__team ${!possessionHome ? 'has-ball' : ''}`}>
        {!possessionHome && <span className="broadcast-scoreboard__ball">●</span>}
        <span
          className="broadcast-scoreboard__abbr"
          style={{ color: awayTeam.primaryColor }}
        >
          {awayTeam.abbr}
        </span>
        <span className="broadcast-scoreboard__score">{awayScore}</span>
      </div>

      {/* Separator */}
      <span className="broadcast-scoreboard__sep">-</span>

      {/* Home team (right) */}
      <div className={`broadcast-scoreboard__team ${possessionHome ? 'has-ball' : ''}`}>
        <span className="broadcast-scoreboard__score">{homeScore}</span>
        <span
          className="broadcast-scoreboard__abbr"
          style={{ color: homeTeam.primaryColor }}
        >
          {homeTeam.abbr}
        </span>
        {possessionHome && <span className="broadcast-scoreboard__ball">●</span>}
      </div>

      {/* Game info */}
      <div className="broadcast-scoreboard__info">
        <span className="broadcast-scoreboard__quarter">{formatQuarter(quarter)}</span>
        <span className="broadcast-scoreboard__time">{timeRemaining}</span>
        <span className="broadcast-scoreboard__down">{formatDown(down, distance)}</span>
      </div>
    </div>
  );
};

export default Scoreboard;
