// ReferencePanel.tsx - Container that switches between different panel types

import React from 'react';
import type { LeftPanelView } from '../types';
import { PersonnelPanel } from './PersonnelPanel';
import { TransactionsPanel } from './TransactionsPanel';
import { FinancesPanel } from './FinancesPanel';
import { DraftPanel } from './DraftPanel';
import { SeasonPanel } from './SeasonPanel';
import { TeamPanel } from './TeamPanel';

interface ReferencePanelProps {
  type: Exclude<LeftPanelView, 'queue'>;
  onAddPlayerToWorkspace?: (player: { id: string; name: string; position: string; overall: number }) => void;
}

export const ReferencePanel: React.FC<ReferencePanelProps> = ({ type, onAddPlayerToWorkspace }) => {
  return (
    <div className="ref-panel">
      {type === 'personnel' && <PersonnelPanel onAddPlayerToWorkspace={onAddPlayerToWorkspace} />}
      {type === 'transactions' && <TransactionsPanel />}
      {type === 'finances' && <FinancesPanel />}
      {type === 'draft' && <DraftPanel />}
      {type === 'season' && <SeasonPanel />}
      {type === 'team' && <TeamPanel />}
    </div>
  );
};

export default ReferencePanel;
