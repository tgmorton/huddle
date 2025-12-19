import React, { useState } from 'react';
import { PlayerCard } from './PlayerCard';
import type { MoraleState, PhaseType } from './PlayerCard';
import './PlayerCardDemo.css';

// Sample player portraits (using placeholder images)
const SAMPLE_PLAYERS = [
  {
    name: 'Marcus Williams',
    position: 'QB',
    number: 12,
    portraitUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300&h=300&fit=crop&crop=face',
    stats: [
      { label: 'TD', value: 24 },
      { label: 'INT', value: 6 },
      { label: 'QBR', value: 94.2 },
    ],
    isStarter: true,
  },
  {
    name: 'DeShawn Carter',
    position: 'WR',
    number: 81,
    portraitUrl: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=300&h=300&fit=crop&crop=face',
    stats: [
      { label: 'REC', value: 67 },
      { label: 'YDS', value: 1042 },
      { label: 'TD', value: 8 },
    ],
    isStarter: true,
  },
  {
    name: 'James Thompson',
    position: 'RB',
    number: 28,
    portraitUrl: 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=300&h=300&fit=crop&crop=face',
    stats: [
      { label: 'CAR', value: 156 },
      { label: 'YDS', value: 724 },
      { label: 'AVG', value: 4.6 },
    ],
    isStarter: false,
  },
];

const MORALE_STATES: MoraleState[] = ['confident', 'neutral', 'struggling'];
const PHASES: PhaseType[] = ['practice', 'gameday', 'recovery'];

export const PlayerCardDemo: React.FC = () => {
  const [activePhase, setActivePhase] = useState<PhaseType>('practice');

  return (
    <div className="player-card-demo" data-phase={activePhase}>
      <header className="demo-header">
        <h1>Player Card Prototype</h1>
        <p className="demo-subtitle">
          Morale communicated through visual treatment, not badges or meters
        </p>
      </header>

      {/* Phase selector */}
      <div className="phase-selector">
        <span className="phase-selector__label">Phase:</span>
        {PHASES.map((phase) => (
          <button
            key={phase}
            className={`phase-selector__btn ${activePhase === phase ? 'phase-selector__btn--active' : ''}`}
            onClick={() => setActivePhase(phase)}
            data-phase={phase}
          >
            {phase === 'practice' && '📋 Practice'}
            {phase === 'gameday' && '🏈 Game Day'}
            {phase === 'recovery' && '☀️ Recovery'}
          </button>
        ))}
      </div>

      {/* Morale comparison */}
      <section className="demo-section">
        <h2 className="demo-section__title">Morale States</h2>
        <p className="demo-section__desc">
          Same player, three mental states. Can you tell who needs attention?
        </p>

        <div className="card-row">
          {MORALE_STATES.map((morale) => (
            <div key={morale} className="card-column">
              <span className="card-label">{morale}</span>
              <PlayerCard
                {...SAMPLE_PLAYERS[0]}
                morale={morale}
                phase={activePhase}
              />
            </div>
          ))}
        </div>
      </section>

      {/* Roster preview */}
      <section className="demo-section">
        <h2 className="demo-section__title">Roster Context</h2>
        <p className="demo-section__desc">
          In a real roster view, your eye should immediately find who's struggling
        </p>

        <div className="card-row card-row--roster">
          <PlayerCard
            {...SAMPLE_PLAYERS[0]}
            morale="confident"
            phase={activePhase}
          />
          <PlayerCard
            {...SAMPLE_PLAYERS[1]}
            morale="struggling"
            phase={activePhase}
          />
          <PlayerCard
            {...SAMPLE_PLAYERS[2]}
            morale="neutral"
            phase={activePhase}
          />
        </div>
      </section>

      {/* The test */}
      <section className="demo-section demo-section--test">
        <h2 className="demo-section__title">The Test</h2>
        <div className="test-grid">
          <div className="test-question">
            <span className="test-q">Q:</span>
            <p>Without reading any text, which player needs your attention?</p>
          </div>
          <div className="test-answer">
            <span className="test-a">A:</span>
            <p>
              If you immediately looked at <strong>DeShawn Carter (#81)</strong>,
              the design is working. The desaturation and shadow treatment
              draws your coaching instinct before any cognitive processing.
            </p>
          </div>
        </div>
      </section>

      {/* Design notes */}
      <footer className="demo-footer">
        <h3>Design Treatments</h3>
        <div className="treatment-grid">
          <div className="treatment treatment--confident">
            <span className="treatment__label">Confident</span>
            <ul>
              <li>+10% brightness, +25% saturation</li>
              <li>Subtle glow around portrait</li>
              <li>Phase-colored accent ring</li>
              <li>Gentle pulse animation</li>
            </ul>
          </div>
          <div className="treatment treatment--neutral">
            <span className="treatment__label">Neutral</span>
            <ul>
              <li>Default brightness/saturation</li>
              <li>Clean, no effects</li>
              <li>Baseline state</li>
            </ul>
          </div>
          <div className="treatment treatment--struggling">
            <span className="treatment__label">Struggling</span>
            <ul>
              <li>-30% brightness, -60% saturation</li>
              <li>Vignette shadow overlay</li>
              <li>Muted colors throughout</li>
              <li>Pulsing "Needs Attention" hint</li>
            </ul>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default PlayerCardDemo;
