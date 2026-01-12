/**
 * FieldPositionBar - Visual field position indicator
 *
 * A horizontal bar showing:
 * - Current line of scrimmage
 * - First down line
 * - Red zone shading
 * - End zones
 */

import React from 'react';

interface FieldPositionBarProps {
  los: number; // 0-100, where 0 = own goal line, 100 = opponent goal line
  firstDownLine: number; // Target for first down
  isRedZone?: boolean;
  direction?: 'left' | 'right'; // Which way offense is going
  driveStartLos?: number; // Where the drive started (for showing progress)
}

export const FieldPositionBar: React.FC<FieldPositionBarProps> = ({
  los,
  firstDownLine,
  isRedZone = false,
  direction = 'right',
  driveStartLos,
}) => {
  // Clamp values to valid range
  const clampedLos = Math.max(0, Math.min(100, los));
  const clampedFirstDown = Math.max(0, Math.min(100, firstDownLine));
  const clampedDriveStart = driveStartLos !== undefined
    ? Math.max(0, Math.min(100, driveStartLos))
    : undefined;

  // Convert to percentage for positioning
  const losPercent = direction === 'right' ? clampedLos : 100 - clampedLos;
  const firstDownPercent = direction === 'right' ? clampedFirstDown : 100 - clampedFirstDown;
  const driveStartPercent = clampedDriveStart !== undefined
    ? (direction === 'right' ? clampedDriveStart : 100 - clampedDriveStart)
    : undefined;

  return (
    <div className="field-position-bar">
      {/* End zones */}
      <div className="field-position-bar__endzone field-position-bar__endzone--left" />
      <div className="field-position-bar__endzone field-position-bar__endzone--right" />

      {/* Field with yard markers */}
      <div className="field-position-bar__field">
        {/* Yard line markers at 10, 20, 30, 40, 50 */}
        {[10, 20, 30, 40, 50, 60, 70, 80, 90].map(yard => (
          <div
            key={yard}
            className="field-position-bar__yard-marker"
            style={{ left: `${yard}%` }}
          >
            {yard <= 50 ? yard : 100 - yard}
          </div>
        ))}

        {/* Drive progress area (from start to current position) */}
        {driveStartPercent !== undefined && (
          <div
            className="field-position-bar__drive-progress"
            style={{
              left: `${Math.min(driveStartPercent, losPercent)}%`,
              width: `${Math.abs(losPercent - driveStartPercent)}%`,
            }}
          />
        )}

        {/* Red zone shading */}
        {isRedZone && (
          <div
            className="field-position-bar__redzone"
            style={{
              left: direction === 'right' ? '80%' : '0%',
              width: '20%',
            }}
          />
        )}

        {/* First down line */}
        <div
          className="field-position-bar__first-down"
          style={{ left: `${firstDownPercent}%` }}
        />

        {/* Line of scrimmage */}
        <div
          className="field-position-bar__los"
          style={{ left: `${losPercent}%` }}
        />

        {/* Ball marker */}
        <div
          className="field-position-bar__ball"
          style={{ left: `${losPercent}%` }}
        />
      </div>
    </div>
  );
};

export default FieldPositionBar;
