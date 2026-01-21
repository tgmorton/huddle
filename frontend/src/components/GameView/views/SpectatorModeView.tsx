/**
 * SpectatorModeView - Spectator controls for watching AI vs AI games
 *
 * Extracted from GameView to separate spectator-specific UI:
 * - SpectatorControls for play/pause/pacing
 * - Game over handling
 */

import React from 'react';
import { SpectatorControls } from '../components/SpectatorControls';
import type { Pacing } from '../hooks/useGameWebSocket';

interface SpectatorModeViewProps {
  // Playback state
  isPaused: boolean;
  pacing: Pacing;
  gameOver: boolean;

  // Handlers
  onTogglePause: () => void;
  onSetPacing: (pacing: Pacing) => void;
  onStep: () => void;
  onEndGame: () => void;
}

export const SpectatorModeView: React.FC<SpectatorModeViewProps> = ({
  isPaused,
  pacing,
  gameOver,
  onTogglePause,
  onSetPacing,
  onStep,
  onEndGame,
}) => {
  return (
    <div className="game-view__play-caller">
      <SpectatorControls
        isPaused={isPaused}
        pacing={pacing}
        gameOver={gameOver}
        onTogglePause={onTogglePause}
        onSetPacing={onSetPacing}
        onStep={onStep}
        onEndGame={onEndGame}
      />
    </div>
  );
};

export default SpectatorModeView;
