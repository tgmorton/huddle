/**
 * GameHUD - Bottom scoreboard bar
 *
 * Always-visible game situation display showing:
 * - Team scores
 * - Quarter and time
 * - Down and distance
 * - Field position
 * - Timeouts remaining
 */

import React from 'react';
import { Circle } from 'lucide-react';
import type { GameSituation } from '../types';

interface GameHUDProps {
  situation: GameSituation | null;
}

export const GameHUD: React.FC<GameHUDProps> = ({ situation }) => {
  if (!situation) {
    return (
      <div className="game-hud">
        <div className="game-hud__loading">Loading game...</div>
      </div>
    );
  }

  const {
    quarter,
    timeRemaining,
    down,
    distance,
    yardLineDisplay,
    homeScore,
    awayScore,
    possessionHome,
    isRedZone,
    isGoalToGo,
    homeTimeouts,
    awayTimeouts,
  } = situation;

  // Format down and distance
  const downDistanceText = isGoalToGo
    ? `${down}${getOrdinal(down)} & Goal`
    : `${down}${getOrdinal(down)} & ${distance}`;

  // Quarter display
  const quarterText = quarter <= 4 ? `Q${quarter}` : 'OT';

  return (
    <div className={`game-hud ${isRedZone ? 'game-hud--redzone' : ''}`}>
      {/* Away team */}
      <div className="game-hud__team game-hud__team--away">
        <span className="game-hud__team-name">AWAY</span>
        <span className="game-hud__team-score">{awayScore}</span>
        <div className="game-hud__timeouts">
          {Array.from({ length: 3 }).map((_, i) => (
            <span
              key={i}
              className={`game-hud__timeout ${i < awayTimeouts ? 'game-hud__timeout--active' : ''}`}
            />
          ))}
        </div>
        {!possessionHome && <Circle className="game-hud__possession" size={8} fill="currentColor" />}
      </div>

      {/* Center: Time and situation */}
      <div className="game-hud__center">
        <div className="game-hud__clock">
          <span className="game-hud__quarter">{quarterText}</span>
          <span className="game-hud__time">{timeRemaining}</span>
        </div>
        <div className="game-hud__situation">
          <span className="game-hud__down">{downDistanceText}</span>
          <span className="game-hud__field-pos">{yardLineDisplay}</span>
        </div>
        {isRedZone && <span className="game-hud__redzone-indicator">RED ZONE</span>}
      </div>

      {/* Home team */}
      <div className="game-hud__team game-hud__team--home">
        {possessionHome && <Circle className="game-hud__possession" size={8} fill="currentColor" />}
        <span className="game-hud__team-name">HOME</span>
        <span className="game-hud__team-score">{homeScore}</span>
        <div className="game-hud__timeouts">
          {Array.from({ length: 3 }).map((_, i) => (
            <span
              key={i}
              className={`game-hud__timeout ${i < homeTimeouts ? 'game-hud__timeout--active' : ''}`}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

// Helper to get ordinal suffix
function getOrdinal(n: number): string {
  if (n === 1) return 'st';
  if (n === 2) return 'nd';
  if (n === 3) return 'rd';
  return 'th';
}

export default GameHUD;
