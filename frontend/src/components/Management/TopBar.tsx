/**
 * TopBar - Displays time, date, season phase, and time controls
 */

import React from 'react';
import { useManagementStore, selectIsPaused, selectCurrentSpeed } from '../../stores/managementStore';
import type { TimeSpeed } from '../../types/management';
import { SPEED_LABELS } from '../../types/management';
import './TopBar.css';

interface TopBarProps {
  onPause: () => void;
  onPlay: (speed?: TimeSpeed) => void;
  onSetSpeed: (speed: TimeSpeed) => void;
}

export const TopBar: React.FC<TopBarProps> = ({ onPause, onPlay, onSetSpeed }) => {
  const calendar = useManagementStore((state) => state.calendar);
  const isPaused = useManagementStore(selectIsPaused);
  const currentSpeed = useManagementStore(selectCurrentSpeed);

  if (!calendar) {
    return (
      <div className="topbar topbar--loading">
        <div className="topbar__loading">Loading...</div>
      </div>
    );
  }

  const handleSpeedChange = (speed: TimeSpeed) => {
    if (speed === 'PAUSED') {
      onPause();
    } else {
      onSetSpeed(speed);
    }
  };

  const handlePlayPause = () => {
    if (isPaused) {
      onPlay('NORMAL');
    } else {
      onPause();
    }
  };

  return (
    <div className="topbar">
      {/* Left section: Date and Time */}
      <div className="topbar__section topbar__datetime">
        <div className="topbar__day">{calendar.day_name}</div>
        <div className="topbar__date">{calendar.date_display}</div>
        <div className="topbar__time">{calendar.time_display}</div>
      </div>

      {/* Center section: Week and Phase */}
      <div className="topbar__section topbar__season">
        <div className="topbar__week">{calendar.week_display}</div>
        <div className="topbar__phase">{formatPhase(calendar.phase)}</div>
        <div className="topbar__year">{calendar.season_year} Season</div>
      </div>

      {/* Right section: Time Controls */}
      <div className="topbar__section topbar__controls">
        <button
          className={`topbar__btn topbar__btn--playpause ${isPaused ? 'paused' : 'playing'}`}
          onClick={handlePlayPause}
          title={isPaused ? 'Play' : 'Pause'}
        >
          {isPaused ? '▶' : '⏸'}
        </button>

        <div className="topbar__speed-controls">
          {(['SLOW', 'NORMAL', 'FAST', 'VERY_FAST'] as TimeSpeed[]).map((speed) => (
            <button
              key={speed}
              className={`topbar__btn topbar__btn--speed ${
                currentSpeed === speed ? 'active' : ''
              }`}
              onClick={() => handleSpeedChange(speed)}
              title={SPEED_LABELS[speed]}
            >
              {getSpeedIcon(speed)}
            </button>
          ))}
        </div>

        <div className="topbar__status">
          {isPaused ? (
            <span className="topbar__status-paused">PAUSED</span>
          ) : (
            <span className="topbar__status-playing">{SPEED_LABELS[currentSpeed]}</span>
          )}
        </div>
      </div>
    </div>
  );
};

function formatPhase(phase: string): string {
  return phase
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function getSpeedIcon(speed: TimeSpeed): string {
  switch (speed) {
    case 'SLOW':
      return '>';
    case 'NORMAL':
      return '>>';
    case 'FAST':
      return '>>>';
    case 'VERY_FAST':
      return '>>>>';
    default:
      return '>';
  }
}
