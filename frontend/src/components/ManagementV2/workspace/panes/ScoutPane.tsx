// ScoutPane.tsx - Scout report pane showing opponent analysis with completion state

import React, { useState } from 'react';
import { CheckCircle, BookOpen, Target } from 'lucide-react';
import { managementApi } from '../../../../api/managementClient';
import { useManagementStore, selectFranchiseId } from '../../../../stores/managementStore';

interface ScoutPaneProps {
  eventPayload?: {
    opponent_name?: string;
    opponent_id?: string;
    week?: number;
    rankings?: {
      offense?: number;
      defense?: number;
    };
    tendencies?: {
      base_defense?: string;
      third_down?: string;
      red_zone?: string;
      blitz_rate?: string;
    };
    key_threats?: Array<{
      position: string;
      stat_type: string;
      stat_value: number;
    }>;
    attack_vectors?: Array<{
      area: string;
      note: string;
    }>;
  };
  onComplete: () => void;
}

export const ScoutPane: React.FC<ScoutPaneProps> = ({ eventPayload, onComplete }) => {
  const [completed, setCompleted] = useState(false);
  const [action, setAction] = useState<'notes' | 'reviewed' | null>(null);
  const franchiseId = useManagementStore(selectFranchiseId);
  const bumpJournalVersion = useManagementStore(state => state.bumpJournalVersion);

  // Get data from payload or use fallback defaults
  const opponentName = eventPayload?.opponent_name || 'Opponent';
  const rankings = eventPayload?.rankings || { offense: 16, defense: 16 };
  const tendencies = eventPayload?.tendencies || {
    base_defense: '4-3',
    third_down: 'Cover 3',
    red_zone: 'Man',
    blitz_rate: '35%',
  };
  const keyThreats = eventPayload?.key_threats || [
    { position: 'DE', stat_type: 'sacks', stat_value: 5 },
    { position: 'CB', stat_type: 'INTs', stat_value: 3 },
  ];
  const attackVectors = eventPayload?.attack_vectors || [
    { area: 'Slot CB', note: 'Weak vs quick routes' },
    { area: 'LB Coverage', note: 'Middle open' },
    { area: 'DE Crash', note: 'Bootleg opportunity' },
  ];

  // Handle completing the scout report
  const handleComplete = async (actionType: 'notes' | 'reviewed') => {
    setAction(actionType);
    setCompleted(true);

    // Post to journal
    if (franchiseId) {
      try {
        await managementApi.addJournalEntry(franchiseId, {
          category: 'intel',
          title: `${opponentName} Scout Report`,
          effect: 'Game Prep +15%',
          detail: actionType === 'notes'
            ? 'Notes saved for game planning reference.'
            : `${tendencies.third_down} coverage on 3rd down, ${tendencies.blitz_rate} blitz rate.`,
        });
        bumpJournalVersion();
      } catch (err) {
        console.error('Failed to add journal entry:', err);
      }
    }
  };

  // Show completion state
  if (completed && action) {
    return (
      <div className="pane pane--no-header">
        <div className="pane__body">
          <div className="pane__alert pane__alert--success">
            <CheckCircle size={18} />
            <span>{action === 'notes' ? 'Notes Saved' : 'Report Reviewed'}</span>
          </div>
          <div className="pane-section">
            <div className="ctrl-result">
              <span className="ctrl-result__label">Game Prep</span>
              <span className="ctrl-result__value ctrl-result__value--success">+15%</span>
            </div>
            <div className="ctrl-result">
              <span className="ctrl-result__label">Playcall Bonus</span>
              <span className="ctrl-result__value">vs {tendencies.third_down}</span>
            </div>
            {action === 'notes' && (
              <div className="ctrl-result">
                <span className="ctrl-result__label">Notes</span>
                <span className="ctrl-result__value ctrl-result__value--muted">Saved to clipboard</span>
              </div>
            )}
          </div>
          <p className="pane__description pane__description--muted">
            {action === 'notes'
              ? 'Your notes have been saved. Reference them during game planning.'
              : 'Scout intel will give you an edge on game day.'}
          </p>
        </div>
        <footer className="pane__footer">
          <button className="pane__btn pane__btn--primary" onClick={onComplete}>
            Done
          </button>
        </footer>
      </div>
    );
  }

  // Rank class helper
  const rankClass = (rank: number) => {
    if (rank <= 10) return 'ctrl-result__value--success';
    if (rank >= 25) return 'ctrl-result__value--danger';
    if (rank >= 20) return 'ctrl-result__value--warning';
    return '';
  };

  return (
    <div className="pane pane--no-header">
      <div className="pane__body">
        {/* Header */}
        <div className="pane__alert pane__alert--info">
          <Target size={18} />
          <span>Scout Report: {opponentName}</span>
        </div>

        {/* Rankings */}
        <div className="pane-section">
          <div className="pane-section__header">Rankings</div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Offense</span>
            <span className={`ctrl-result__value ${rankClass(rankings.offense || 16)}`}>
              #{rankings.offense}
            </span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Defense</span>
            <span className={`ctrl-result__value ${rankClass(rankings.defense || 16)}`}>
              #{rankings.defense}
            </span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Blitz Rate</span>
            <span className="ctrl-result__value ctrl-result__value--muted">{tendencies.blitz_rate}</span>
          </div>
        </div>

        {/* Key Threats */}
        <div className="pane-section">
          <div className="pane-section__header">Key Threats</div>
          {keyThreats.map((threat, idx) => (
            <div key={idx} className="ctrl-result">
              <span className="ctrl-result__label">{threat.position}</span>
              <span className="ctrl-result__value ctrl-result__value--danger">
                {threat.stat_value} {threat.stat_type}
              </span>
            </div>
          ))}
        </div>

        {/* Tendencies */}
        <div className="pane-section">
          <div className="pane-section__header">Tendencies</div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Base Defense</span>
            <span className="ctrl-result__value ctrl-result__value--muted">{tendencies.base_defense}</span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">3rd Down</span>
            <span className="ctrl-result__value ctrl-result__value--muted">{tendencies.third_down}</span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Red Zone</span>
            <span className="ctrl-result__value ctrl-result__value--muted">{tendencies.red_zone}</span>
          </div>
        </div>

        {/* Attack Vectors */}
        <div className="pane-section">
          <div className="pane-section__header">Attack Vectors</div>
          {attackVectors.map((vector, idx) => (
            <div key={idx} className="ctrl-result">
              <span className="ctrl-result__label">{vector.area}</span>
              <span className="ctrl-result__value">{vector.note}</span>
            </div>
          ))}
        </div>
      </div>

      <footer className="pane__footer">
        <button
          className="pane__btn pane__btn--secondary"
          onClick={() => handleComplete('notes')}
        >
          <BookOpen size={14} />
          Save Notes
        </button>
        <button
          className="pane__btn pane__btn--primary"
          onClick={() => handleComplete('reviewed')}
        >
          <CheckCircle size={14} />
          Got It
        </button>
      </footer>
    </div>
  );
};

export default ScoutPane;
