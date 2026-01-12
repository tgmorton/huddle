/**
 * SpectatorControls - Controls for auto-play spectator mode
 *
 * Provides:
 * - Play/Pause toggle
 * - Speed control (slow/normal/fast)
 * - Step mode for manual advancement
 */

import React from 'react';
import { Play, Pause, FastForward, SkipForward, Gauge, Rewind } from 'lucide-react';
import type { Pacing } from '../hooks/useGameWebSocket';

interface SpectatorControlsProps {
  isPaused: boolean;
  pacing: Pacing;
  gameOver: boolean;
  onTogglePause: () => void;
  onSetPacing: (pacing: Pacing) => void;
  onStep: () => void;
  onEndGame: () => void;
}

export const SpectatorControls: React.FC<SpectatorControlsProps> = ({
  isPaused,
  pacing,
  gameOver,
  onTogglePause,
  onSetPacing,
  onStep,
  onEndGame,
}) => {
  if (gameOver) {
    return (
      <div className="spectator-controls spectator-controls--game-over">
        <div className="spectator-controls__game-over">
          <span className="spectator-controls__game-over-text">FINAL</span>
          <button
            className="spectator-controls__btn spectator-controls__btn--primary"
            onClick={onEndGame}
          >
            New Game
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="spectator-controls">
      {/* Play/Pause */}
      <div className="spectator-controls__playback">
        {/* Show play/pause toggle for auto modes, just step for step mode */}
        {pacing !== 'step' && (
          <button
            className={`spectator-controls__btn spectator-controls__btn--play ${isPaused ? '' : 'active'}`}
            onClick={onTogglePause}
            title={isPaused ? 'Resume' : 'Pause'}
          >
            {isPaused ? <Play size={18} /> : <Pause size={18} />}
          </button>
        )}

        {/* Step button - main control in step mode */}
        {pacing === 'step' && (
          <button
            className="spectator-controls__btn spectator-controls__btn--primary spectator-controls__btn--step"
            onClick={onStep}
            title="Next Play"
          >
            <SkipForward size={18} />
            <span>Next Play</span>
          </button>
        )}

        {/* Also show step when paused in auto mode */}
        {pacing !== 'step' && isPaused && (
          <button
            className="spectator-controls__btn"
            onClick={onStep}
            title="Step (advance one play)"
          >
            <SkipForward size={18} />
          </button>
        )}
      </div>

      {/* Speed Controls */}
      <div className="spectator-controls__speed">
        <span className="spectator-controls__speed-label">
          <Gauge size={14} />
          SPEED
        </span>
        <div className="spectator-controls__speed-btns">
          <button
            className={`spectator-controls__speed-btn ${pacing === 'slow' ? 'active' : ''}`}
            onClick={() => onSetPacing('slow')}
            title="Slow (2s per play)"
          >
            <Rewind size={14} />
            0.5x
          </button>
          <button
            className={`spectator-controls__speed-btn ${pacing === 'normal' ? 'active' : ''}`}
            onClick={() => onSetPacing('normal')}
            title="Normal (1s per play)"
          >
            1x
          </button>
          <button
            className={`spectator-controls__speed-btn ${pacing === 'fast' ? 'active' : ''}`}
            onClick={() => onSetPacing('fast')}
            title="Fast (0.3s per play)"
          >
            <FastForward size={14} />
            2x
          </button>
          <button
            className={`spectator-controls__speed-btn ${pacing === 'step' ? 'active' : ''}`}
            onClick={() => onSetPacing('step')}
            title="Step mode (manual advancement)"
          >
            <SkipForward size={14} />
          </button>
        </div>
      </div>

      {/* End Game */}
      <div className="spectator-controls__actions">
        <button
          className="spectator-controls__btn spectator-controls__btn--end"
          onClick={onEndGame}
          title="End Game"
        >
          End
        </button>
      </div>
    </div>
  );
};

export default SpectatorControls;
