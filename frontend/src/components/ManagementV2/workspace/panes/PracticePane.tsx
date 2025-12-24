// PracticePane.tsx - Practice allocation pane with sliders and intensity controls

import React, { useState } from 'react';
import { managementApi } from '../../../../api/managementClient';
import type { PracticeResults } from '../../../../api/managementClient';
import { useManagementStore, selectFranchiseId } from '../../../../stores/managementStore';

interface PracticePaneProps {
  eventId?: string;
  onRunPractice?: (eventId: string, allocation: { playbook: number; development: number; gamePrep: number }) => void;
  onComplete: () => void;
}

export const PracticePane: React.FC<PracticePaneProps> = ({ eventId, onComplete }) => {
  const [allocation, setAllocation] = useState({
    playbook: 40,
    conditioning: 30,
    gamePrep: 30,
  });
  const [intensity, setIntensity] = useState<'light' | 'normal' | 'intense'>('normal');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<PracticeResults | null>(null);

  const franchiseId = useManagementStore(selectFranchiseId);
  const bumpJournalVersion = useManagementStore(state => state.bumpJournalVersion);

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
    <div className="pane pane--no-header">
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
        <button className="pane__btn pane__btn--secondary" onClick={onComplete} disabled={loading}>
          {results ? 'Close' : 'Skip'}
        </button>
        <button
          className="pane__btn pane__btn--primary"
          disabled={loading || !franchiseId || !eventId || !!results}
          onClick={async () => {
            if (!eventId || !franchiseId) return;

            setLoading(true);
            try {
              const practiceResults = await managementApi.runPractice(franchiseId, {
                event_id: eventId,
                playbook: allocation.playbook,
                development: allocation.conditioning,
                game_prep: allocation.gamePrep,
                intensity,
              });
              setResults(practiceResults);
              bumpJournalVersion();
            } catch (err) {
              console.error('Practice failed:', err);
              onComplete();
            } finally {
              setLoading(false);
            }
          }}
        >
          {loading ? 'Running...' : 'Run Practice'}
        </button>
      </footer>

      {/* Results Display */}
      {results && results.success && (
        <div className="pane-section pane-section--results">
          <div className="pane-section__header">Practice Complete</div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Players Practiced</span>
            <span className="ctrl-result__value">{results.playbook_stats.players_practiced}</span>
          </div>
          {results.playbook_stats.tier_advancements > 0 && (
            <div className="ctrl-result">
              <span className="ctrl-result__label">Mastery Advancements</span>
              <span className="ctrl-result__value ctrl-result__value--success">
                +{results.playbook_stats.tier_advancements}
              </span>
            </div>
          )}
          {results.development_stats.players_developed > 0 && (
            <div className="ctrl-result">
              <span className="ctrl-result__label">Players Developed</span>
              <span className="ctrl-result__value ctrl-result__value--success">
                {results.development_stats.players_developed}
              </span>
            </div>
          )}
          {results.game_prep_stats.opponent && (
            <div className="ctrl-result">
              <span className="ctrl-result__label">vs {results.game_prep_stats.opponent}</span>
              <span className="ctrl-result__value">
                {Math.round(results.game_prep_stats.prep_level * 100)}% Ready
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PracticePane;
