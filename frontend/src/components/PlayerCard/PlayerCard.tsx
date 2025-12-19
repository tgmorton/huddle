import React from 'react';
import './PlayerCard.css';

export type MoraleState = 'confident' | 'neutral' | 'struggling';
export type PhaseType = 'practice' | 'gameday' | 'recovery';

export interface PlayerCardProps {
  name: string;
  position: string;
  number: number;
  portraitUrl?: string;
  morale: MoraleState;
  phase?: PhaseType;
  stats?: {
    label: string;
    value: string | number;
  }[];
  isStarter?: boolean;
  onClick?: () => void;
}

const defaultPortrait = 'data:image/svg+xml,' + encodeURIComponent(`
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
    <rect fill="#1a1a1a" width="200" height="200"/>
    <circle cx="100" cy="75" r="45" fill="#333"/>
    <ellipse cx="100" cy="180" rx="60" ry="50" fill="#333"/>
  </svg>
`);

export const PlayerCard: React.FC<PlayerCardProps> = ({
  name,
  position,
  number,
  portraitUrl,
  morale,
  phase = 'practice',
  stats = [],
  isStarter = false,
  onClick,
}) => {
  const moraleLabel = {
    confident: 'Locked In',
    neutral: '',
    struggling: 'Needs Attention',
  };

  return (
    <div
      className={`player-card player-card--${morale} player-card--phase-${phase}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Ambient glow for confident players */}
      {morale === 'confident' && <div className="player-card__glow" />}

      {/* Portrait container with morale treatment */}
      <div className="player-card__portrait-container">
        <div className="player-card__portrait-frame">
          <img
            src={portraitUrl || defaultPortrait}
            alt={name}
            className="player-card__portrait"
          />
          {/* Vignette overlay for struggling players */}
          <div className="player-card__portrait-overlay" />
        </div>

        {/* Jersey number badge */}
        <div className="player-card__number">
          {number}
        </div>

        {/* Position tag */}
        <div className="player-card__position">
          {position}
        </div>
      </div>

      {/* Player info */}
      <div className="player-card__info">
        <h3 className="player-card__name">{name}</h3>

        {/* Morale indicator - subtle text, not a badge */}
        {moraleLabel[morale] && (
          <span className={`player-card__morale-hint player-card__morale-hint--${morale}`}>
            {moraleLabel[morale]}
          </span>
        )}

        {/* Stats row */}
        {stats.length > 0 && (
          <div className="player-card__stats">
            {stats.slice(0, 3).map((stat, i) => (
              <div key={i} className="player-card__stat">
                <span className="player-card__stat-value">{stat.value}</span>
                <span className="player-card__stat-label">{stat.label}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Starter indicator */}
      {isStarter && (
        <div className="player-card__starter-badge">
          STARTER
        </div>
      )}
    </div>
  );
};

export default PlayerCard;
