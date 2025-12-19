// PersonnelPanel.tsx - Roster, Depth Chart, Coaches tabs

import React, { useState } from 'react';
import type { RosterView } from '../types';
import { RosterContent } from '../content/RosterContent';
import { DepthChartContent } from '../content/DepthChartContent';
import { CoachesContent } from '../content/CoachesContent';

type PersonnelTab = 'roster' | 'depth' | 'coaches';

interface PersonnelPanelProps {
  onAddPlayerToWorkspace?: (player: { id: string; name: string; position: string; overall: number }) => void;
}

export const PersonnelPanel: React.FC<PersonnelPanelProps> = ({ onAddPlayerToWorkspace }) => {
  const [tab, setTab] = useState<PersonnelTab>('roster');
  const [rosterView, setRosterView] = useState<RosterView>({ type: 'list' });

  const handleTabClick = (newTab: PersonnelTab) => {
    setTab(newTab);
    if (newTab !== 'roster') {
      setRosterView({ type: 'list' });
    }
  };

  return (
    <div className="tabbed-panel">
      <div className="tabbed-panel__tabs">
        <button
          className={`tabbed-panel__tab ${tab === 'roster' ? 'tabbed-panel__tab--active' : ''}`}
          onClick={() => { handleTabClick('roster'); setRosterView({ type: 'list' }); }}
        >
          Roster
        </button>
        <button className={`tabbed-panel__tab ${tab === 'depth' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => handleTabClick('depth')}>Depth</button>
        <button className={`tabbed-panel__tab ${tab === 'coaches' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => handleTabClick('coaches')}>Coaches</button>
      </div>
      <div className="tabbed-panel__content">
        {tab === 'roster' && <RosterContent onAddPlayerToWorkspace={onAddPlayerToWorkspace} view={rosterView} setView={setRosterView} />}
        {tab === 'depth' && <DepthChartContent />}
        {tab === 'coaches' && <CoachesContent />}
      </div>
    </div>
  );
};

export default PersonnelPanel;
