// SeasonPanel.tsx - Schedule, Standings, Playoffs tabs

import React, { useState } from 'react';
import { ScheduleContent } from '../content/ScheduleContent';
import { StandingsContent } from '../content/StandingsContent';
import { PlayoffsContent } from '../content/PlayoffsContent';

type SeasonTab = 'schedule' | 'standings' | 'playoffs';

export const SeasonPanel: React.FC = () => {
  const [tab, setTab] = useState<SeasonTab>('schedule');

  return (
    <div className="tabbed-panel">
      <div className="tabbed-panel__tabs">
        <button className={`tabbed-panel__tab ${tab === 'schedule' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('schedule')}>Schedule</button>
        <button className={`tabbed-panel__tab ${tab === 'standings' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('standings')}>Standings</button>
        <button className={`tabbed-panel__tab ${tab === 'playoffs' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('playoffs')}>Playoffs</button>
      </div>
      <div className="tabbed-panel__content">
        {tab === 'schedule' && <ScheduleContent />}
        {tab === 'standings' && <StandingsContent />}
        {tab === 'playoffs' && <PlayoffsContent />}
      </div>
    </div>
  );
};

export default SeasonPanel;
