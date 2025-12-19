// DraftPanel.tsx - Board, Scouts, Prospects tabs

import React, { useState } from 'react';
import { PlaceholderContent } from '../content/PlaceholderContent';

type DraftTab = 'board' | 'scouts' | 'prospects';

export const DraftPanel: React.FC = () => {
  const [tab, setTab] = useState<DraftTab>('board');

  return (
    <div className="tabbed-panel">
      <div className="tabbed-panel__tabs">
        <button className={`tabbed-panel__tab ${tab === 'board' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('board')}>Board</button>
        <button className={`tabbed-panel__tab ${tab === 'scouts' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('scouts')}>Scouts</button>
        <button className={`tabbed-panel__tab ${tab === 'prospects' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('prospects')}>Prospects</button>
      </div>
      <div className="tabbed-panel__content">
        {tab === 'board' && <PlaceholderContent title="Draft Board" />}
        {tab === 'scouts' && <PlaceholderContent title="Scouts" />}
        {tab === 'prospects' && <PlaceholderContent title="Prospects" />}
      </div>
    </div>
  );
};

export default DraftPanel;
