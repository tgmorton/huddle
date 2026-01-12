/**
 * PlaybackControls - Controls for play animation playback
 *
 * Features:
 * - Play/Pause button
 * - Speed selector (0.5x, 1x, 2x, 4x)
 * - Timeline scrub bar
 * - Frame stepping (forward/back)
 * - Live indicator
 */

import React from 'react';
import {
  Play,
  Pause,
  SkipForward,
  SkipBack,
  FastForward,
  Rewind,
} from 'lucide-react';

interface PlaybackControlsProps {
  currentTick: number;
  totalTicks: number;
  isPlaying: boolean;
  speed: number;
  onPlay: () => void;
  onPause: () => void;
  onSeek: (tick: number) => void;
  onSpeedChange: (speed: number) => void;
  onStepForward?: () => void;
  onStepBack?: () => void;
}

const SPEEDS = [0.5, 1, 2, 4];

export function PlaybackControls({
  currentTick,
  totalTicks,
  isPlaying,
  speed,
  onPlay,
  onPause,
  onSeek,
  onSpeedChange,
  onStepForward,
  onStepBack,
}: PlaybackControlsProps) {
  const progress = totalTicks > 0 ? (currentTick / totalTicks) * 100 : 0;
  const currentTime = (currentTick * 0.05).toFixed(2);  // 20 ticks/sec = 50ms per tick
  const totalTime = (totalTicks * 0.05).toFixed(2);

  const handleSeekChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const tick = parseInt(e.target.value, 10);
    onSeek(tick);
  };

  const handleStepBack = () => {
    if (onStepBack) {
      onStepBack();
    } else {
      onSeek(Math.max(0, currentTick - 1));
    }
  };

  const handleStepForward = () => {
    if (onStepForward) {
      onStepForward();
    } else {
      onSeek(Math.min(totalTicks - 1, currentTick + 1));
    }
  };

  return (
    <div className="playback-controls">
      {/* Timeline */}
      <div className="playback-controls__timeline">
        <span className="playback-controls__time">{currentTime}s</span>
        <input
          type="range"
          min={0}
          max={totalTicks - 1 || 0}
          value={currentTick}
          onChange={handleSeekChange}
          className="playback-controls__slider"
          disabled={totalTicks === 0}
        />
        <span className="playback-controls__time">{totalTime}s</span>
      </div>

      {/* Controls row */}
      <div className="playback-controls__row">
        {/* Step back */}
        <button
          className="playback-controls__btn"
          onClick={handleStepBack}
          disabled={currentTick === 0 || totalTicks === 0}
          title="Step back"
        >
          <SkipBack size={16} />
        </button>

        {/* Play/Pause */}
        <button
          className="playback-controls__btn playback-controls__btn--primary"
          onClick={isPlaying ? onPause : onPlay}
          disabled={totalTicks === 0}
          title={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? <Pause size={20} /> : <Play size={20} />}
        </button>

        {/* Step forward */}
        <button
          className="playback-controls__btn"
          onClick={handleStepForward}
          disabled={currentTick >= totalTicks - 1 || totalTicks === 0}
          title="Step forward"
        >
          <SkipForward size={16} />
        </button>

        {/* Speed selector */}
        <div className="playback-controls__speed">
          {SPEEDS.map(s => (
            <button
              key={s}
              className={`playback-controls__speed-btn ${speed === s ? 'active' : ''}`}
              onClick={() => onSpeedChange(s)}
              title={`${s}x speed`}
            >
              {s}x
            </button>
          ))}
        </div>

        {/* Tick counter */}
        <span className="playback-controls__ticks">
          {currentTick + 1} / {totalTicks}
        </span>
      </div>
    </div>
  );
}

export default PlaybackControls;
