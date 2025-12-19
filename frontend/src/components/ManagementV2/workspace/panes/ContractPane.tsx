// ContractPane.tsx - Contract negotiation pane

import React from 'react';

interface ContractPaneProps {
  onComplete: () => void;
}

export const ContractPane: React.FC<ContractPaneProps> = ({ onComplete }) => (
  <div className="pane">
    <header className="pane__header">
      <div className="pane__header-left">
        <span className="pane__type">DEC</span>
        <div>
          <h2 className="pane__title">Contract Negotiation</h2>
          <p className="pane__subtitle">Jaylen Smith (WR) • Extension Request</p>
        </div>
      </div>
      <button className="pane__close" onClick={onComplete}>Cancel</button>
    </header>
    <div className="pane__body pane__body--placeholder">
      <p>Contract negotiation UI would go here with offer/counter-offer interface.</p>
    </div>
    <footer className="pane__footer">
      <button className="pane__btn pane__btn--secondary" onClick={onComplete}>Walk Away</button>
      <button className="pane__btn pane__btn--primary" onClick={onComplete}>Make Offer</button>
    </footer>
  </div>
);

export default ContractPane;
