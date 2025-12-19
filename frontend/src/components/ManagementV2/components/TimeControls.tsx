// TimeControls.tsx - Play/pause and speed controls

import React from 'react';

interface TimeControlsProps {
  isPaused: boolean;
  speed: 1 | 2 | 3;
  onTogglePause: () => void;
  onSetSpeed: (speed: 1 | 2 | 3) => void;
}

const speedLabels = ['Slow', 'Normal', 'Fast'];

export const TimeControls: React.FC<TimeControlsProps> = ({
  isPaused,
  speed,
  onTogglePause,
  onSetSpeed,
}) => {
  return (
    <div className="time-ctrl">
      <button
        className={`time-ctrl__play ${isPaused ? '' : 'time-ctrl__play--active'}`}
        onClick={onTogglePause}
      >
        {isPaused ? '▶ Play' : '❚❚ Pause'}
      </button>

      <div className="time-ctrl__speed">
        {[1, 2, 3].map(s => (
          <button
            key={s}
            className={`time-ctrl__speed-btn ${speed === s ? 'time-ctrl__speed-btn--active' : ''}`}
            onClick={() => onSetSpeed(s as 1 | 2 | 3)}
            disabled={isPaused}
          >
            {speedLabels[s - 1]}
          </button>
        ))}
      </div>
    </div>
  );
};

export default TimeControls;
