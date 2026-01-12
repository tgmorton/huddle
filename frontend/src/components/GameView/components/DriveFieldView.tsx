/**
 * DriveFieldView - Large field visualization showing drive progress
 *
 * Shows the full field with:
 * - Drive start position
 * - Each play as a marker/segment
 * - Current ball position
 * - First down line
 * - Red zone shading
 * - End zones
 */

import React from 'react';
import type { DrivePlay } from '../types';

interface DriveFieldViewProps {
  los: number; // Current line of scrimmage (0-100)
  driveStartLos: number; // Where drive started
  firstDownLine: number; // First down marker
  currentDrive: DrivePlay[];
  isRedZone?: boolean;
  direction?: 'right' | 'left'; // Which way offense is going
  homeTeamColor?: string; // Home team primary color
  awayTeamColor?: string; // Away team primary color
  homeTeamLogo?: string; // Home team logo filename for midfield
  offenseTeam?: string; // Team abbreviation on offense
  defenseTeam?: string; // Team abbreviation on defense
}

export const DriveFieldView: React.FC<DriveFieldViewProps> = ({
  los,
  driveStartLos,
  firstDownLine,
  currentDrive,
  isRedZone = false,
  direction = 'right',
  homeTeamColor = '#8b2020',
  awayTeamColor = '#002244',
  homeTeamLogo,
  offenseTeam,
  defenseTeam,
}) => {
  // Calculate positions as percentages
  const losPercent = direction === 'right' ? los : 100 - los;
  const driveStartPercent = direction === 'right' ? driveStartLos : 100 - driveStartLos;
  const firstDownPercent = direction === 'right'
    ? Math.min(100, firstDownLine)
    : Math.max(0, 100 - firstDownLine);

  // Build play markers - cumulative positions along the drive
  const playMarkers = buildPlayMarkers(currentDrive, driveStartLos, direction);

  return (
    <div className="drive-field">
      {/* Field surface with yard lines */}
      <div className="drive-field__surface">
        {/* Single yard markers (every yard except 5s and 10s) */}
        {Array.from({ length: 99 }, (_, i) => i + 1)
          .filter(yard => yard % 5 !== 0)
          .map(yard => (
            <div
              key={`tick-${yard}`}
              className="drive-field__yard-line drive-field__yard-line--tick"
              style={{ left: `${yard}%` }}
            />
          ))}

        {/* Minor yard lines every 5 yards (except 10s) */}
        {[5, 15, 25, 35, 45, 55, 65, 75, 85, 95].map(yard => (
          <div
            key={`minor-${yard}`}
            className="drive-field__yard-line drive-field__yard-line--minor"
            style={{ left: `${yard}%` }}
          />
        ))}

        {/* Major yard lines every 10 yards */}
        {[10, 20, 30, 40, 50, 60, 70, 80, 90].map(yard => (
          <div
            key={yard}
            className="drive-field__yard-line drive-field__yard-line--major"
            style={{ left: `${yard}%` }}
          />
        ))}

        {/* Field numbers - top row */}
        {[10, 20, 30, 40, 50, 60, 70, 80, 90].map(yard => (
          <span
            key={`num-top-${yard}`}
            className="drive-field__field-number drive-field__field-number--top"
            style={{ left: `${yard}%` }}
          >
            {yard <= 50 ? yard : 100 - yard}
          </span>
        ))}

        {/* Midfield logo */}
        {homeTeamLogo && (
          <div className="drive-field__midfield-logo">
            <img
              src={`/logos/${homeTeamLogo}`}
              alt="Home team logo"
              className="drive-field__midfield-logo-img"
            />
          </div>
        )}

        {/* Field numbers - bottom row */}
        {[10, 20, 30, 40, 50, 60, 70, 80, 90].map(yard => (
          <span
            key={`num-bot-${yard}`}
            className="drive-field__field-number drive-field__field-number--bottom"
            style={{ left: `${yard}%` }}
          >
            {yard <= 50 ? yard : 100 - yard}
          </span>
        ))}

        {/* Hash marks */}
        <div className="drive-field__hashes drive-field__hashes--top" />
        <div className="drive-field__hashes drive-field__hashes--bottom" />

        {/* End zones with team colors - offense goes right toward defense's end zone */}
        <div
          className="drive-field__endzone drive-field__endzone--left"
          style={{ '--endzone-color': homeTeamColor } as React.CSSProperties}
        >
          <span>{offenseTeam || 'OFF'}</span>
        </div>
        <div
          className="drive-field__endzone drive-field__endzone--right drive-field__endzone--target"
          style={{ '--endzone-color': awayTeamColor } as React.CSSProperties}
        >
          <span>{defenseTeam || 'DEF'}</span>
          <span className="drive-field__endzone-goal">GOAL →</span>
        </div>

        {/* Red zone shading */}
        {isRedZone && (
          <div
            className="drive-field__redzone"
            style={{
              left: direction === 'right' ? '80%' : '0%',
              width: '20%',
            }}
          />
        )}

        {/* Drive progress area (shaded region from start to current) */}
        <div
          className="drive-field__drive-area"
          style={{
            left: `${Math.min(driveStartPercent, losPercent)}%`,
            width: `${Math.abs(losPercent - driveStartPercent)}%`,
          }}
        />

        {/* Drive start marker */}
        <div
          className="drive-field__drive-start"
          style={{ left: `${driveStartPercent}%` }}
        >
          <span className="drive-field__drive-start-label">START</span>
        </div>

        {/* Play markers along the drive */}
        {playMarkers.map((marker, index) => (
          <div
            key={index}
            className={`drive-field__play-marker ${marker.isFirstDown ? 'drive-field__play-marker--first-down' : ''} ${marker.yards < 0 ? 'drive-field__play-marker--loss' : ''}`}
            style={{ left: `${marker.position}%` }}
            title={`${marker.playName}: ${marker.yards > 0 ? '+' : ''}${marker.yards} yds`}
          />
        ))}

        {/* First down line */}
        <div
          className="drive-field__first-down-line"
          style={{ left: `${firstDownPercent}%` }}
        />

        {/* Current ball position */}
        <div
          className="drive-field__ball"
          style={{ left: `${losPercent}%` }}
        >
          <div className="drive-field__ball-icon" />
          <span className="drive-field__ball-label">BALL</span>
        </div>
      </div>

      {/* Field info bar below */}
      <div className="drive-field__info">
        <span className="drive-field__info-start">
          Started: OWN {driveStartLos}
        </span>
        <span className="drive-field__info-progress">
          {currentDrive.length} plays | {currentDrive.reduce((sum, p) => sum + p.yardsGained, 0)} yards
        </span>
        <span className="drive-field__info-current">
          Current: {los <= 50 ? `OWN ${los}` : `OPP ${100 - los}`}
        </span>
      </div>
    </div>
  );
};

interface PlayMarker {
  position: number; // Percentage along field
  yards: number;
  playName: string;
  isFirstDown: boolean;
}

function buildPlayMarkers(
  plays: DrivePlay[],
  startLos: number,
  direction: 'right' | 'left'
): PlayMarker[] {
  const markers: PlayMarker[] = [];
  let currentPos = startLos;

  for (const play of plays) {
    currentPos += play.yardsGained;
    const position = direction === 'right' ? currentPos : 100 - currentPos;

    markers.push({
      position: Math.max(0, Math.min(100, position)),
      yards: play.yardsGained,
      playName: play.playName || play.playType,
      isFirstDown: play.isFirstDown,
    });
  }

  return markers;
}

export default DriveFieldView;
