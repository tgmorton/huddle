// TeamPanel.tsx - Strategy, Playbook, Chemistry, Front Office tabs

import React, { useState } from 'react';
import { PlaceholderContent } from '../content/PlaceholderContent';
import { PlaybookContent } from '../content/PlaybookContent';

type TeamTab = 'strategy' | 'playbook' | 'chemistry' | 'front-office';

export const TeamPanel: React.FC = () => {
  const [tab, setTab] = useState<TeamTab>('strategy');

  return (
    <div className="tabbed-panel">
      <div className="tabbed-panel__tabs">
        <button className={`tabbed-panel__tab ${tab === 'strategy' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('strategy')}>Strategy</button>
        <button className={`tabbed-panel__tab ${tab === 'playbook' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('playbook')}>Playbook</button>
        <button className={`tabbed-panel__tab ${tab === 'chemistry' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('chemistry')}>Chemistry</button>
        <button className={`tabbed-panel__tab ${tab === 'front-office' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('front-office')}>Front Office</button>
      </div>
      <div className="tabbed-panel__content">
        {tab === 'strategy' && <PlaceholderContent title="Strategy" />}
        {tab === 'playbook' && <PlaybookContent />}
        {tab === 'chemistry' && <PlaceholderContent title="Team Chemistry" />}
        {tab === 'front-office' && <PlaceholderContent title="Front Office" />}
      </div>
    </div>
  );
};

export default TeamPanel;
