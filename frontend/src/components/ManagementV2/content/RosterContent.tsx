// RosterContent.tsx - Roster panel content with player list and detail views

import React from 'react';
import { Maximize2 } from 'lucide-react';
import type { Player, RosterView } from '../types';
import { DEMO_PLAYERS } from '../data/demo';

// === Color Helpers ===

const getOvrColor = (ovr: number): string => {
  if (ovr >= 90) return 'var(--success)';
  if (ovr >= 85) return 'var(--accent)';
  if (ovr >= 75) return 'var(--text-secondary)';
  return 'var(--text-muted)';
};

const getAgeColor = (age: number): string => {
  if (age <= 25) return 'var(--success)';
  if (age <= 28) return 'var(--text-secondary)';
  if (age <= 30) return 'var(--accent)';
  return 'var(--danger)';
};

const getContractColor = (years: number): string => {
  if (years >= 3) return 'var(--text-secondary)';
  if (years === 2) return 'var(--accent)';
  return 'var(--danger)'; // 1 year = expiring
};

const getMoraleIndicator = (morale: 'high' | 'neutral' | 'low'): { symbol: string; color: string } => {
  if (morale === 'high') return { symbol: '●', color: 'var(--success)' };
  if (morale === 'low') return { symbol: '●', color: 'var(--danger)' };
  return { symbol: '●', color: 'var(--text-muted)' };
};

// === PlayerDetailView ===

interface PlayerDetailViewProps {
  player: Player;
  onPopOut?: (player: Player) => void;
}

export const PlayerDetailView: React.FC<PlayerDetailViewProps> = ({ player, onPopOut }) => {
  const moraleColor = player.morale === 'high' ? 'var(--success)' : player.morale === 'low' ? 'var(--danger)' : 'var(--text-muted)';

  return (
    <div className="player-detail">
      <div className="player-detail__header">
        <span className="player-detail__number">#{player.number}</span>
        <div className="player-detail__info">
          <h3 className="player-detail__name">{player.name}</h3>
          <span className="player-detail__pos">{player.position} • {player.experience}</span>
        </div>
        <span className="player-detail__ovr">{player.overall}</span>
        {onPopOut && (
          <button
            className="player-detail__popout"
            onClick={() => onPopOut(player)}
            title="Open in workspace"
          >
            <Maximize2 size={14} />
          </button>
        )}
      </div>

      <div className="player-detail__section">
        <div className="player-detail__label">Contract</div>
        <div className="player-detail__row">
          <span>{player.salary}/yr</span>
          <span>{player.contractYears} yr{player.contractYears > 1 ? 's' : ''} left</span>
        </div>
      </div>

      <div className="player-detail__section">
        <div className="player-detail__label">Status</div>
        <div className="player-detail__row">
          <span>Age {player.age}</span>
          <span style={{ color: moraleColor }}>
            {player.morale === 'high' ? '● Happy' : player.morale === 'low' ? '● Unhappy' : '● Neutral'}
          </span>
        </div>
      </div>

      <div className="player-detail__section">
        <div className="player-detail__label">Traits</div>
        <div className="player-detail__traits">
          {player.traits.map(trait => (
            <span key={trait} className="player-detail__trait">{trait}</span>
          ))}
        </div>
      </div>

      <div className="player-detail__actions">
        <button className="player-detail__action">View Contract</button>
        <button className="player-detail__action player-detail__action--secondary">Release</button>
      </div>
    </div>
  );
};

// === RosterContent ===

interface RosterContentProps {
  onAddPlayerToWorkspace?: (player: { id: string; name: string; position: string; overall: number }) => void;
  view: RosterView;
  setView: (view: RosterView) => void;
}

export const RosterContent: React.FC<RosterContentProps> = ({ onAddPlayerToWorkspace, view, setView }) => {
  const selectedPlayer = view.type === 'player'
    ? DEMO_PLAYERS.find(p => p.id === view.playerId)
    : null;

  const handlePopOut = (player: Player) => {
    if (onAddPlayerToWorkspace) {
      onAddPlayerToWorkspace({
        id: player.id,
        name: player.name,
        position: player.position,
        overall: player.overall,
      });
    }
  };

  // Group players by position
  const positionOrder = ['QB', 'RB', 'WR', 'TE', 'DE', 'DT', 'LB', 'CB', 'S'];
  const grouped = DEMO_PLAYERS.reduce((acc, player) => {
    const pos = player.position;
    if (!acc[pos]) acc[pos] = [];
    acc[pos].push(player);
    return acc;
  }, {} as Record<string, Player[]>);

  // Sort each group by overall
  Object.values(grouped).forEach(group => {
    group.sort((a, b) => b.overall - a.overall);
  });

  const orderedGroups = positionOrder.filter(pos => grouped[pos]?.length);

  return (
    <div className="ref-content">
      {/* Content based on view */}
      {view.type === 'list' ? (
        <div className="stat-table">
          {orderedGroups.map(pos => (
            <div key={pos} className="stat-table__group">
              <div className="stat-table__header">
                <span className="stat-table__header-pos">{pos}</span>
                <span className="stat-table__header-attr">OVR</span>
                <span className="stat-table__header-attr">AGE</span>
                <span className="stat-table__header-attr">SAL</span>
                <span className="stat-table__header-attr">YRS</span>
              </div>
              {grouped[pos].map(player => {
                const morale = getMoraleIndicator(player.morale);
                return (
                  <button
                    key={player.id}
                    className="stat-table__row"
                    onClick={() => setView({ type: 'player', playerId: player.id })}
                  >
                    <span className="stat-table__name">
                      <span style={{ color: morale.color, fontSize: '8px' }}>{morale.symbol}</span>
                      {player.name}
                    </span>
                    <span className="stat-table__stat" style={{ color: getOvrColor(player.overall) }}>
                      {player.overall}
                    </span>
                    <span className="stat-table__stat" style={{ color: getAgeColor(player.age) }}>
                      {player.age}
                    </span>
                    <span className="stat-table__stat" style={{ color: 'var(--text-secondary)' }}>
                      {player.salary.replace('$', '').replace('.0M', 'M')}
                    </span>
                    <span className="stat-table__stat" style={{ color: getContractColor(player.contractYears) }}>
                      {player.contractYears}
                    </span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      ) : selectedPlayer ? (
        <PlayerDetailView player={selectedPlayer} onPopOut={handlePopOut} />
      ) : null}
    </div>
  );
};

export default RosterContent;
