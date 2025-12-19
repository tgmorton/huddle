/**
 * GameDayPanel - Game day UI
 *
 * When it's game day, this panel shows:
 * - Opponent info and matchup preview
 * - Option to Play (go to game sim) or Sim (auto-resolve)
 */

import React from 'react';
import './GameDayPanel.css';

interface GameDayPanelProps {
  eventId: string;
  week: number;
  opponentName: string;
  isHome: boolean;
  onPlayGame: (eventId: string) => void;
  onSimGame: (eventId: string) => void;
  onCancel: () => void;
}

export const GameDayPanel: React.FC<GameDayPanelProps> = ({
  eventId,
  week,
  opponentName,
  isHome,
  onPlayGame,
  onSimGame,
  onCancel,
}) => {
  const location = isHome ? 'HOME' : 'AWAY';
  const locationText = isHome ? 'vs' : '@';

  return (
    <div className="game-day-panel">
      <div className="game-day-panel__header">
        <span className="game-day-panel__week">Week {week}</span>
        <span className={`game-day-panel__location game-day-panel__location--${location.toLowerCase()}`}>
          {location}
        </span>
      </div>

      <div className="game-day-panel__matchup">
        <div className="game-day-panel__team game-day-panel__team--player">
          <div className="game-day-panel__team-name">PHI</div>
          <div className="game-day-panel__team-label">Eagles</div>
        </div>

        <div className="game-day-panel__vs">{locationText}</div>

        <div className="game-day-panel__team game-day-panel__team--opponent">
          <div className="game-day-panel__team-name">{opponentName.substring(0, 3).toUpperCase()}</div>
          <div className="game-day-panel__team-label">{opponentName}</div>
        </div>
      </div>

      <div className="game-day-panel__preview">
        <h3>Game Preview</h3>
        <div className="game-day-panel__stats">
          <div className="game-day-panel__stat-row">
            <span className="game-day-panel__stat-label">Your Record</span>
            <span className="game-day-panel__stat-value">0-0</span>
          </div>
          <div className="game-day-panel__stat-row">
            <span className="game-day-panel__stat-label">Opponent Record</span>
            <span className="game-day-panel__stat-value">0-0</span>
          </div>
        </div>
      </div>

      <div className="game-day-panel__actions">
        <button
          className="game-day-panel__btn game-day-panel__btn--sim"
          onClick={() => onSimGame(eventId)}
        >
          Sim Game
          <span className="game-day-panel__btn-hint">Auto-resolve</span>
        </button>
        <button
          className="game-day-panel__btn game-day-panel__btn--play"
          onClick={() => onPlayGame(eventId)}
        >
          Play Game
          <span className="game-day-panel__btn-hint">Watch simulation</span>
        </button>
      </div>

      <button className="game-day-panel__back" onClick={onCancel}>
        Back
      </button>
    </div>
  );
};

export default GameDayPanel;
