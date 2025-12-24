// ReferencePanel.tsx - Container that switches between different panel types

import React from 'react';
import type { LeftPanelView } from '../types';
import { PersonnelPanel } from './PersonnelPanel';
import { TransactionsPanel } from './TransactionsPanel';
import { FinancesPanel } from './FinancesPanel';
import { DraftPanel } from './DraftPanel';
import { SeasonPanel } from './SeasonPanel';
import { TeamPanel } from './TeamPanel';
import { WeekPanel } from './WeekPanel';

interface ReferencePanelProps {
  type: Exclude<LeftPanelView, 'queue'>;
  onAddPlayerToWorkspace?: (player: { id: string; name: string; position: string; overall: number }) => void;
  onAddProspectToWorkspace?: (prospect: { id: string; name: string; position: string; overall: number }) => void;
  franchiseId?: string | null;
}

export const ReferencePanel: React.FC<ReferencePanelProps> = ({ type, onAddPlayerToWorkspace, onAddProspectToWorkspace, franchiseId }) => {
  return (
    <div className="ref-panel">
      {type === 'personnel' && <PersonnelPanel onAddPlayerToWorkspace={onAddPlayerToWorkspace} />}
      {type === 'transactions' && <TransactionsPanel />}
      {type === 'finances' && <FinancesPanel onAddPlayerToWorkspace={onAddPlayerToWorkspace} />}
      {type === 'draft' && <DraftPanel onAddProspectToWorkspace={onAddProspectToWorkspace} franchiseId={franchiseId} />}
      {type === 'season' && <SeasonPanel />}
      {type === 'team' && <TeamPanel />}
      {type === 'week' && <WeekPanel franchiseId={franchiseId} />}
    </div>
  );
};

export default ReferencePanel;
