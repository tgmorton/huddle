// FinancesPanel.tsx - Salary Cap, Contracts tabs

import React, { useState } from 'react';
import { PlaceholderContent } from '../content/PlaceholderContent';

type FinancesTab = 'cap' | 'contracts';

export const FinancesPanel: React.FC = () => {
  const [tab, setTab] = useState<FinancesTab>('cap');

  return (
    <div className="tabbed-panel">
      <div className="tabbed-panel__tabs">
        <button className={`tabbed-panel__tab ${tab === 'cap' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('cap')}>Salary Cap</button>
        <button className={`tabbed-panel__tab ${tab === 'contracts' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('contracts')}>Contracts</button>
      </div>
      <div className="tabbed-panel__content">
        {tab === 'cap' && <PlaceholderContent title="Salary Cap" />}
        {tab === 'contracts' && <PlaceholderContent title="Contracts" />}
      </div>
    </div>
  );
};

export default FinancesPanel;
