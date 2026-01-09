// FinancesPanel.tsx - Salary Cap, Contracts, Negotiations tabs

import React, { useState, useCallback } from 'react';
import { SalaryCapContent } from '../content/SalaryCapContent';
import { ContractsContent } from '../content/ContractsContent';
import { NegotiationsContent } from '../content/NegotiationsContent';

type FinancesTab = 'cap' | 'contracts' | 'negotiations';

interface FinancesPanelProps {
  onAddPlayerToWorkspace?: (player: { id: string; name: string; position: string; overall: number }) => void;
  onAddContractToWorkspace?: (contract: { id: string; name: string; position: string; salary: number }) => void;
  onResumeNegotiation?: (player: { id: string; name: string; position: string; overall: number }) => void;
}

export const FinancesPanel: React.FC<FinancesPanelProps> = ({ onAddPlayerToWorkspace, onAddContractToWorkspace, onResumeNegotiation }) => {
  const [tab, setTab] = useState<FinancesTab>('cap');

  // Handler for player clicks - will fetch player details and add to workspace
  const handlePlayerClick = useCallback((playerId: string, playerName: string, position: string, overall: number) => {
    if (onAddPlayerToWorkspace) {
      onAddPlayerToWorkspace({
        id: playerId,
        name: playerName,
        position,
        overall,
      });
    }
  }, [onAddPlayerToWorkspace]);

  // Handler for contract clicks - opens contract detail pane in workspace
  const handleContractClick = useCallback((playerId: string, playerName: string, position: string, salary: number) => {
    if (onAddContractToWorkspace) {
      onAddContractToWorkspace({
        id: playerId,
        name: playerName,
        position,
        salary,
      });
    }
  }, [onAddContractToWorkspace]);

  // Handler for resuming negotiation
  const handleResumeNegotiation = useCallback((playerId: string, playerName: string, position: string, overall: number) => {
    if (onResumeNegotiation) {
      onResumeNegotiation({
        id: playerId,
        name: playerName,
        position,
        overall,
      });
    }
  }, [onResumeNegotiation]);

  return (
    <div className="tabbed-panel">
      <div className="tabbed-panel__tabs">
        <button className={`tabbed-panel__tab ${tab === 'cap' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('cap')}>Salary Cap</button>
        <button className={`tabbed-panel__tab ${tab === 'contracts' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('contracts')}>Contracts</button>
        <button className={`tabbed-panel__tab ${tab === 'negotiations' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('negotiations')}>Negotiations</button>
      </div>
      <div className="tabbed-panel__content">
        {tab === 'cap' && <SalaryCapContent onPlayerClick={handlePlayerClick} />}
        {tab === 'contracts' && <ContractsContent onPlayerClick={handlePlayerClick} onContractClick={handleContractClick} />}
        {tab === 'negotiations' && <NegotiationsContent onResumeNegotiation={handleResumeNegotiation} />}
      </div>
    </div>
  );
};

export default FinancesPanel;
