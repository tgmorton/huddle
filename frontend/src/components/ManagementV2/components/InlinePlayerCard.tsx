// InlinePlayerCard.tsx - Compact player card for embedding in events and lists
// Use this for inline references to players within panes and events

import React from 'react';
import { PlayerPortrait } from './PlayerPortrait';
import type { PortraitStatus } from './PlayerPortrait';

export interface InlinePlayerData {
  id: string;
  name: string;
  position: string;
  overall: number;
  number?: number;
  age?: number;
  experience?: string;
  salary?: string;
  status?: 'healthy' | 'injured' | 'questionable' | 'out';
}

export interface InlinePlayerCardProps {
  player: InlinePlayerData;
  leagueId?: string;
  variant?: 'compact' | 'standard' | 'detailed';
  showStatus?: boolean;
  showSalary?: boolean;
  onClick?: () => void;
  className?: string;
}

// Map player status to portrait status
const getPortraitStatus = (status?: InlinePlayerData['status']): PortraitStatus => {
  if (status === 'injured' || status === 'out') return 'injured';
  return 'normal';
};

// OVR color helper
const getOvrClass = (ovr: number): string => {
  if (ovr >= 85) return 'inline-player__ovr--elite';
  if (ovr >= 75) return 'inline-player__ovr--good';
  if (ovr >= 65) return 'inline-player__ovr--average';
  return 'inline-player__ovr--below';
};

// Status badge helper
const getStatusBadge = (status?: InlinePlayerData['status']) => {
  switch (status) {
    case 'injured':
      return { label: 'IR', class: 'inline-player__status--injured' };
    case 'questionable':
      return { label: 'Q', class: 'inline-player__status--questionable' };
    case 'out':
      return { label: 'OUT', class: 'inline-player__status--out' };
    default:
      return null;
  }
};

export const InlinePlayerCard: React.FC<InlinePlayerCardProps> = ({
  player,
  leagueId,
  variant = 'standard',
  showStatus = true,
  showSalary = false,
  onClick,
  className = '',
}) => {
  const statusBadge = showStatus ? getStatusBadge(player.status) : null;
  const isClickable = !!onClick;

  const containerClass = [
    'inline-player',
    `inline-player--${variant}`,
    isClickable && 'inline-player--clickable',
    player.status && player.status !== 'healthy' && 'inline-player--has-status',
    className,
  ].filter(Boolean).join(' ');

  const Component = isClickable ? 'button' : 'div';

  return (
    <Component
      className={containerClass}
      onClick={onClick}
      type={isClickable ? 'button' : undefined}
    >
      {/* Portrait */}
      <div className="inline-player__portrait">
        <PlayerPortrait
          playerId={player.id}
          leagueId={leagueId}
          size={variant === 'compact' ? 'sm' : variant === 'detailed' ? 'md' : 'roster'}
          status={getPortraitStatus(player.status)}
        />
        {statusBadge && (
          <span className={`inline-player__status ${statusBadge.class}`}>
            {statusBadge.label}
          </span>
        )}
      </div>

      {/* Info */}
      <div className="inline-player__info">
        <div className="inline-player__header">
          <span className="inline-player__pos">{player.position}</span>
          {player.number && (
            <span className="inline-player__number">#{player.number}</span>
          )}
          <span className="inline-player__name">{player.name}</span>
        </div>

        {variant !== 'compact' && (
          <div className="inline-player__meta">
            <span className={`inline-player__ovr ${getOvrClass(player.overall)}`}>
              {player.overall} OVR
            </span>
            {player.age && (
              <span className="inline-player__detail">{player.age} yrs</span>
            )}
            {player.experience && (
              <span className="inline-player__detail">{player.experience}</span>
            )}
            {showSalary && player.salary && (
              <span className="inline-player__salary">{player.salary}</span>
            )}
          </div>
        )}
      </div>

      {/* Compact OVR badge */}
      {variant === 'compact' && (
        <span className={`inline-player__ovr-badge ${getOvrClass(player.overall)}`}>
          {player.overall}
        </span>
      )}
    </Component>
  );
};

export default InlinePlayerCard;
