// DeadlinePane.tsx - Simple placeholder pane for deadline type

import React from 'react';
import type { WorkspaceItem } from '../../types';

interface DeadlinePaneProps {
  item: WorkspaceItem;
  onComplete: () => void;
}

export const DeadlinePane: React.FC<DeadlinePaneProps> = ({ item, onComplete }) => (
  <div className="pane">
    <header className="pane__header">
      <div className="pane__header-left">
        <span className="pane__type">DUE</span>
        <div>
          <h2 className="pane__title">{item.title}</h2>
          <p className="pane__subtitle">{item.subtitle}</p>
        </div>
      </div>
      <button className="pane__close" onClick={onComplete}>Close</button>
    </header>
    <div className="pane__body pane__body--placeholder">
      <p>Deadline management UI would go here.</p>
    </div>
    <footer className="pane__footer">
      <button className="pane__btn pane__btn--secondary" onClick={onComplete}>Dismiss</button>
      <button className="pane__btn pane__btn--primary" onClick={onComplete}>Take Action</button>
    </footer>
  </div>
);

export default DeadlinePane;
