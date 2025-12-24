// PlayerPortrait.tsx - Player portrait component with placeholder handling

import React, { useState } from 'react';

export type PortraitSize = 'xs' | 'sm' | 'roster' | 'md' | 'lg' | 'xl';
export type PortraitStatus = 'normal' | 'injured' | 'prospect' | 'selected';

const SIZE_MAP: Record<PortraitSize, number> = {
  xs: 32,      // Compact lists
  sm: 48,      // Depth chart, trade lists
  roster: 64,  // Roster table rows
  md: 80,      // Player cards, workspace items
  lg: 120,     // Player pane header, detail views
  xl: 200,     // Spotlight, draft selection moment
};

export interface PlayerPortraitProps {
  playerId?: string;
  leagueId?: string;
  size?: PortraitSize;
  teamAccent?: string;        // Team primary color for accent
  bracketed?: boolean;        // Corner bracket treatment
  status?: PortraitStatus;
  className?: string;
}

export const PlayerPortrait: React.FC<PlayerPortraitProps> = ({
  playerId,
  leagueId,
  size = 'md',
  teamAccent,
  bracketed = false,
  status = 'normal',
  className = '',
}) => {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);

  const px = SIZE_MAP[size];
  const showPlaceholder = !playerId || error || !loaded;

  // Portrait URL - matches API spec: /api/v1/portraits/{league_id}/{player_id}
  const portraitUrl = playerId && leagueId
    ? `/api/v1/portraits/${leagueId}/${playerId}`
    : null;

  const containerClass = [
    'portrait',
    `portrait--${size}`,
    bracketed && 'portrait--bracketed',
    status !== 'normal' && `portrait--${status}`,
    className,
  ].filter(Boolean).join(' ');

  const accentStyle = teamAccent ? {
    '--portrait-accent': teamAccent,
  } as React.CSSProperties : undefined;

  return (
    <div
      className={containerClass}
      style={{
        width: px,
        height: px,
        ...accentStyle,
      }}
    >
      {/* Placeholder - always rendered, hidden when image loads */}
      <div className={`portrait__placeholder ${!showPlaceholder ? 'portrait__placeholder--hidden' : ''}`}>
        <svg viewBox="0 0 80 80" fill="currentColor" opacity="0.3">
          {/* Simple head/shoulders silhouette */}
          <ellipse cx="40" cy="28" rx="16" ry="18" />
          <path d="M12 80 Q12 52 40 52 Q68 52 68 80" />
        </svg>
      </div>

      {/* Actual portrait image */}
      {portraitUrl && (
        <img
          src={portraitUrl}
          alt=""
          className={`portrait__image ${loaded ? 'portrait__image--loaded' : ''}`}
          onLoad={() => setLoaded(true)}
          onError={() => setError(true)}
          loading="lazy"
        />
      )}

      {/* Team accent edge (optional) */}
      {teamAccent && <div className="portrait__accent" />}
    </div>
  );
};

export default PlayerPortrait;
