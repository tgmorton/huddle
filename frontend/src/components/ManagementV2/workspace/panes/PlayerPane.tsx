// PlayerPane.tsx - Player detail pane for workspace

import React from 'react';
import { X } from 'lucide-react';
import { DEMO_PLAYERS } from '../../data/demo';

interface PlayerPaneProps {
  playerId: string;
  onComplete: () => void;
}

export const PlayerPane: React.FC<PlayerPaneProps> = ({ playerId, onComplete }) => {
  const player = DEMO_PLAYERS.find(p => p.id === playerId);

  if (!player) {
    return (
      <div className="pane">
        <header className="pane__header">
          <div className="pane__header-left">
            <span className="pane__type">PLR</span>
            <h2 className="pane__title">Player Not Found</h2>
          </div>
          <button className="pane__close" onClick={onComplete}><X size={16} /></button>
        </header>
      </div>
    );
  }

  const moraleColor = player.morale === 'high' ? 'var(--success)' : player.morale === 'low' ? 'var(--danger)' : 'var(--text-muted)';
  const moraleLabel = player.morale === 'high' ? 'Happy' : player.morale === 'low' ? 'Unhappy' : 'Neutral';

  return (
    <div className="pane">
      <header className="pane__header">
        <div className="pane__header-left">
          <span className="pane__type">PLR</span>
          <div>
            <h2 className="pane__title">#{player.number} {player.name}</h2>
            <p className="pane__subtitle">{player.position} • {player.experience}</p>
          </div>
        </div>
        <span className="pane__ovr">{player.overall}</span>
        <button className="pane__close" onClick={onComplete}><X size={16} /></button>
      </header>

      <div className="pane__body">
        {/* Contract */}
        <div className="pane-section">
          <div className="pane-section__header">Contract</div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Salary</span>
            <span className="ctrl-result__value ctrl-result__value--muted">{player.salary}/yr</span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Years Left</span>
            <span className="ctrl-result__value" style={{ color: player.contractYears <= 1 ? 'var(--danger)' : 'var(--text-secondary)' }}>
              {player.contractYears}
            </span>
          </div>
        </div>

        {/* Status */}
        <div className="pane-section">
          <div className="pane-section__header">Status</div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Age</span>
            <span className="ctrl-result__value ctrl-result__value--muted">{player.age}</span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Morale</span>
            <span className="ctrl-result__value" style={{ color: moraleColor }}>{moraleLabel}</span>
          </div>
        </div>

        {/* Traits */}
        <div className="pane-section">
          <div className="pane-section__header">Traits</div>
          <div className="player-pane__traits">
            {player.traits.map(trait => (
              <span key={trait} className="player-pane__trait">{trait}</span>
            ))}
          </div>
        </div>
      </div>

      <footer className="pane__footer">
        <button className="pane__btn pane__btn--secondary" onClick={onComplete}>View Contract</button>
        <button className="pane__btn pane__btn--danger" onClick={onComplete}>Release</button>
      </footer>
    </div>
  );
};

export default PlayerPane;
