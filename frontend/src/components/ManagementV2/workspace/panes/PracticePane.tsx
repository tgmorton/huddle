// PracticePane.tsx - Practice allocation pane with sliders and intensity controls

import React, { useState } from 'react';

interface PracticePaneProps {
  onComplete: () => void;
}

export const PracticePane: React.FC<PracticePaneProps> = ({ onComplete }) => {
  const [allocation, setAllocation] = useState({
    playbook: 40,
    conditioning: 30,
    gamePrep: 30,
  });
  const [intensity, setIntensity] = useState<'light' | 'normal' | 'intense'>('normal');

  const total = allocation.playbook + allocation.conditioning + allocation.gamePrep;
  const remaining = 100 - total;
  const isMaxed = remaining === 0;

  const updateAllocation = (key: keyof typeof allocation, value: number) => {
    const oldValue = allocation[key];
    const otherTotal = total - oldValue;
    // Cap at 100% total
    const maxAllowed = 100 - otherTotal;
    const clampedValue = Math.min(value, maxAllowed);
    setAllocation({ ...allocation, [key]: clampedValue });
  };

  const riskLevel = intensity === 'light' ? 'Low' : intensity === 'normal' ? 'Medium' : 'High';
  const riskClass = intensity === 'intense' ? 'ctrl-result__value--danger' : intensity === 'normal' ? 'ctrl-result__value--warning' : 'ctrl-result__value--muted';

  return (
    <div className="pane">
      <header className="pane__header">
        <div className="pane__header-left">
          <span className="pane__type">PRC</span>
          <div>
            <h2 className="pane__title">Practice Allocation</h2>
            <p className="pane__subtitle">Thursday Practice • 120 min</p>
          </div>
        </div>
        <button className="pane__close" onClick={onComplete}>Cancel</button>
      </header>

      <div className="pane__body">
        {/* Allocation Section */}
        <div className="pane-section">
          <div className="pane-section__header">Allocation</div>
          <div className="ctrl-slider">
            <span className="ctrl-slider__label">Playbook</span>
            <input
              type="range"
              min="0"
              max="100"
              value={allocation.playbook}
              onChange={e => updateAllocation('playbook', Number(e.target.value))}
              className="ctrl-slider__input"
            />
            <span className="ctrl-slider__value">{allocation.playbook}%</span>
          </div>
          <div className="ctrl-slider">
            <span className="ctrl-slider__label">Conditioning</span>
            <input
              type="range"
              min="0"
              max="100"
              value={allocation.conditioning}
              onChange={e => updateAllocation('conditioning', Number(e.target.value))}
              className="ctrl-slider__input"
            />
            <span className="ctrl-slider__value">{allocation.conditioning}%</span>
          </div>
          <div className="ctrl-slider">
            <span className="ctrl-slider__label">Game Prep</span>
            <input
              type="range"
              min="0"
              max="100"
              value={allocation.gamePrep}
              onChange={e => updateAllocation('gamePrep', Number(e.target.value))}
              className="ctrl-slider__input"
            />
            <span className="ctrl-slider__value">{allocation.gamePrep}%</span>
          </div>
          <div className={`ctrl-status ${isMaxed ? 'ctrl-status--maxed' : ''}`}>
            {isMaxed ? '100% allocated' : `${remaining}% remaining`}
          </div>
        </div>

        {/* Intensity Toggle */}
        <div className="pane-section">
          <div className="ctrl-toggle">
            <span className="ctrl-toggle__label">Intensity</span>
            <div className="ctrl-toggle__options">
              {(['light', 'normal', 'intense'] as const).map(level => (
                <button
                  key={level}
                  className={`ctrl-toggle__btn ${intensity === level ? 'ctrl-toggle__btn--active' : ''}`}
                  onClick={() => setIntensity(level)}
                >
                  {level.charAt(0).toUpperCase() + level.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Projected Results */}
        <div className="pane-section">
          <div className="pane-section__header">Projected Results</div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Play Mastery</span>
            <span className="ctrl-result__value">+{Math.round(allocation.playbook * 0.3)}%</span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Player Development</span>
            <span className="ctrl-result__value">+{Math.round(allocation.conditioning * 0.2)} XP</span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Game Prep vs DAL</span>
            <span className="ctrl-result__value">+{Math.round(allocation.gamePrep * 0.4)}%</span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Injury Risk</span>
            <span className={`ctrl-result__value ${riskClass}`}>{riskLevel}</span>
          </div>
        </div>
      </div>

      <footer className="pane__footer">
        <button className="pane__btn pane__btn--secondary" onClick={onComplete}>Skip</button>
        <button className="pane__btn pane__btn--primary" onClick={onComplete}>Run Practice</button>
      </footer>
    </div>
  );
};

export default PracticePane;
