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
import { LeagueStatsPanel } from './LeagueStatsPanel';
import { HistoryPanel } from './HistoryPanel';

interface ReferencePanelProps {
  type: Exclude<LeftPanelView, 'queue'>;
  onAddPlayerToWorkspace?: (player: { id: string; name: string; position: string; overall: number }) => void;
  onAddProspectToWorkspace?: (prospect: { id: string; name: string; position: string; overall: number }) => void;
  onAddContractToWorkspace?: (contract: { id: string; name: string; position: string; salary: number }) => void;
  onStartNegotiation?: (player: { id: string; name: string; position: string; overall: number }) => void;
  onResumeNegotiation?: (player: { id: string; name: string; position: string; overall: number }) => void;
  onStartAuction?: (player: { id: string; name: string; position: string; overall: number }) => void;
  franchiseId?: string | null;
}

export const ReferencePanel: React.FC<ReferencePanelProps> = ({ type, onAddPlayerToWorkspace, onAddProspectToWorkspace, onAddContractToWorkspace, onStartNegotiation, onResumeNegotiation, onStartAuction, franchiseId }) => {
  return (
    <div className="ref-panel">
      {type === 'personnel' && <PersonnelPanel onAddPlayerToWorkspace={onAddPlayerToWorkspace} />}
      {type === 'transactions' && <TransactionsPanel onStartNegotiation={onStartNegotiation} onStartAuction={onStartAuction} />}
      {type === 'finances' && <FinancesPanel onAddPlayerToWorkspace={onAddPlayerToWorkspace} onAddContractToWorkspace={onAddContractToWorkspace} onResumeNegotiation={onResumeNegotiation} />}
      {type === 'draft' && <DraftPanel onAddProspectToWorkspace={onAddProspectToWorkspace} franchiseId={franchiseId} />}
      {type === 'season' && <SeasonPanel />}
      {type === 'team' && <TeamPanel />}
      {type === 'league' && <LeagueStatsPanel onAddPlayerToWorkspace={onAddPlayerToWorkspace} />}
      {type === 'week' && <WeekPanel franchiseId={franchiseId} />}
      {type === 'history' && <HistoryPanel />}
    </div>
  );
};

export default ReferencePanel;
