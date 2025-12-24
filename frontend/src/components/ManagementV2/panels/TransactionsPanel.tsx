// TransactionsPanel.tsx - Free Agents, Trades, Waivers tabs

import React, { useState } from 'react';
import { PlaceholderContent } from '../content/PlaceholderContent';
import { FreeAgentsContent } from '../content/FreeAgentsContent';

type TransactionsTab = 'free-agents' | 'trades' | 'waivers';

export const TransactionsPanel: React.FC = () => {
  const [tab, setTab] = useState<TransactionsTab>('free-agents');

  return (
    <div className="tabbed-panel">
      <div className="tabbed-panel__tabs">
        <button className={`tabbed-panel__tab ${tab === 'free-agents' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('free-agents')}>Free Agents</button>
        <button className={`tabbed-panel__tab ${tab === 'trades' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('trades')}>Trades</button>
        <button className={`tabbed-panel__tab ${tab === 'waivers' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('waivers')}>Waivers</button>
      </div>
      <div className="tabbed-panel__content">
        {tab === 'free-agents' && <FreeAgentsContent />}
        {tab === 'trades' && <PlaceholderContent title="Trade Block" />}
        {tab === 'waivers' && <PlaceholderContent title="Waivers" />}
      </div>
    </div>
  );
};

export default TransactionsPanel;
