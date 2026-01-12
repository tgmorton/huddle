/**
 * GameHeader - Top header with league ticker placeholder
 *
 * Shows:
 * - Current game context (Week, Teams, Stadium)
 * - League ticker placeholder with mock scores
 */

import React from 'react';
import { MOCK_LEAGUE_SCORES } from '../constants';

interface GameHeaderProps {
  homeTeam: string;
  awayTeam: string;
  week: number;
  stadium?: string;
}

export const GameHeader: React.FC<GameHeaderProps> = ({
  homeTeam,
  awayTeam,
  week,
  stadium = 'Stadium',
}) => {
  return (
    <header className="game-header">
      {/* Left: Current game context */}
      <div className="game-header__context">
        <span className="game-header__week">WEEK {week}</span>
        <span className="game-header__sep">|</span>
        <span className="game-header__matchup">{awayTeam} @ {homeTeam}</span>
        <span className="game-header__sep">|</span>
        <span className="game-header__stadium">{stadium}</span>
      </div>

      {/* Right: League ticker placeholder */}
      <div className="game-header__ticker">
        <span className="game-header__ticker-label">AROUND THE LEAGUE</span>
        <div className="game-header__ticker-scroll">
          {MOCK_LEAGUE_SCORES.map((score, i) => (
            <span key={i} className="game-header__ticker-item">
              {score.awayTeam} {score.awayScore} - {score.homeTeam} {score.homeScore}
              {score.quarter === 'FINAL' ? (
                <span className="game-header__ticker-status game-header__ticker-status--final">
                  FINAL
                </span>
              ) : (
                <span className="game-header__ticker-status">
                  Q{score.quarter} {score.timeRemaining}
                </span>
              )}
              {i < MOCK_LEAGUE_SCORES.length - 1 && (
                <span className="game-header__ticker-sep">|</span>
              )}
            </span>
          ))}
        </div>
      </div>
    </header>
  );
};

export default GameHeader;
