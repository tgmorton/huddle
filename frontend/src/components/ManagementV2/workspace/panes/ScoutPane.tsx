// ScoutPane.tsx - Scout report pane showing opponent analysis

import React from 'react';

interface ScoutPaneProps {
  onComplete: () => void;
}

export const ScoutPane: React.FC<ScoutPaneProps> = ({ onComplete }) => (
  <div className="pane">
    <header className="pane__header">
      <div className="pane__header-left">
        <span className="pane__type">SCT</span>
        <div>
          <h2 className="pane__title">Dallas Cowboys</h2>
          <p className="pane__subtitle">Week 5 • 3-1 Record</p>
        </div>
      </div>
      <button className="pane__close" onClick={onComplete}>Done</button>
    </header>

    <div className="pane__body">
      {/* Rankings */}
      <div className="pane-section">
        <div className="pane-section__header">Rankings</div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">Offense</span>
          <span className="ctrl-result__value">#5</span>
        </div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">Defense</span>
          <span className="ctrl-result__value ctrl-result__value--warning">#18</span>
        </div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">Turnover Margin</span>
          <span className="ctrl-result__value">+6</span>
        </div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">Blitz Rate</span>
          <span className="ctrl-result__value ctrl-result__value--muted">38%</span>
        </div>
      </div>

      {/* Key Threats */}
      <div className="pane-section">
        <div className="pane-section__header">Key Threats</div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">DE M. Parsons</span>
          <span className="ctrl-result__value ctrl-result__value--danger">6 sacks</span>
        </div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">CB T. Diggs</span>
          <span className="ctrl-result__value ctrl-result__value--danger">3 INTs</span>
        </div>
      </div>

      {/* Tendencies */}
      <div className="pane-section">
        <div className="pane-section__header">Tendencies</div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">Base Defense</span>
          <span className="ctrl-result__value ctrl-result__value--muted">4-3 Under</span>
        </div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">3rd Down</span>
          <span className="ctrl-result__value ctrl-result__value--muted">Cover 3</span>
        </div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">Red Zone</span>
          <span className="ctrl-result__value ctrl-result__value--muted">Man</span>
        </div>
      </div>

      {/* Attack Vectors */}
      <div className="pane-section">
        <div className="pane-section__header">Attack Vectors</div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">Slot CB</span>
          <span className="ctrl-result__value">Weak vs quick routes</span>
        </div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">LB Coverage</span>
          <span className="ctrl-result__value">Middle open</span>
        </div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">DE Crash</span>
          <span className="ctrl-result__value">Bootleg opportunity</span>
        </div>
      </div>
    </div>

    <footer className="pane__footer">
      <button className="pane__btn pane__btn--secondary" onClick={onComplete}>Save Notes</button>
      <button className="pane__btn pane__btn--primary" onClick={onComplete}>Got It</button>
    </footer>
  </div>
);

export default ScoutPane;
