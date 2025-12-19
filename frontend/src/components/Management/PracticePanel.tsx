/**
 * PracticePanel - Practice allocation UI
 *
 * When attending a practice event, this panel lets the user allocate
 * practice time between three focus areas:
 * - Playbook Learning: Helps team execute plays better
 * - Player Development: Grows young players' skills
 * - Game Prep: Gives edge vs next opponent
 */

import React, { useState } from 'react';
import './PracticePanel.css';

interface PracticeAllocation {
  playbook: number;
  development: number;
  gamePrep: number;
}

interface PracticePanelProps {
  eventId: string;
  duration: number; // minutes
  nextOpponent?: string;
  onRunPractice: (eventId: string, allocation: PracticeAllocation) => void;
  onCancel: () => void;
}

export const PracticePanel: React.FC<PracticePanelProps> = ({
  eventId,
  duration,
  nextOpponent,
  onRunPractice,
  onCancel,
}) => {
  const [allocation, setAllocation] = useState<PracticeAllocation>({
    playbook: 34,
    development: 33,
    gamePrep: 33,
  });

  const total = allocation.playbook + allocation.development + allocation.gamePrep;
  const isValid = total === 100;

  const handleSliderChange = (field: keyof PracticeAllocation, value: number) => {
    const others = Object.keys(allocation).filter(k => k !== field) as (keyof PracticeAllocation)[];
    const remaining = 100 - value;
    const currentOthersTotal = others.reduce((sum, k) => sum + allocation[k], 0);

    if (currentOthersTotal === 0) {
      // Split remaining evenly
      setAllocation({
        ...allocation,
        [field]: value,
        [others[0]]: Math.floor(remaining / 2),
        [others[1]]: Math.ceil(remaining / 2),
      });
    } else {
      // Scale others proportionally
      const scale = remaining / currentOthersTotal;
      setAllocation({
        ...allocation,
        [field]: value,
        [others[0]]: Math.round(allocation[others[0]] * scale),
        [others[1]]: 100 - value - Math.round(allocation[others[0]] * scale),
      });
    }
  };

  const handleSubmit = () => {
    if (isValid) {
      onRunPractice(eventId, allocation);
    }
  };

  const formatHours = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  };

  return (
    <div className="practice-panel">
      <div className="practice-panel__header">
        <h2 className="practice-panel__title">Practice Session</h2>
        <span className="practice-panel__duration">{formatHours(duration)} available</span>
      </div>

      <div className="practice-panel__intro">
        <p>How should the team spend practice time today?</p>
        {nextOpponent && (
          <p className="practice-panel__opponent">
            Next game: vs <strong>{nextOpponent}</strong>
          </p>
        )}
      </div>

      <div className="practice-panel__allocations">
        <AllocationSlider
          label="Playbook Learning"
          description="Master plays and formations. Improves execution and reduces mistakes."
          value={allocation.playbook}
          onChange={(v) => handleSliderChange('playbook', v)}
          color="#3b82f6"
        />

        <AllocationSlider
          label="Player Development"
          description="Individual skill work. Best for young players with high potential."
          value={allocation.development}
          onChange={(v) => handleSliderChange('development', v)}
          color="#10b981"
        />

        <AllocationSlider
          label="Game Prep"
          description={nextOpponent
            ? `Study ${nextOpponent}'s tendencies. Gives edge in the next game.`
            : "Study opponent tendencies. Gives edge in the next game."
          }
          value={allocation.gamePrep}
          onChange={(v) => handleSliderChange('gamePrep', v)}
          color="#f59e0b"
        />
      </div>

      <div className="practice-panel__summary">
        <div className={`practice-panel__total ${isValid ? '' : 'practice-panel__total--invalid'}`}>
          Total: {total}%
          {!isValid && <span className="practice-panel__total-warning"> (must equal 100%)</span>}
        </div>
      </div>

      <div className="practice-panel__actions">
        <button
          className="practice-panel__btn practice-panel__btn--cancel"
          onClick={onCancel}
        >
          Skip Practice
        </button>
        <button
          className="practice-panel__btn practice-panel__btn--run"
          onClick={handleSubmit}
          disabled={!isValid}
        >
          Run Practice
        </button>
      </div>
    </div>
  );
};

interface AllocationSliderProps {
  label: string;
  description: string;
  value: number;
  onChange: (value: number) => void;
  color: string;
}

const AllocationSlider: React.FC<AllocationSliderProps> = ({
  label,
  description,
  value,
  onChange,
  color,
}) => {
  return (
    <div className="allocation-slider">
      <div className="allocation-slider__header">
        <span className="allocation-slider__label">{label}</span>
        <span className="allocation-slider__value" style={{ color }}>{value}%</span>
      </div>
      <p className="allocation-slider__description">{description}</p>
      <div className="allocation-slider__track">
        <input
          type="range"
          min="0"
          max="100"
          value={value}
          onChange={(e) => onChange(parseInt(e.target.value, 10))}
          className="allocation-slider__input"
          style={{
            '--slider-color': color,
            '--slider-percent': `${value}%`,
          } as React.CSSProperties}
        />
      </div>
    </div>
  );
};

export default PracticePanel;
