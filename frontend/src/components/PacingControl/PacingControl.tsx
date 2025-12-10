/**
 * PacingControl component - pause/resume/speed controls
 */

import { useGameStore } from '../../stores/gameStore';
import './PacingControl.css';

interface PacingControlProps {
  onPause: () => void;
  onResume: () => void;
  onStep: () => void;
  onPacingChange: (pacing: 'instant' | 'fast' | 'normal' | 'slow') => void;
}

const PACING_OPTIONS = [
  { value: 'instant', label: 'Instant', icon: '⚡' },
  { value: 'fast', label: 'Fast', icon: '🏃' },
  { value: 'normal', label: 'Normal', icon: '🚶' },
  { value: 'slow', label: 'Slow', icon: '🐢' },
] as const;

export function PacingControl({ onPause, onResume, onStep, onPacingChange }: PacingControlProps) {
  const { isPaused, pacing, gameState } = useGameStore();

  const isGameOver = gameState?.is_game_over ?? false;

  return (
    <div className="pacing-control">
      <div className="pacing-control__buttons">
        {isPaused ? (
          <>
            <button
              className="pacing-control__btn pacing-control__btn--play"
              onClick={onResume}
              disabled={isGameOver}
              title="Resume (Space)"
            >
              ▶️ Play
            </button>
            <button
              className="pacing-control__btn pacing-control__btn--step"
              onClick={onStep}
              disabled={isGameOver}
              title="Step (N)"
            >
              ⏭️ Step
            </button>
          </>
        ) : (
          <button
            className="pacing-control__btn pacing-control__btn--pause"
            onClick={onPause}
            disabled={isGameOver}
            title="Pause (Space)"
          >
            ⏸️ Pause
          </button>
        )}
      </div>

      <div className="pacing-control__speed">
        <span className="pacing-control__speed-label">Speed:</span>
        <div className="pacing-control__speed-options">
          {PACING_OPTIONS.map((option) => (
            <button
              key={option.value}
              className={`pacing-control__speed-btn ${
                pacing === option.value ? 'pacing-control__speed-btn--active' : ''
              }`}
              onClick={() => onPacingChange(option.value)}
              title={option.label}
            >
              {option.icon}
            </button>
          ))}
        </div>
      </div>

      {isGameOver && (
        <div className="pacing-control__game-over">
          Game Over
        </div>
      )}
    </div>
  );
}
