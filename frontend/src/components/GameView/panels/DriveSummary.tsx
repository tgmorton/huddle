/**
 * DriveSummary - Current drive panel showing play-by-play progress
 *
 * Displays:
 * - Total plays and yards for current drive
 * - Individual play results with down, type, yards
 * - First down indicators
 * - Time of possession
 */

import React from 'react';
import { ArrowRight, CircleDot } from 'lucide-react';
import type { DrivePlay } from '../types';

interface DriveSummaryProps {
  plays: DrivePlay[];
  startingPosition?: number;
  timeOfPossession?: string;
  className?: string;
}

export const DriveSummary: React.FC<DriveSummaryProps> = ({
  plays,
  startingPosition,
  timeOfPossession,
  className = '',
}) => {
  if (plays.length === 0) {
    return (
      <div className={`drive-summary drive-summary--empty ${className}`}>
        <p className="drive-summary__empty-text">No plays yet this drive</p>
      </div>
    );
  }

  const totalYards = plays.reduce((sum, p) => sum + p.yardsGained, 0);
  const firstDowns = plays.filter(p => p.isFirstDown).length;
  const runPlays = plays.filter(p => p.playType === 'run').length;
  const passPlays = plays.filter(p => p.playType === 'pass').length;

  return (
    <div className={`drive-summary ${className}`}>
      {/* Drive stats header */}
      <div className="drive-summary__header">
        <div className="drive-summary__stat">
          <span className="drive-summary__stat-value">{plays.length}</span>
          <span className="drive-summary__stat-label">Plays</span>
        </div>
        <div className="drive-summary__stat">
          <span className={`drive-summary__stat-value ${totalYards >= 0 ? 'positive' : 'negative'}`}>
            {totalYards > 0 ? '+' : ''}{totalYards}
          </span>
          <span className="drive-summary__stat-label">Yards</span>
        </div>
        <div className="drive-summary__stat">
          <span className="drive-summary__stat-value">{firstDowns}</span>
          <span className="drive-summary__stat-label">1st Downs</span>
        </div>
        {timeOfPossession && (
          <div className="drive-summary__stat">
            <span className="drive-summary__stat-value">{timeOfPossession}</span>
            <span className="drive-summary__stat-label">TOP</span>
          </div>
        )}
      </div>

      {/* Play balance indicator */}
      <div className="drive-summary__balance">
        <div className="drive-summary__balance-bar">
          <div
            className="drive-summary__balance-run"
            style={{ width: `${(runPlays / plays.length) * 100}%` }}
          />
          <div
            className="drive-summary__balance-pass"
            style={{ width: `${(passPlays / plays.length) * 100}%` }}
          />
        </div>
        <div className="drive-summary__balance-labels">
          <span>Run: {runPlays}</span>
          <span>Pass: {passPlays}</span>
        </div>
      </div>

      {/* Play list */}
      <div className="drive-summary__plays">
        {plays.map((play, i) => (
          <div
            key={i}
            className={`drive-summary__play ${play.isFirstDown ? 'drive-summary__play--first-down' : ''}`}
          >
            <span className="drive-summary__play-down">
              {getDownAbbrev(play.down)}&{play.distance}
            </span>
            <span className={`drive-summary__play-type drive-summary__play-type--${play.playType}`}>
              {play.playType === 'run' ? <CircleDot size={10} /> : <ArrowRight size={10} />}
            </span>
            <span className="drive-summary__play-name">{play.playName}</span>
            <span className={`drive-summary__play-yards ${play.yardsGained > 0 ? 'positive' : play.yardsGained < 0 ? 'negative' : ''}`}>
              {play.yardsGained > 0 ? '+' : ''}{play.yardsGained}
            </span>
            {play.isFirstDown && (
              <span className="drive-summary__play-first">1ST</span>
            )}
          </div>
        ))}
      </div>

      {/* Starting position if available */}
      {startingPosition !== undefined && (
        <div className="drive-summary__footer">
          <span className="drive-summary__start">
            Started at: {formatYardLine(startingPosition)}
          </span>
        </div>
      )}
    </div>
  );
};

function getDownAbbrev(down: number): string {
  switch (down) {
    case 1: return '1st';
    case 2: return '2nd';
    case 3: return '3rd';
    case 4: return '4th';
    default: return `${down}th`;
  }
}

function formatYardLine(los: number): string {
  if (los <= 50) {
    return `OWN ${los}`;
  }
  return `OPP ${100 - los}`;
}

export default DriveSummary;
