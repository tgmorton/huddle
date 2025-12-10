/**
 * FieldView - SVG-based football field visualization
 */

import { useGameStore } from '../../stores/gameStore';
import './FieldView.css';

export function FieldView() {
  const { gameState, homeTeam, awayTeam } = useGameStore();

  if (!gameState || !homeTeam || !awayTeam) {
    return (
      <div className="field-view field-view--loading">
        <p>Waiting for game...</p>
      </div>
    );
  }

  const { down_state, possession } = gameState;
  const lineOfScrimmage = down_state.line_of_scrimmage;
  const firstDownMarker = down_state.first_down_marker;
  const isHomeOffense = possession.team_with_ball === homeTeam.id;

  // Convert yard line (0-100) to SVG x position
  // Field is 100 yards, we'll use viewBox of 1000 units for the playing field
  // Plus 100 units on each side for end zones = 1200 total
  const yardToX = (yard: number) => 100 + (yard * 10);

  // Determine which end zone belongs to which team
  // Home team defends left (0), away defends right (100) at game start
  const homeEndZoneX = 0;
  const awayEndZoneX = 1100;

  return (
    <div className="field-view">
      <svg
        viewBox="0 0 1200 533"
        preserveAspectRatio="xMidYMid meet"
        className="field-view__svg"
      >
        {/* Field background */}
        <rect x="0" y="0" width="1200" height="533" fill="#2d5a3d" />

        {/* Home end zone (left) */}
        <rect
          x={homeEndZoneX}
          y="0"
          width="100"
          height="533"
          fill={homeTeam.primary_color}
          opacity="0.8"
        />
        <text
          x="50"
          y="266"
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#fff"
          fontSize="48"
          fontWeight="bold"
          transform="rotate(-90, 50, 266)"
          opacity="0.6"
        >
          {homeTeam.abbreviation}
        </text>

        {/* Away end zone (right) */}
        <rect
          x={awayEndZoneX}
          y="0"
          width="100"
          height="533"
          fill={awayTeam.primary_color}
          opacity="0.8"
        />
        <text
          x="1150"
          y="266"
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#fff"
          fontSize="48"
          fontWeight="bold"
          transform="rotate(90, 1150, 266)"
          opacity="0.6"
        >
          {awayTeam.abbreviation}
        </text>

        {/* Playing field border */}
        <rect
          x="100"
          y="0"
          width="1000"
          height="533"
          fill="none"
          stroke="#fff"
          strokeWidth="4"
        />

        {/* Yard lines every 5 yards */}
        {Array.from({ length: 21 }, (_, i) => i * 5).map((yard) => (
          <line
            key={yard}
            x1={yardToX(yard)}
            y1="0"
            x2={yardToX(yard)}
            y2="533"
            stroke="#fff"
            strokeWidth={yard % 10 === 0 ? 2 : 1}
            opacity={yard % 10 === 0 ? 0.8 : 0.4}
          />
        ))}

        {/* Yard numbers */}
        {[10, 20, 30, 40, 50, 40, 30, 20, 10].map((num, i) => {
          const yard = (i + 1) * 10;
          return (
            <g key={`num-${yard}`}>
              <text
                x={yardToX(yard)}
                y="50"
                textAnchor="middle"
                fill="#fff"
                fontSize="36"
                fontWeight="bold"
                opacity="0.5"
              >
                {num}
              </text>
              <text
                x={yardToX(yard)}
                y="500"
                textAnchor="middle"
                fill="#fff"
                fontSize="36"
                fontWeight="bold"
                opacity="0.5"
              >
                {num}
              </text>
            </g>
          );
        })}

        {/* Hash marks */}
        {Array.from({ length: 99 }, (_, i) => i + 1).map((yard) => (
          <g key={`hash-${yard}`}>
            <line
              x1={yardToX(yard)}
              y1="177"
              x2={yardToX(yard)}
              y2="187"
              stroke="#fff"
              strokeWidth="1"
              opacity="0.4"
            />
            <line
              x1={yardToX(yard)}
              y1="346"
              x2={yardToX(yard)}
              y2="356"
              stroke="#fff"
              strokeWidth="1"
              opacity="0.4"
            />
          </g>
        ))}

        {/* First down marker */}
        {firstDownMarker > 0 && firstDownMarker < 100 && (
          <line
            x1={yardToX(firstDownMarker)}
            y1="0"
            x2={yardToX(firstDownMarker)}
            y2="533"
            stroke="#ffeb3b"
            strokeWidth="4"
            strokeDasharray="10,5"
            className="field-view__first-down"
          />
        )}

        {/* Line of scrimmage */}
        <line
          x1={yardToX(lineOfScrimmage)}
          y1="0"
          x2={yardToX(lineOfScrimmage)}
          y2="533"
          stroke="#2196f3"
          strokeWidth="4"
          className="field-view__los"
        />

        {/* Ball indicator */}
        <g transform={`translate(${yardToX(lineOfScrimmage)}, 266)`}>
          <ellipse
            cx="0"
            cy="0"
            rx="15"
            ry="10"
            fill="#8B4513"
            stroke="#fff"
            strokeWidth="2"
          />
          {/* Possession indicator arrow */}
          <polygon
            points={isHomeOffense ? "25,0 40,-10 40,10" : "-25,0 -40,-10 -40,10"}
            fill={isHomeOffense ? homeTeam.primary_color : awayTeam.primary_color}
            stroke="#fff"
            strokeWidth="1"
          />
        </g>

        {/* Down and distance overlay */}
        <rect
          x="500"
          y="230"
          width="200"
          height="70"
          rx="8"
          fill="rgba(0,0,0,0.7)"
        />
        <text
          x="600"
          y="258"
          textAnchor="middle"
          fill="#fff"
          fontSize="20"
          fontWeight="bold"
        >
          {down_state.display}
        </text>
        <text
          x="600"
          y="285"
          textAnchor="middle"
          fill="#aaa"
          fontSize="16"
        >
          {down_state.field_position_display}
        </text>
      </svg>

      {/* Legend */}
      <div className="field-view__legend">
        <span className="field-view__legend-item">
          <span className="field-view__legend-color field-view__legend-color--los"></span>
          Line of Scrimmage
        </span>
        <span className="field-view__legend-item">
          <span className="field-view__legend-color field-view__legend-color--first"></span>
          First Down
        </span>
      </div>
    </div>
  );
}
