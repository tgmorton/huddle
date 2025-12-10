/**
 * PlayLog component - displays play-by-play history
 */

import { useEffect, useRef } from 'react';
import { useGameStore } from '../../stores/gameStore';
import './PlayLog.css';

export function PlayLog() {
  const { playLog } = useGameStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new plays are added
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [playLog.length]);

  if (playLog.length === 0) {
    return (
      <div className="play-log play-log--empty">
        <p>No plays yet. Start the game to see play-by-play updates.</p>
      </div>
    );
  }

  return (
    <div className="play-log" ref={scrollRef}>
      <div className="play-log__header">
        <span>Play-by-Play</span>
        <span className="play-log__count">{playLog.length} plays</span>
      </div>
      <div className="play-log__entries">
        {playLog.map((entry) => (
          <div
            key={entry.id}
            className={`play-log__entry ${
              entry.isScoring ? 'play-log__entry--scoring' : ''
            } ${entry.isTurnover ? 'play-log__entry--turnover' : ''}`}
          >
            <div className="play-log__entry-meta">
              <span className="play-log__entry-quarter">Q{entry.quarter}</span>
              <span className="play-log__entry-time">{entry.timeRemaining}</span>
            </div>
            <div className="play-log__entry-description">{entry.description}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
